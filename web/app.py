"""
app.py — Flask entry point untuk aplikasi MotorMind.
Menangani autentikasi, routing per role, integrasi pipeline ML,
manajemen lexicon, dan ekspor laporan.
"""

import sys
import os

# Tambahkan direktori src ke sys.path agar modul predict dan config dapat diimpor.
# Gunakan abspath(__file__) agar path selalu absolut, apapun working directory saat Flask dijalankan.
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
@app.context_processor
def inject_now():
    """Inject datetime.now ke semua template agar bisa dipakai langsung."""
    return {'now': datetime.now}


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
# AUTH ROUTES
# ─────────────────────────────────────────────
@app.route('/', methods=['GET', 'POST'])
def login():
    """Halaman login: validasi identifier (email/NIP) + password ke DB."""
    if 'user_id' in session:
        return redirect(url_for('dashboard_redirect'))

    if request.method == 'POST':
        identifier = request.form.get('identifier', '').strip()
        password   = request.form.get('password', '')

        db = get_db()
        cur = db.cursor(dictionary=True)
        cur.execute(
            """SELECT * FROM users
               WHERE (email = %s OR employee_id = %s)
                 AND password = %s AND is_active = 1""",
            (identifier, identifier, hash_password(password))
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
            flash('Identifikasi atau security key tidak valid.', 'danger')

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

    cur.execute("SELECT COUNT(*) AS total FROM analyses WHERE user_id = %s", (session['user_id'],))
    total = cur.fetchone()['total']

    cur.execute("SELECT COUNT(*) AS cnt FROM analyses WHERE user_id = %s AND sentiment = 'positif'", (session['user_id'],))
    positif = cur.fetchone()['cnt']

    cur.execute("SELECT COUNT(*) AS cnt FROM analyses WHERE user_id = %s AND sentiment = 'negatif'", (session['user_id'],))
    negatif = cur.fetchone()['cnt']

    cur.execute(
        """SELECT id, LEFT(text,80) AS snippet, sentiment, confidence, created_at
           FROM analyses WHERE user_id = %s ORDER BY created_at DESC LIMIT 5""",
        (session['user_id'],)
    )
    recent = cur.fetchall()
    cur.close(); db.close()

    return render_template('pegawai/dashboard.html',
                           total=total, positif=positif, negatif=negatif,
                           recent=recent)


# ─────────────────────────────────────────────
# PEGAWAI — ANALISIS
# ─────────────────────────────────────────────
@app.route('/pegawai/analisis', methods=['GET', 'POST'])
@login_required
@role_required('pegawai')
def pegawai_analisis():
    """
    Halaman analisis sentimen.
    POST: jalankan pipeline Hybrid (MNB + Lexicon) → simpan hasil ke DB → tampilkan.
    GET:  tampilkan form input kosong.
    """
    result     = None
    input_text = ''

    if request.method == 'POST':
        input_text = request.form.get('text', '').strip()

        if input_text:
            # ── Ambil lexicon dari DB sebagai sumber tunggal ──────────────────
            db  = get_db()
            cur = db.cursor(dictionary=True)
            cur.execute("SELECT word, score FROM lexicon")
            combined_lexicon = {row['word']: float(row['score']) for row in cur.fetchall()}

            # ── Jalankan pipeline Hybrid ML + Lexicon ─────────────────────────
            pred = hybrid_prediction(input_text, _model, _vectorizer, _stemmer, combined_lexicon)

            sentiment     = pred['label']
            confidence    = pred['confidence'] / 100   # simpan sebagai 0–1
            lexicon_score = pred['lexicon_score']
            clean_text    = pred['clean_text']
            word_count    = len(input_text.split())

            # ── XAI: highlight kata yang berpengaruh pada prediksi ────────────
            xai_items  = get_xai_explanation(clean_text, _model, _vectorizer)
            # Ambil top-10 kata berpengaruh untuk highlight di template
            top_features = {item['fitur'] for item in xai_items[:10]}

            highlights = []
            for w in set(clean_text.split()):
                if w in top_features:
                    # Tentukan label highlight berdasarkan skor lexicon gabungan
                    lex_val = combined_lexicon.get(w, 0)
                    label   = 'positive' if lex_val >= 0 else 'negative'
                    highlights.append({'word': w, 'label': label})

            # ── Simpan hasil ke tabel analyses ───────────────────────────────
            cur.execute(
                """INSERT INTO analyses
                   (user_id, text, sentiment, confidence, lexicon_score, word_count, created_at)
                   VALUES (%s, %s, %s, %s, %s, %s, NOW())""",
                (session['user_id'], input_text, sentiment, confidence, lexicon_score, word_count)
            )
            db.commit()
            analysis_id = cur.lastrowid
            cur.close(); db.close()

            result = {
                'id'           : analysis_id,
                'sentiment'    : sentiment,
                'confidence'   : confidence,
                'lexicon_score': lexicon_score,
                'text'         : input_text,
                'highlights'   : highlights
            }

    return render_template('pegawai/analisis.html', result=result, input_text=input_text)


# ─────────────────────────────────────────────
# PEGAWAI — HISTORY
# ─────────────────────────────────────────────
@app.route('/pegawai/history')
@login_required
@role_required('pegawai')
def pegawai_history():
    """Riwayat analisis pegawai dengan filter (kata kunci, sentimen, rentang tanggal) dan paginasi."""
    q          = request.args.get('q', '').strip()
    sentiment  = request.args.get('sentiment', 'all')
    date_from  = request.args.get('date_from', '')
    date_to    = request.args.get('date_to', '')
    page       = int(request.args.get('page', 1))
    per_page   = 10

    db  = get_db()
    cur = db.cursor(dictionary=True)

    # Pegawai hanya melihat hasil analisisnya sendiri
    conditions = ["user_id = %s"]
    params     = [session['user_id']]

    if q:
        conditions.append("text LIKE %s")
        params.append(f'%{q}%')
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
        f"""SELECT id, LEFT(text,100) AS snippet, sentiment, confidence, created_at
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
# PEGAWAI — LEXICON CRUD
# ─────────────────────────────────────────────
@app.route('/pegawai/lexicon', methods=['GET', 'POST'])
@login_required
@role_required('pegawai')
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

    cond   = ["1=1"]
    params = []
    if q_lex:
        cond.append("word LIKE %s"); params.append(f'%{q_lex}%')
    if cat != 'all':
        cond.append("category = %s"); params.append(cat)

    cur.execute(f"SELECT * FROM lexicon WHERE {' AND '.join(cond)} ORDER BY word ASC", params)
    lexicons = cur.fetchall()
    cur.close(); db.close()

    return render_template('pegawai/lexicon.html', lexicons=lexicons, q=q_lex, cat=cat)


# ─────────────────────────────────────────────
# OWNER — DASHBOARD
# ─────────────────────────────────────────────
@app.route('/owner/dashboard')
@login_required
@role_required('owner')
def owner_dashboard():
    """Dashboard owner: statistik global, tren harian 7 hari, dan 5 analisis terbaru lintas pegawai."""
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
        """SELECT a.id, LEFT(a.text,90) AS snippet, a.sentiment, a.confidence, a.created_at, u.name AS analyst
           FROM analyses a JOIN users u ON a.user_id=u.id
           ORDER BY a.created_at DESC LIMIT 5"""
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


@app.route('/report/single/<int:analysis_id>')
@login_required
def report_single(analysis_id):
    """Laporan cetak satu analisis berdasarkan ID."""
    db  = get_db()
    cur = db.cursor(dictionary=True)
    cur.execute("SELECT * FROM analyses WHERE id=%s", (analysis_id,))
    row = cur.fetchone()
    cur.close(); db.close()
    if not row:
        return "Analysis not found", 404
    return render_template('report_single.html', row=row)


@app.route('/report/all-analyses')
@login_required
def report_all_analyses():
    """Popup laporan analisis dengan filter identik halaman history. Pegawai hanya melihat datanya sendiri."""
    date_from = request.args.get('date_from', '')
    date_to   = request.args.get('date_to', '')
    sentiment = request.args.get('sentiment', 'all')
    q         = request.args.get('q', '').strip()

    db  = get_db()
    cur = db.cursor(dictionary=True)

    if session['role'] == 'pegawai':
        cond   = ["user_id = %s"]
        params = [session['user_id']]
    else:
        cond   = ["1=1"]
        params = []
    if q:
        cond.append("text LIKE %s"); params.append(f'%{q}%')
    if sentiment != 'all':
        cond.append("sentiment = %s"); params.append(sentiment)
    if date_from:
        cond.append("DATE(created_at) >= %s"); params.append(date_from)
    if date_to:
        cond.append("DATE(created_at) <= %s"); params.append(date_to)

    where = " AND ".join(cond)

    # Subquery terlebih dahulu untuk menghindari ambiguitas kolom created_at saat JOIN dengan users
    cur.execute(
        f"""SELECT sub.id, sub.user_id, sub.text, sub.sentiment,
                   sub.confidence, sub.lexicon_score, sub.word_count,
                   sub.created_at, u.name AS analyst_name
            FROM (SELECT * FROM analyses WHERE {where}) AS sub
            LEFT JOIN users u ON sub.user_id = u.id
            ORDER BY sub.created_at DESC""",
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

    if session['role'] == 'pegawai':
        cond   = ["user_id = %s"]
        params = [session['user_id']]
    else:
        cond   = ["1=1"]
        params = []
    if q:
        cond.append("text LIKE %s"); params.append(f'%{q}%')
    if sentiment != 'all':
        cond.append("sentiment = %s"); params.append(sentiment)
    if date_from:
        cond.append("DATE(created_at) >= %s"); params.append(date_from)
    if date_to:
        cond.append("DATE(created_at) <= %s"); params.append(date_to)

    where = " AND ".join(cond)

    # Subquery to avoid ambiguity on created_at column during JOIN with users
    cur.execute(
        f"""SELECT sub.id, sub.user_id, sub.text, sub.sentiment,
                   sub.confidence, sub.lexicon_score, sub.word_count,
                   sub.created_at, u.name AS analyst_name
            FROM (SELECT * FROM analyses WHERE {where}) AS sub
            LEFT JOIN users u ON sub.user_id = u.id
            ORDER BY sub.created_at DESC""",
        params
    )
    rows = cur.fetchall()
    cur.close(); db.close()

    # Generate CSV in memory
    si = io.StringIO()
    cw = csv.writer(si)

    # Write header
    cw.writerow(['No', 'Tanggal & Waktu', 'Analyst', 'Teks Analisis', 'Sentimen', 'Confidence (%)', 'Lexicon Score', 'Word Count'])

    for idx, row in enumerate(rows, 1):
        created_at_str = row['created_at'].strftime('%Y-%m-%d %H:%M:%S') if row['created_at'] else '—'
        confidence_pct = round(row['confidence'] * 100, 1) if row['confidence'] else '—'
        cw.writerow([
            idx,
            created_at_str,
            row['analyst_name'] or '—',
            row['text'],
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
    """Popup laporan statistik lengkap untuk owner: tren 30 hari dan top 10 analyst."""
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

    cur.execute("""SELECT u.name, COUNT(*) AS cnt
                   FROM analyses a JOIN users u ON a.user_id=u.id
                   GROUP BY u.id ORDER BY cnt DESC LIMIT 10""")
    analysts = cur.fetchall()

    cur.close(); db.close()

    pos_pct = round((positif / total * 100) if total else 0, 1)
    neg_pct = round(100 - pos_pct, 1)

    return render_template('report_owner_statistik.html',
                           total=total, positif=positif, negatif=negatif,
                           pos_pct=pos_pct, neg_pct=neg_pct,
                           trend=trend, analysts=analysts)


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
