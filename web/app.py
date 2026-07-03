"""
app.py — Flask entry point untuk aplikasi MotorMind.
Menangani portal feedback pelanggan (simulasi wifi), autentikasi,
routing per role, manajemen pegawai oleh owner, manajemen lexicon,
dan ekspor laporan.
"""

import sys
import os

# Tambahkan direktori src ke sys.path agar modul predict dan config dapat diimpor.
_SRC_DIR = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'src'))
if _SRC_DIR not in sys.path:
    sys.path.insert(0, _SRC_DIR)

from flask import Flask, render_template, request, redirect, url_for, session, flash, make_response, jsonify
import mysql.connector
from functools import wraps
import csv
import io
from datetime import datetime
import hashlib
import re
from collections import Counter

# Impor pipeline ML dari src/predict.py
import joblib
from stemmid import Stemmer
from predict import hybrid_prediction, get_xai_explanation
from config import MODEL_FILE, VECTORIZER_FILE

app = Flask(__name__)
app.secret_key = 'motormind_secret_2024_ta'

# Muat model dan vectorizer satu kali saat aplikasi dijalankan (bukan per request)
_model      = joblib.load(MODEL_FILE)
_vectorizer = joblib.load(VECTORIZER_FILE)
_stemmer    = Stemmer()


# ─────────────────────────────────────────────
# CONTEXT PROCESSOR
# ─────────────────────────────────────────────
def format_date_id(dt, show_time=False, short_month=False, show_year=True, show_day=False):
    """Format datetime object or string to Indonesian date format."""
    if not dt:
        return '—'
    if isinstance(dt, str):
        try:
            dt = datetime.strptime(dt, '%Y-%m-%d %H:%M:%S')
        except ValueError:
            try:
                dt = datetime.strptime(dt, '%Y-%m-%d')
            except ValueError:
                return dt
                
    months = [
        'Januari', 'Februari', 'Maret', 'April', 'Mei', 'Juni',
        'Juli', 'Agustus', 'September', 'Oktober', 'November', 'Desember'
    ]
    short_months = [
        'Jan', 'Feb', 'Mar', 'Apr', 'Mei', 'Jun',
        'Jul', 'Agt', 'Sep', 'Okt', 'Nov', 'Des'
    ]
    
    days = ['Senin', 'Selasa', 'Rabu', 'Kamis', 'Jumat', 'Sabtu', 'Minggu']
    
    day_num = dt.day
    month_name = short_months[dt.month - 1] if short_month else months[dt.month - 1]
    year = dt.year
    
    formatted = ""
    if show_day and hasattr(dt, 'weekday'):
        day_name = days[dt.weekday()]
        formatted += f"{day_name}, "
        
    formatted += f"{day_num} {month_name}"
    if show_year:
        formatted += f" {year}"
    if show_time:
        formatted += f", {dt.strftime('%H:%M')}"
    return formatted

@app.context_processor
def inject_now():
    """Inject datetime.now dan helper format_date_id ke semua template."""
    return {
        'now': datetime.now,
        'format_date_id': format_date_id
    }


# ─────────────────────────────────────────────
# DATABASE
# ─────────────────────────────────────────────
DB_CONFIG = {
    'host': 'localhost',
    'user': 'root',
    'password': '',
    'database': 'motormind_db'
}

def get_db():
    """Buka dan kembalikan koneksi baru ke database MySQL."""
    return mysql.connector.connect(**DB_CONFIG)

def hash_password(pw):
    """Hash password menggunakan MD5 sebelum disimpan/dibandingkan."""
    return hashlib.md5(pw.encode()).hexdigest()


# ─────────────────────────────────────────────
# DECORATORS (AUTH GUARD)
# ─────────────────────────────────────────────
def login_required(f):
    """Decorator: redirect ke halaman login jika user belum login."""
    @wraps(f)
    def decorated(*args, **kwargs):
        if 'user_id' not in session:
            flash('Silakan login terlebih dahulu.', 'warning')
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated

def role_required(*roles):
    """Decorator: tolak akses jika role user tidak ada dalam daftar roles yang diizinkan."""
    def decorator(f):
        @wraps(f)
        def decorated(*args, **kwargs):
            if session.get('role') not in roles:
                flash('Akses ditolak — role tidak sesuai.', 'danger')
                return redirect(url_for('login'))
            return f(*args, **kwargs)
        return decorated
    return decorator


# ─────────────────────────────────────────────
# CUSTOMER FEEDBACK & WIFI PORTAL ROUTES
# ─────────────────────────────────────────────
@app.route('/', methods=['GET', 'POST'])
def index():
    """Halaman Awal: Form Feedback Pelanggan (Simulasi Wifi Captive Portal Redirect)."""
    if request.method == 'POST':
        customer_name = request.form.get('name', '').strip()
        motor_type = request.form.get('motor_type', '').strip()
        feedback = request.form.get('feedback', '').strip()
        criticism_suggestion = request.form.get('criticism_suggestion', '').strip()

        if not motor_type or not feedback:
            flash('Tipe Motor dan Feedback wajib diisi.', 'danger')
            return redirect(url_for('index'))

        # ── Ambil lexicon dari DB sebagai sumber tunggal ──────────────────
        db  = get_db()
        cur = db.cursor(dictionary=True)
        cur.execute("SELECT word, score FROM lexicon")
        combined_lexicon = {row['word']: float(row['score']) for row in cur.fetchall()}

        # ── Jalankan pipeline Hybrid ML + Lexicon ─────────────────────────
        pred = hybrid_prediction(feedback, _model, _vectorizer, _stemmer, combined_lexicon)

        sentiment     = pred['label']
        confidence    = pred['confidence'] / 100   # simpan sebagai 0–1
        lexicon_score = pred['lexicon_score']
        word_count    = len(feedback.split())

        # Simpan ke tabel analyses (tanpa user_id karena diisi langsung oleh pelanggan)
        cur.execute(
            """INSERT INTO analyses
               (customer_name, motor_type, text, criticism_suggestion, sentiment, confidence, lexicon_score, word_count, created_at)
               VALUES (%s, %s, %s, %s, %s, %s, %s, %s, NOW())""",
            (customer_name or None, motor_type, feedback, criticism_suggestion or None, sentiment, confidence, lexicon_score, word_count)
        )
        db.commit()
        cur.close(); db.close()

        # Simpan nama pelanggan di session sementara untuk halaman sukses
        session['last_customer'] = customer_name or 'Pelanggan Steam'
        return redirect(url_for('wifi_success'))

    return render_template('feedback.html')


@app.route('/wifi-success')
def wifi_success():
    """Halaman sukses setelah mengisi feedback: Terhubung ke Wifi Steam."""
    customer = session.pop('last_customer', 'Pelanggan Steam')
    return render_template('wifi_success.html', customer=customer)


# ─────────────────────────────────────────────
# AUTH ROUTES
# ─────────────────────────────────────────────
@app.route('/login', methods=['GET', 'POST'])
def login():
    """Halaman login: validasi identifier (email/employee_id) + password ke DB."""
    if 'user_id' in session:
        return redirect(url_for('dashboard_redirect'))

    if request.method == 'POST':
        identifier = request.form.get('identifier', '').strip()
        password   = request.form.get('password', '')

        db = get_db()
        cur = db.cursor(dictionary=True)
        cur.execute(
            """SELECT * FROM users
               WHERE employee_id = %s
                 AND password = %s AND is_active = 1""",
            (identifier, hash_password(password))
        )
        user = cur.fetchone()
        cur.close(); db.close()

        if user:
            session['user_id']  = user['id']
            session['username'] = user['name']
            session['role']     = user['role']
            session['avatar']   = user.get('avatar', '')
            return redirect(url_for('dashboard_redirect'))
        else:
            flash('Identifikasi atau password tidak valid.', 'danger')

    return render_template('login.html')


@app.route('/logout')
def logout():
    """Hapus session dan redirect ke halaman login."""
    session.clear()
    return redirect(url_for('login'))


@app.route('/redirect')
@login_required
def dashboard_redirect():
    """Arahkan user ke dashboard sesuai role setelah login."""
    if session['role'] == 'pegawai':
        return redirect(url_for('pegawai_dashboard'))
    return redirect(url_for('owner_dashboard'))


# ─────────────────────────────────────────────
# PEGAWAI — DASHBOARD
# ─────────────────────────────────────────────
@app.route('/pegawai/dashboard')
@login_required
@role_required('pegawai')
def pegawai_dashboard():
    """Dashboard pegawai: statistik personal (total, positif, negatif) + 5 analisis terbaru."""
    db = get_db()
    cur = db.cursor(dictionary=True)

    cur.execute("SELECT COUNT(*) AS total FROM analyses")
    total = cur.fetchone()['total']

    cur.execute("SELECT COUNT(*) AS cnt FROM analyses WHERE sentiment = 'positif'")
    positif = cur.fetchone()['cnt']

    cur.execute("SELECT COUNT(*) AS cnt FROM analyses WHERE sentiment = 'negatif'")
    negatif = cur.fetchone()['cnt']

    cur.execute(
        """SELECT id, customer_name, motor_type, LEFT(text,80) AS snippet, criticism_suggestion, sentiment, confidence, created_at
           FROM analyses ORDER BY created_at DESC LIMIT 5"""
    )
    recent = cur.fetchall()
    cur.close(); db.close()

    return render_template('pegawai/dashboard.html',
                           total=total, positif=positif, negatif=negatif,
                           recent=recent)


# ─────────────────────────────────────────────
# PEGAWAI & OWNER — HISTORY
# ─────────────────────────────────────────────
@app.route('/pegawai/history')
@login_required
@role_required('pegawai', 'owner')
def pegawai_history():
    """Riwayat analisis pegawai dan owner dengan filter (kata kunci, sentimen, rentang tanggal) dan paginasi."""
    q          = request.args.get('q', '').strip()
    sentiment  = request.args.get('sentiment', 'all')
    date_from  = request.args.get('date_from', '')
    date_to    = request.args.get('date_to', '')
    page       = int(request.args.get('page', 1))
    per_page   = 5

    db  = get_db()
    cur = db.cursor(dictionary=True)

    conditions = ["1=1"]
    params     = []

    if q:
        conditions.append("(text LIKE %s OR customer_name LIKE %s OR motor_type LIKE %s OR criticism_suggestion LIKE %s)")
        params.extend([f'%{q}%', f'%{q}%', f'%{q}%', f'%{q}%'])
    if sentiment != 'all':
        conditions.append("sentiment = %s")
        params.append(sentiment)
    if date_from:
        conditions.append("DATE(created_at) >= %s")
        params.append(date_from)
    if date_to:
        conditions.append("DATE(created_at) <= %s")
        params.append(date_to)

    where = " AND ".join(conditions)

    cur.execute(f"SELECT COUNT(*) AS cnt FROM analyses WHERE {where}", params)
    total_rows  = cur.fetchone()['cnt']
    total_pages = max(1, (total_rows + per_page - 1) // per_page)

    offset = (page - 1) * per_page
    cur.execute(
        f"""SELECT id, customer_name, motor_type, LEFT(text,100) AS snippet, criticism_suggestion, sentiment, confidence, created_at
            FROM analyses WHERE {where}
            ORDER BY created_at DESC LIMIT %s OFFSET %s""",
        params + [per_page, offset]
    )
    analyses = cur.fetchall()
    cur.close(); db.close()

    return render_template('pegawai/history.html',
                           analyses=analyses, total_rows=total_rows,
                           page=page, total_pages=total_pages,
                           q=q, sentiment=sentiment, date_from=date_from, date_to=date_to)


# ─────────────────────────────────────────────
# PEGAWAI & OWNER — LEXICON CRUD
# ─────────────────────────────────────────────
@app.route('/pegawai/lexicon', methods=['GET', 'POST'])
@login_required
@role_required('pegawai', 'owner')
def pegawai_lexicon():
    """
    Manajemen kamus lexicon sentimen.
    POST: tambah / edit / hapus kata lexicon.
    GET:  tampilkan daftar lexicon dengan filter kata kunci dan kategori.
    """
    db  = get_db()
    cur = db.cursor(dictionary=True)

    if request.method == 'POST':
        action = request.form.get('action')

        if action == 'add':
            word     = request.form.get('word', '').strip().lower()
            score    = float(request.form.get('score', 0))
            category = request.form.get('category', 'positif')
            cur.execute(
                "INSERT IGNORE INTO lexicon (word, score, category) VALUES (%s, %s, %s)",
                (word, score, category)
            )
            db.commit()
            flash(f'Kata "{word}" berhasil ditambahkan.', 'success')

        elif action == 'edit':
            lex_id   = int(request.form.get('id'))
            score    = float(request.form.get('score', 0))
            category = request.form.get('category', 'positif')
            cur.execute(
                "UPDATE lexicon SET score=%s, category=%s WHERE id=%s",
                (score, category, lex_id)
            )
            db.commit()
            flash('Lexicon berhasil diperbarui.', 'success')

        elif action == 'delete':
            lex_id = int(request.form.get('id'))
            cur.execute("DELETE FROM lexicon WHERE id=%s", (lex_id,))
            db.commit()
            flash('Kata berhasil dihapus.', 'info')

    q_lex = request.args.get('q', '').strip()
    cat   = request.args.get('cat', 'all')
    page  = int(request.args.get('page', 1))
    per_page = 5

    cond   = ["1=1"]
    params = []
    if q_lex:
        cond.append("word LIKE %s"); params.append(f'%{q_lex}%')
    if cat != 'all':
        cond.append("category = %s"); params.append(cat)

    where = " AND ".join(cond)
    cur.execute(f"SELECT COUNT(*) AS cnt FROM lexicon WHERE {where}", params)
    total_rows = cur.fetchone()['cnt']
    total_pages = max(1, (total_rows + per_page - 1) // per_page)
    offset = (page - 1) * per_page

    cur.execute(
        f"SELECT * FROM lexicon WHERE {where} ORDER BY word ASC LIMIT %s OFFSET %s",
        params + [per_page, offset]
    )
    lexicons = cur.fetchall()
    cur.close(); db.close()

    return render_template('pegawai/lexicon.html', lexicons=lexicons, q=q_lex, cat=cat, page=page, total_pages=total_pages, total_rows=total_rows)


# ─────────────────────────────────────────────
# OWNER — DASHBOARD
# ─────────────────────────────────────────────
@app.route('/owner/dashboard')
@login_required
@role_required('owner')
def owner_dashboard():
    """Dashboard owner: statistik global, tren harian 7 hari, dan 5 ulasan feedback terbaru."""
    db  = get_db()
    cur = db.cursor(dictionary=True)

    cur.execute("SELECT COUNT(*) AS total FROM analyses")
    total = cur.fetchone()['total']

    cur.execute("SELECT COUNT(*) AS cnt FROM analyses WHERE sentiment='positif'")
    positif = cur.fetchone()['cnt']

    cur.execute("SELECT COUNT(*) AS cnt FROM analyses WHERE sentiment='negatif'")
    negatif = cur.fetchone()['cnt']

    # Tren jumlah analisis per hari dalam 7 hari terakhir
    cur.execute(
        """SELECT DATE(created_at) AS day, COUNT(*) AS cnt
           FROM analyses WHERE created_at >= DATE_SUB(NOW(), INTERVAL 7 DAY)
           GROUP BY DATE(created_at) ORDER BY day ASC"""
    )
    trend = cur.fetchall()

    cur.execute(
        """SELECT id, customer_name, motor_type, LEFT(text,90) AS snippet, criticism_suggestion, sentiment, confidence, created_at
           FROM analyses
           ORDER BY created_at DESC LIMIT 5"""
    )
    latest = cur.fetchall()
    cur.close(); db.close()

    pos_pct = round((positif / total * 100) if total else 0, 1)
    neg_pct = round(100 - pos_pct, 1)

    return render_template('owner/dashboard.html',
                           total=total, positif=positif, negatif=negatif,
                           pos_pct=pos_pct, neg_pct=neg_pct,
                           trend=trend, latest=latest)


# ─────────────────────────────────────────────
# OWNER — INSIGHT
# ─────────────────────────────────────────────
@app.route('/owner/insight')
@login_required
@role_required('owner')
def owner_insight():
    """Insight owner: frekuensi kata pada ulasan negatif + tren mingguan 8 minggu terakhir."""
    db  = get_db()
    cur = db.cursor(dictionary=True)

    cur.execute("SELECT text FROM analyses WHERE sentiment='negatif'")
    rows = cur.fetchall()

    # Hitung frekuensi kata dari teks negatif, kecualikan stopword umum
    stopwords = {'yang','dan','di','ke','dari','untuk','dengan','pada','ini','itu',
                 'tidak','ada','juga','sudah','atau','bisa','lebih','dalam','saat','kami'}
    word_freq = Counter()
    for row in rows:
        words = re.findall(r'\b[a-z]{3,}\b', row['text'].lower())
        word_freq.update([w for w in words if w not in stopwords])

    top_words = word_freq.most_common(15)

    cur.execute(
        """SELECT YEARWEEK(created_at,1) AS wk, COUNT(*) AS cnt
           FROM analyses WHERE sentiment='negatif'
             AND created_at >= DATE_SUB(NOW(), INTERVAL 8 WEEK)
           GROUP BY wk ORDER BY wk ASC"""
    )
    neg_trend = cur.fetchall()
    cur.close(); db.close()

    return render_template('owner/insight.html', top_words=top_words, neg_trend=neg_trend)


# ─────────────────────────────────────────────
# OWNER — KELOLA PEGAWAI (CRUD)
# ─────────────────────────────────────────────
@app.route('/owner/employees', methods=['GET', 'POST'])
@login_required
@role_required('owner')
def owner_employees():
    """Halaman kelola pegawai oleh owner: tambah pegawai baru dan tampilkan daftar pegawai."""
    db = get_db()
    cur = db.cursor(dictionary=True)

    if request.method == 'POST':
        action = request.form.get('action')
        if action == 'add':
            name = request.form.get('name', '').strip()
            phone = request.form.get('phone', '').strip()
            employee_id = request.form.get('employee_id', '').strip()
            password = request.form.get('password', '')

            if name and phone and employee_id and password:
                # Cek apakah employee_id sudah ada
                cur.execute("SELECT id FROM users WHERE employee_id = %s", (employee_id,))
                if cur.fetchone():
                    flash(f'ID Pegawai "{employee_id}" sudah terdaftar.', 'danger')
                else:
                    hashed_pw = hash_password(password)
                    cur.execute(
                        "INSERT INTO users (employee_id, name, phone, password, role) VALUES (%s, %s, %s, %s, 'pegawai')",
                        (employee_id, name, phone, hashed_pw)
                    )
                    db.commit()
                    flash(f'Pegawai "{name}" berhasil ditambahkan.', 'success')
            else:
                flash('Semua kolom wajib diisi.', 'danger')

        elif action == 'edit':
            emp_id = int(request.form.get('id'))
            name = request.form.get('name', '').strip()
            phone = request.form.get('phone', '').strip()
            employee_id = request.form.get('employee_id', '').strip()
            password = request.form.get('password', '')
            is_active = int(request.form.get('is_active', 1))

            if name and phone and employee_id:
                if password:
                    hashed_pw = hash_password(password)
                    cur.execute(
                        "UPDATE users SET name = %s, phone = %s, employee_id = %s, password = %s, is_active = %s WHERE id = %s AND role = 'pegawai'",
                        (name, phone, employee_id, hashed_pw, is_active, emp_id)
                    )
                else:
                    cur.execute(
                        "UPDATE users SET name = %s, phone = %s, employee_id = %s, is_active = %s WHERE id = %s AND role = 'pegawai'",
                        (name, phone, employee_id, is_active, emp_id)
                    )
                db.commit()
                flash('Pegawai berhasil diperbarui.', 'success')
            else:
                flash('Nama, No. Telp, dan ID Pegawai wajib diisi.', 'danger')

        elif action == 'delete':
            emp_id = int(request.form.get('id'))
            # Mencegah menghapus diri sendiri
            if emp_id == session['user_id']:
                flash('Tidak dapat menghapus akun Anda sendiri.', 'danger')
            else:
                cur.execute("DELETE FROM users WHERE id = %s AND role = 'pegawai'", (emp_id,))
                db.commit()
                flash('Pegawai berhasil dihapus.', 'info')

    cur.execute("SELECT * FROM users WHERE role = 'pegawai' ORDER BY employee_id ASC")
    employees = cur.fetchall()
    cur.close(); db.close()

    return render_template('owner/employees.html', employees=employees)


# ─────────────────────────────────────────────
# REPORT / EXPORT
# ─────────────────────────────────────────────

@app.route('/report/lexicon-list')
@login_required
def report_lexicon_list():
    """Popup laporan daftar lexicon lengkap."""
    db  = get_db()
    cur = db.cursor(dictionary=True)
    cur.execute("SELECT * FROM lexicon ORDER BY word ASC")
    lexicons = cur.fetchall()
    cur.close(); db.close()

    total = len(lexicons)
    pos   = sum(1 for r in lexicons if r['category'] == 'positif')
    neg   = sum(1 for r in lexicons if r['category'] == 'negatif')
    stats = {'total': total, 'pos': pos, 'neg': neg}

    return render_template('report_lexicon_list.html', lexicons=lexicons, stats=stats)


@app.route('/report/employees')
@login_required
@role_required('owner')
def report_employees():
    """Popup laporan cetak daftar pegawai terdaftar."""
    db = get_db()
    cur = db.cursor(dictionary=True)
    cur.execute("SELECT employee_id, name, phone, created_at, is_active FROM users WHERE role = 'pegawai' ORDER BY employee_id ASC")
    employees = cur.fetchall()
    cur.close(); db.close()
    return render_template('report_employees.html', employees=employees)


@app.route('/report/all-analyses')
@login_required
def report_all_analyses():
    """Popup laporan analisis dengan filter identik halaman history."""
    date_from = request.args.get('date_from', '')
    date_to   = request.args.get('date_to', '')
    sentiment = request.args.get('sentiment', 'all')
    q         = request.args.get('q', '').strip()

    db  = get_db()
    cur = db.cursor(dictionary=True)

    cond   = ["1=1"]
    params = []
    if q:
        cond.append("(text LIKE %s OR customer_name LIKE %s OR motor_type LIKE %s OR criticism_suggestion LIKE %s)")
        params.extend([f'%{q}%', f'%{q}%', f'%{q}%', f'%{q}%'])
    if sentiment != 'all':
        cond.append("sentiment = %s"); params.append(sentiment)
    if date_from:
        cond.append("DATE(created_at) >= %s"); params.append(date_from)
    if date_to:
        cond.append("DATE(created_at) <= %s"); params.append(date_to)

    where = " AND ".join(cond)

    cur.execute(
        f"""SELECT id, customer_name, motor_type, text, criticism_suggestion, sentiment,
                   confidence, lexicon_score, word_count, created_at
            FROM analyses WHERE {where}
            ORDER BY created_at DESC""",
        params
    )
    rows = cur.fetchall()
    cur.close(); db.close()

    total = len(rows)
    pos   = sum(1 for r in rows if r['sentiment'] == 'positif')
    neg   = sum(1 for r in rows if r['sentiment'] == 'negatif')
    stats = {'total': total, 'pos': pos, 'neg': neg}

    return render_template('report_all_analyses.html',
                           rows=rows, stats=stats,
                           date_from=date_from, date_to=date_to,
                           sentiment=sentiment, q=q)


@app.route('/report/export-csv')
@login_required
def report_export_csv():
    """Download laporan analisis sebagai file CSV dengan filter identik."""
    date_from = request.args.get('date_from', '')
    date_to   = request.args.get('date_to', '')
    sentiment = request.args.get('sentiment', 'all')
    q         = request.args.get('q', '').strip()

    db  = get_db()
    cur = db.cursor(dictionary=True)

    cond   = ["1=1"]
    params = []
    if q:
        cond.append("(text LIKE %s OR customer_name LIKE %s OR motor_type LIKE %s OR criticism_suggestion LIKE %s)")
        params.extend([f'%{q}%', f'%{q}%', f'%{q}%', f'%{q}%'])
    if sentiment != 'all':
        cond.append("sentiment = %s"); params.append(sentiment)
    if date_from:
        cond.append("DATE(created_at) >= %s"); params.append(date_from)
    if date_to:
        cond.append("DATE(created_at) <= %s"); params.append(date_to)

    where = " AND ".join(cond)

    cur.execute(
        f"""SELECT id, customer_name, motor_type, text, criticism_suggestion, sentiment,
                   confidence, lexicon_score, word_count, created_at
            FROM analyses WHERE {where}
            ORDER BY created_at DESC""",
        params
    )
    rows = cur.fetchall()
    cur.close(); db.close()

    # Generate CSV in memory
    si = io.StringIO()
    cw = csv.writer(si)

    # Write header
    cw.writerow(['No', 'Tanggal & Waktu', 'Pelanggan', 'Tipe Motor', 'Teks Analisis', 'Kritik/Saran', 'Sentimen', 'Confidence (%)', 'Lexicon Score', 'Word Count'])

    for idx, row in enumerate(rows, 1):
        created_at_str = row['created_at'].strftime('%Y-%m-%d %H:%M:%S') if row['created_at'] else '—'
        confidence_pct = round(row['confidence'] * 100, 1) if row['confidence'] else '—'
        cw.writerow([
            idx,
            created_at_str,
            row['customer_name'] or 'Anonim',
            row['motor_type'] or '—',
            row['text'],
            row['criticism_suggestion'] or '—',
            row['sentiment'].upper() if row['sentiment'] else '—',
            confidence_pct,
            f"{row['lexicon_score']:+.2f}" if row['lexicon_score'] is not None else '—',
            row['word_count'] or 0
        ])

    output = make_response(si.getvalue())
    output.headers["Content-Disposition"] = f"attachment; filename=report_analyses_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
    output.headers["Content-type"] = "text/csv; charset=utf-8"
    return output


@app.route('/report/owner-statistik')
@login_required
@role_required('owner')
def report_owner_statistik():
    """Popup laporan statistik lengkap untuk owner: tren 30 hari dan top 10 tipe motor terpopuler."""
    db  = get_db()
    cur = db.cursor(dictionary=True)

    cur.execute("SELECT COUNT(*) AS total FROM analyses")
    total = cur.fetchone()['total']
    cur.execute("SELECT COUNT(*) AS cnt FROM analyses WHERE sentiment='positif'")
    positif = cur.fetchone()['cnt']
    cur.execute("SELECT COUNT(*) AS cnt FROM analyses WHERE sentiment='negatif'")
    negatif = cur.fetchone()['cnt']

    cur.execute("""SELECT DATE(created_at) AS day,
                          SUM(sentiment='positif') AS pos,
                          SUM(sentiment='negatif') AS neg,
                          COUNT(*) AS total
                   FROM analyses WHERE created_at >= DATE_SUB(NOW(), INTERVAL 30 DAY)
                   GROUP BY DATE(created_at) ORDER BY day ASC""")
    trend = cur.fetchall()

    cur.execute("""SELECT motor_type, COUNT(*) AS cnt
                   FROM analyses
                   GROUP BY motor_type ORDER BY cnt DESC LIMIT 10""")
    motor_types = cur.fetchall()

    cur.close(); db.close()

    pos_pct = round((positif / total * 100) if total else 0, 1)
    neg_pct = round(100 - pos_pct, 1)

    return render_template('report_owner_statistik.html',
                           total=total, positif=positif, negatif=negatif,
                           pos_pct=pos_pct, neg_pct=neg_pct,
                           trend=trend, motor_types=motor_types)


@app.route('/report/insight')
@login_required
@role_required('owner')
def report_insight():
    """Popup laporan insight kata negatif untuk owner."""
    db  = get_db()
    cur = db.cursor(dictionary=True)
    cur.execute("SELECT text FROM analyses WHERE sentiment='negatif'")
    rows = cur.fetchall()

    stopwords = {'yang','dan','di','ke','dari','untuk','dengan','pada','ini','itu',
                 'tidak','ada','juga','sudah','atau','bisa','lebih','dalam','saat','kami'}
    word_freq = Counter()
    for row in rows:
        words = re.findall(r'\b[a-z]{3,}\b', row['text'].lower())
        word_freq.update([w for w in words if w not in stopwords])
    top_words = word_freq.most_common(20)

    cur.execute("SELECT COUNT(*) AS total FROM analyses")
    total = cur.fetchone()['total']
    cur.execute("SELECT COUNT(*) AS cnt FROM analyses WHERE sentiment='negatif'")
    negatif = cur.fetchone()['cnt']
    cur.close(); db.close()

    return render_template('report_insight.html',
                           top_words=top_words, total=total, negatif=negatif)


# ─────────────────────────────────────────────
# API — Chart data (JSON)
# ─────────────────────────────────────────────
@app.route('/api/chart/sentiment')
@login_required
def api_chart_sentiment():
    """API endpoint: kembalikan data sentimen harian 30 hari terakhir dalam format JSON untuk chart."""
    db  = get_db()
    cur = db.cursor(dictionary=True)
    cur.execute(
        """SELECT DATE(created_at) AS day,
                  SUM(sentiment='positif') AS pos,
                  SUM(sentiment='negatif') AS neg
           FROM analyses
           WHERE created_at >= DATE_SUB(NOW(), INTERVAL 30 DAY)
           GROUP BY day ORDER BY day ASC"""
    )
    rows = cur.fetchall()
    cur.close(); db.close()
    return jsonify([{
        'day': str(r['day']), 'pos': int(r['pos']), 'neg': int(r['neg'])
    } for r in rows])


# ─────────────────────────────────────────────
if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)
