# MotorMind — Aplikasi Analisis Sentimen
## Tugas Akhir | Flask + MySQL + TF-IDF + Naive Bayes + Lexicon Hybrid

---

## Struktur Proyek

```
motormind/
├── app.py                        ← Flask routes + session + DB queries
├── requirements.txt
├── schema.sql                    ← MySQL schema + seed data
├── static/
│   └── css/
│       └── style.css             ← Custom dark UI theme
└── templates/
    ├── base.html                 ← Sidebar + topbar (dinamis per role)
    ├── login.html                ← Halaman login (role tabs)
    ├── report_single.html        ← Laporan cetak/PDF
    ├── pegawai/
    │   ├── dashboard.html        ← Dashboard operasional
    │   ├── analisis.html         ← Input teks + word highlight
    │   ├── history.html          ← Riwayat + filter + pagination
    │   └── lexicon.html          ← CRUD lexicon (add/edit/delete)
    └── owner/
        ├── dashboard.html        ← Overview + pie chart + trend
        └── insight.html          ← Top kata negatif + word cloud
```

---

## Cara Setup (Laragon)

### 1. Persiapan Database
```bash
# Buka MySQL di Laragon Shell atau phpMyAdmin
mysql -u root < schema.sql
```

### 2. Install Dependencies
```bash
pip install -r requirements.txt
```

### 3. Jalankan Aplikasi
```bash
python app.py
# Buka: http://localhost:5000
```

---

## Akun Default (sesuai schema.sql)

| Role    | ID/Email           | Password   |
|---------|--------------------|------------|
| Pegawai | EMP001             | admin123   |
| Pegawai | budi@motormind.id  | admin123   |
| Owner   | OWN001             | owner123   |
| Owner   | owner@motormind.id | owner123   |

---

## Alur Role-Based Access

```
GET / (login)
    ├── POST role=pegawai → /pegawai/dashboard
    │       ├── /pegawai/analisis   (input teks)
    │       ├── /pegawai/history    (riwayat + filter)
    │       ├── /pegawai/lexicon    (CRUD)
    │       └── /report/export-csv
    │
    └── POST role=owner   → /owner/dashboard
            ├── /owner/insight
            ├── /report/statistik
            └── /report/export-csv
```

---

## Integrasi Model Sentimen (app.py baris ~73)

Cari komentar `# ─── PLACEHOLDER PIPELINE ───` di `pegawai_analisis()` dan
ganti dengan pipeline asli:

```python
# Contoh integrasi sklearn
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.naive_bayes import MultinomialNB
import pickle

# Load model yang sudah dilatih
with open('model/tfidf.pkl','rb') as f:  vectorizer = pickle.load(f)
with open('model/nb_model.pkl','rb') as f: model     = pickle.load(f)

# Prediksi
X         = vectorizer.transform([input_text])
sentiment = model.predict(X)[0]             # 'positif' / 'negatif'
proba     = model.predict_proba(X).max()    # confidence

# Lexicon score
lexicon_score = hitung_lexicon(input_text, db)
```

---

## Fitur per Role

### PEGAWAI
- [x] Dashboard personal (total, positif, negatif, recent)
- [x] Analisis sentimen (single text, word-level highlight)
- [x] Riwayat (search, filter tanggal, filter sentimen, pagination)
- [x] Lexicon CRUD (add, edit, delete, search)
- [x] Export CSV
- [x] Generate laporan tunggal (print/PDF)

### OWNER
- [x] Dashboard statistik global (total, pie chart, trend)
- [x] Deep Learning Lab CTA
- [x] Insight kata negatif (top 15, word cloud, tabel)
- [x] Tren negatif 8 minggu
- [x] Export data + laporan statistik

### GLOBAL
- [x] Login dengan session Flask
- [x] Redirect otomatis berdasarkan role
- [x] Proteksi route (`@login_required`, `@role_required`)
- [x] Flash messages → toast notifications
- [x] Responsive (mobile/tablet/desktop)
- [x] Dark UI tema MotorMind

---

## Catatan Teknis

- Password disimpan sebagai **MD5 hash** (ganti dengan `werkzeug.security` untuk produksi)
- Chart menggunakan **pure CSS + JS fetch** dari `/api/chart/sentiment`
- Semua static file menggunakan `url_for('static', filename=...)`
- Template menggunakan **Jinja2** dengan inheritance (`{% extends 'base.html' %}`)
