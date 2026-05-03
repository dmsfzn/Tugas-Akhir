from flask import Flask, render_template, request, redirect, url_for, session, flash, make_response, jsonify
import mysql.connector
from functools import wraps
import csv
import io
from datetime import datetime, date
import hashlib
import re
from collections import Counter
import os
import sys
import joblib
import numpy as np
from stemmid import Stemmer

# Tambahkan path ke folder src agar bisa import predict.py
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'src')))
from predict import get_xai_explanation, hybrid_prediction  # type: ignore

app = Flask(__name__)
app.secret_key = 'motormind_secret_2024_ta'

# GLOBAL MODEL & NLP HELPERS
MODEL_PATH = os.path.join(app.root_path, '..', 'model', 'model.pkl')
VECTORIZER_PATH = os.path.join(app.root_path, '..', 'model', 'vectorizer.pkl')

try:
    _global_model = joblib.load(MODEL_PATH)
    _global_vectorizer = joblib.load(VECTORIZER_PATH)
    _global_stemmer = Stemmer()
    print("[SUCCESS] ML Models and Stemmer loaded successfully.")
except Exception as e:
    print(f"[ERROR] Error loading ML models: {e}")
    _global_model, _global_vectorizer, _global_stemmer = None, None, None

# Inject current datetime into all templates
@app.context_processor
def inject_now():
    return {'now': datetime.now}

# DATABASE
DB_CONFIG = {
    'host': 'localhost',
    'user': 'root',
    'password': '',
    'database': 'motormind_db'
}

def get_db():
    # Establish a connection to the MySQL database using the config above
    return mysql.connector.connect(**DB_CONFIG)

def hash_password(pw):
    # Hash the password using MD5 for secure comparison with the database record
    return hashlib.md5(pw.encode()).hexdigest()


# DECORATORS
def login_required(f):
    # Decorator to ensure that a user is logged into the session before accessing a protected route
    @wraps(f)
    def decorated(*args, **kwargs):
        if 'user_id' not in session:
            flash('Silakan login terlebih dahulu.', 'warning')
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated

def role_required(*roles):
    # Decorator to restrict access to certain routes based on the user's role (e.g., 'owner' or 'pegawai')
    def decorator(f):
        @wraps(f)
        def decorated(*args, **kwargs):
            if session.get('role') not in roles:
                flash('Akses ditolak — role tidak sesuai.', 'danger')
                return redirect(url_for('login'))
            return f(*args, **kwargs)
        return decorated
    return decorator


# AUTH ROUTES
@app.route('/', methods=['GET', 'POST'])
def login():
    """
    Handles user authentication.
    Accepts email or employee_id along with password and role.
    Redirects to the appropriate dashboard based on the user's role upon success.
    """
    if 'user_id' in session:
        return redirect(url_for('dashboard_redirect'))

    if request.method == 'POST':
        # Retrieve login credentials from the submitted form
        identifier = request.form.get('identifier', '').strip()
        password   = request.form.get('password', '')
        role       = request.form.get('role', 'pegawai')

        db = get_db()
        cur = db.cursor(dictionary=True)
        # Query the database to find an active user matching the email/employee_id, password, and role
        cur.execute(
            """SELECT * FROM users
               WHERE (email = %s OR employee_id = %s)
                 AND password = %s AND role = %s AND is_active = 1""",
            (identifier, identifier, hash_password(password), role)
        )
        user = cur.fetchone()
        cur.close(); db.close()

        if user:
            # Login successful: store user details in the session
            session['user_id']  = user['id']
            session['username'] = user['name']
            session['role']     = user['role']
            session['avatar']   = user.get('avatar', '')
            return redirect(url_for('dashboard_redirect'))
        else:
            # Login failed: show an error message
            flash('Identifikasi atau security key tidak valid.', 'danger')

    return render_template('login.html')


@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login'))


@app.route('/redirect')
@login_required
def dashboard_redirect():
    if session['role'] == 'pegawai':
        return redirect(url_for('pegawai_dashboard'))
    return redirect(url_for('owner_dashboard'))


# PEGAWAI — DASHBOARD
@app.route('/pegawai/dashboard')
@login_required
@role_required('pegawai')
def pegawai_dashboard():
    """
    Renders the dashboard for 'pegawai' (employee) role.
    Displays personal statistics: total analyses, positive/negative count, 
    and the 5 most recent analysis activities.
    """
    db = get_db()
    cur = db.cursor(dictionary=True)

    # Stats personal
    cur.execute("SELECT COUNT(*) AS total FROM analyses WHERE user_id = %s", (session['user_id'],))
    total = cur.fetchone()['total']

    cur.execute("SELECT COUNT(*) AS cnt FROM analyses WHERE user_id = %s AND sentiment = 'positif'", (session['user_id'],))
    positif = cur.fetchone()['cnt']

    cur.execute("SELECT COUNT(*) AS cnt FROM analyses WHERE user_id = %s AND sentiment = 'negatif'", (session['user_id'],))
    negatif = cur.fetchone()['cnt']

    # 5 terbaru
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


# PEGAWAI — ANALISIS
@app.route('/pegawai/analisis', methods=['GET', 'POST'])
@login_required
@role_required('pegawai')
def pegawai_analisis():
    """
    Handles the core sentiment analysis prediction logic.
    - Loads custom lexicon words from the database.
    - Runs the input text through the hybrid_prediction pipeline (ML + Lexicon).
    - Uses get_xai_explanation to map feature importances (LIME/SHAP) back to words.
    - Constructs an array of highlighted words based on Lexicon priority and XAI direction.
    - Saves the analysis result to the database and returns it to the UI.
    """
    result = None
    input_text = ''

    if request.method == 'POST':
        # Retrieve the text input to be analyzed
        input_text = request.form.get('text', '').strip()

        if input_text:
            # STEP 1: Load custom dictionary (lexicon) from DB to supplement ML predictions
            db = get_db()
            cur = db.cursor(dictionary=True)
            cur.execute("SELECT word, score FROM lexicon")
            lexicon_rows = cur.fetchall()
            KAMUS_KUSTOM = {row['word']: row['score'] for row in lexicon_rows}
            
            # STEP 2: Run the text through the hybrid ML and Lexicon pipeline
            # Predict using the global loaded models and the custom lexicon rules
            pred_result = hybrid_prediction(input_text, _global_model, _global_vectorizer, _global_stemmer, KAMUS_KUSTOM)
            
            word_count    = len(re.findall(r'\b\w+\b', input_text.lower()))
            sentiment     = pred_result['label']
            confidence    = pred_result['confidence'] / 100.0  # Scale 0-1 untuk UI
            lexicon_score = pred_result['lexicon_score']
            clean_text    = pred_result['clean_text']
            highlights    = []

            # STEP 3: Generate visual highlights using Explainable AI (XAI)
            # This identifies which words contributed to the positive or negative sentiment
            xai_expl = get_xai_explanation(clean_text, _global_model, _global_vectorizer)
            xai_dict = {item['fitur']: item['arah'] for item in xai_expl}
            
            # STEP 4: Map original words to their sentiment labels for UI highlighting
            # Iterate through the original words so the highlight matches the exact user input
            orig_words = re.findall(r'\b\w+\b', input_text.lower())
            for w in set(orig_words):
                # Priority 1: Check if the word exists in the custom Lexicon
                if w in KAMUS_KUSTOM:
                    lbl = 'positive' if KAMUS_KUSTOM[w] > 0 else 'negative'
                    highlights.append({'word': w, 'label': lbl})
                else:
                    # Priority 2: If not in Lexicon, stem the word and check XAI explanation
                    stemmed_w = _global_stemmer.loads(w) if _global_stemmer else w
                    if stemmed_w in xai_dict:
                        lbl = 'positive' if xai_dict[stemmed_w] == 'Positif' else 'negative'
                        highlights.append({'word': w, 'label': lbl})

            # STEP 5: Save the new analysis record to the database
            db = get_db()
            cur = db.cursor()
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


# PEGAWAI — HISTORY
@app.route('/pegawai/history')
@login_required
@role_required('pegawai')
def pegawai_history():
    """
    Displays the analysis history for the currently logged-in user.
    Supports filtering by keyword search (q), sentiment label, and date range.
    Implements pagination to handle large amounts of historical data.
    """
    q          = request.args.get('q', '').strip()
    sentiment  = request.args.get('sentiment', 'all')
    date_from  = request.args.get('date_from', '')
    date_to    = request.args.get('date_to', '')
    page       = int(request.args.get('page', 1))
    per_page   = 10

    db  = get_db()
    cur = db.cursor(dictionary=True)

    # Build query dynamically
    conditions = ["1=1"]
    params     = []

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
    total_rows = cur.fetchone()['cnt']
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


# PEGAWAI — LEXICON CRUD
@app.route('/pegawai/lexicon', methods=['GET', 'POST'])
@login_required
@role_required('pegawai')
def pegawai_lexicon():
    """
    Manages custom lexicon words specific to the application domain.
    Provides Create, Read, Update, and Delete (CRUD) operations for the lexicon table.
    The custom lexicon is loaded during analysis to adjust or override ML predictions.
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


# OWNER — DASHBOARD
@app.route('/owner/dashboard')
@login_required
@role_required('owner')
def owner_dashboard():
    """
    Renders the overall system dashboard for the 'owner' role.
    Aggregates statistics from all users, showing total sentiment distribution,
    7-day historical trends, and recent activities.
    """
    db  = get_db()
    cur = db.cursor(dictionary=True)

    cur.execute("SELECT COUNT(*) AS total FROM analyses")
    total = cur.fetchone()['total']

    cur.execute("SELECT COUNT(*) AS cnt FROM analyses WHERE sentiment='positif'")
    positif = cur.fetchone()['cnt']

    cur.execute("SELECT COUNT(*) AS cnt FROM analyses WHERE sentiment='negatif'")
    negatif = cur.fetchone()['cnt']

    # Trend per hari (7 hari terakhir)
    cur.execute(
        """SELECT DATE(created_at) AS day, COUNT(*) AS cnt
           FROM analyses WHERE created_at >= DATE_SUB(NOW(), INTERVAL 7 DAY)
           GROUP BY DATE(created_at) ORDER BY day ASC"""
    )
    trend = cur.fetchall()

    # Latest 5
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


# OWNER — INSIGHT
@app.route('/owner/insight')
@login_required
@role_required('owner')
def owner_insight():
    """
    Provides analytical insights for the owner, focusing specifically on negative sentiments.
    Extracts the most frequent words (excluding common stopwords) from negative texts
    to help identify persistent issues, and displays an 8-week negative trend.
    """
    db  = get_db()
    cur = db.cursor(dictionary=True)

    # Ambil semua teks negatif
    cur.execute("SELECT text FROM analyses WHERE sentiment='negatif'")
    rows = cur.fetchall()

    stopwords = {'yang','dan','di','ke','dari','untuk','dengan','pada','ini','itu',
                 'tidak','ada','juga','sudah','atau','bisa','lebih','dalam','saat','kami'}
    word_freq = Counter()
    for row in rows:
        words = re.findall(r'\b[a-z]{3,}\b', row['text'].lower())
        word_freq.update([w for w in words if w not in stopwords])

    top_words = word_freq.most_common(15)

    # Trend negatif per minggu
    cur.execute(
        """SELECT YEARWEEK(created_at,1) AS wk, COUNT(*) AS cnt
           FROM analyses WHERE sentiment='negatif'
             AND created_at >= DATE_SUB(NOW(), INTERVAL 8 WEEK)
           GROUP BY wk ORDER BY wk ASC"""
    )
    neg_trend = cur.fetchall()
    cur.close(); db.close()

    return render_template('owner/insight.html', top_words=top_words, neg_trend=neg_trend)


# REPORT / EXPORT
@app.route('/report/export-csv')
@login_required
def report_export_csv():
    db  = get_db()
    cur = db.cursor(dictionary=True)
    # Fetch analysis history; filter by user_id if the role is 'pegawai'
    if session['role'] == 'pegawai':
        cur.execute("SELECT * FROM analyses WHERE user_id=%s ORDER BY created_at DESC", (session['user_id'],))
    else:
        # Owner sees all analyses
        cur.execute("SELECT * FROM analyses ORDER BY created_at DESC")
    rows = cur.fetchall()
    cur.close(); db.close()

    output = io.StringIO()
    if rows:
        writer = csv.DictWriter(output, fieldnames=rows[0].keys())
        writer.writeheader()
        writer.writerows(rows)

    resp = make_response(output.getvalue())
    resp.headers['Content-Disposition'] = f'attachment; filename=motormind_export_{date.today()}.csv'
    resp.headers['Content-Type'] = 'text/csv; charset=utf-8'
    return resp


@app.route('/report/single/<int:analysis_id>')
@login_required
def report_single(analysis_id):
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
    """Popup laporan semua analisis milik user (range dari filter history)"""
    date_from = request.args.get('date_from', '')
    date_to   = request.args.get('date_to', '')
    sentiment = request.args.get('sentiment', 'all')
    q         = request.args.get('q', '').strip()

    db  = get_db()
    cur = db.cursor(dictionary=True)

    cond   = ["1=1"]
    params = []
    if session['role'] == 'pegawai':
        cond.append("user_id = %s"); params.append(session['user_id'])
    if q:
        cond.append("text LIKE %s"); params.append(f'%{q}%')
    if sentiment != 'all':
        cond.append("sentiment = %s"); params.append(sentiment)
    if date_from:
        cond.append("DATE(created_at) >= %s"); params.append(date_from)
    if date_to:
        cond.append("DATE(created_at) <= %s"); params.append(date_to)

    where = " AND ".join(cond)
    cur.execute(f"SELECT * FROM analyses WHERE {where} ORDER BY created_at DESC", params)
    rows = cur.fetchall()

    cur.execute(f"SELECT COUNT(*) AS tot, SUM(sentiment='positif') AS pos, SUM(sentiment='negatif') AS neg FROM analyses WHERE {where}", params)
    stats = cur.fetchone()
    cur.close(); db.close()

    return render_template('report_all_analyses.html',
                           rows=rows, stats=stats,
                           date_from=date_from, date_to=date_to,
                           sentiment=sentiment, q=q)


@app.route('/report/owner-statistik')
@login_required
@role_required('owner')
def report_owner_statistik():
    """Popup laporan statistik lengkap untuk owner"""
    db  = get_db()
    cur = db.cursor(dictionary=True)

    cur.execute("SELECT COUNT(*) AS total FROM analyses")
    total = cur.fetchone()['total']
    cur.execute("SELECT COUNT(*) AS cnt FROM analyses WHERE sentiment='positif'")
    positif = cur.fetchone()['cnt']
    cur.execute("SELECT COUNT(*) AS cnt FROM analyses WHERE sentiment='negatif'")
    negatif = cur.fetchone()['cnt']

    # Trend per hari (30 hari)
    cur.execute("""SELECT DATE(created_at) AS day,
                          SUM(sentiment='positif') AS pos,
                          SUM(sentiment='negatif') AS neg,
                          COUNT(*) AS total
                   FROM analyses WHERE created_at >= DATE_SUB(NOW(), INTERVAL 30 DAY)
                   GROUP BY DATE(created_at) ORDER BY day ASC""")
    trend = cur.fetchall()

    # Top 10 analyst
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
    """Popup laporan insight kata negatif untuk owner"""
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


@app.route('/report/lexicon-list')
@login_required
def report_lexicon_list():
    """Popup daftar lexicon lengkap"""
    db  = get_db()
    cur = db.cursor(dictionary=True)
    cur.execute("SELECT * FROM lexicon ORDER BY category, score ASC")
    lexicons = cur.fetchall()
    cur.execute("SELECT COUNT(*) AS tot, SUM(category='positif') AS pos, SUM(category='negatif') AS neg FROM lexicon")
    stats = cur.fetchone()
    cur.close(); db.close()
    return render_template('report_lexicon_list.html', lexicons=lexicons, stats=stats)


@app.route('/report/statistik')
@login_required
@role_required('owner')
def report_statistik():
    return redirect(url_for('report_owner_statistik'))


# API — Chart data (JSON)
@app.route('/api/chart/sentiment')
@login_required
def api_chart_sentiment():
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


if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)
