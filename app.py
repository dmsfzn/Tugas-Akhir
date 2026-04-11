import streamlit as st
import joblib
import re
from Sastrawi.Stemmer.StemmerFactory import StemmerFactory

# ==========================================
# 1. KONFIGURASI HALAMAN
# ==========================================
st.set_page_config(
    page_title="Sistem Analisis Sentimen",
    page_icon="🏍️",
    layout="centered"
)

# ==========================================
# 2. FUNGSI PREPROCESSING (HARUS SAMA DENGAN TRAINING)
# ==========================================
# Kita load stemmer di awal biar gak berat
factory = StemmerFactory()
stemmer = factory.create_stemmer()

def normalisasi_teks(teks):
    teks = str(teks)
    
    # Emoji -> Teks
    teks = teks.replace("👍", " bagus ").replace("👌", " oke ")
    teks = teks.replace("👎", " jelek ").replace("😡", " marah ")
    teks = teks.replace("😭", " kecewa ").replace("😂", " kecewa ").replace("🤣", " kecewa ")
    
    # Bersihkan Karakter
    teks = teks.lower()
    teks = re.sub(r'(.)\1{2,}', r'\1', teks) # jelekkk -> jelek
    teks = re.sub(r'[^a-z\s]', ' ', teks)    # Hapus simbol
    teks = re.sub(r'\bsangat\b', '', teks)   # Hapus kata 'sangat'
    
    # Stemming
    teks = stemmer.stem(teks)
    
    return re.sub(r'\s+', ' ', teks).strip()

# ==========================================
# 3. LOAD MODEL (CACHE SUPAYA CEPAT)
# ==========================================
@st.cache_resource
def load_model():
    try:
        model = joblib.load('model_nb_steam.pkl')
        vocab = joblib.load('vectorizer_tfidf.pkl')
        return model, vocab
    except FileNotFoundError:
        return None, None

model, vectorizer = load_model()

# ==========================================
# 4. TAMPILAN GUI (INTERFACE)
# ==========================================
st.title("🏍️ Analisis Sentimen Steam Motor")
st.markdown("Aplikasi untuk mendeteksi ulasan **Positif** atau **Negatif** secara otomatis menggunakan algoritma *Naive Bayes*.")

st.divider() # Garis pemisah

# Area Input
input_ulasan = st.text_area("Masukkan Ulasan Pelanggan:", height=150, placeholder="Contoh: Pelayanannya ramah banget, motor jadi kinclong!")

if st.button("🔍 Analisis Sentimen"):
    if input_ulasan.strip() == "":
        st.warning("⚠️ Mohon isi ulasan terlebih dahulu!")
    else:
        if model is None:
            st.error("❌ File model tidak ditemukan! Pastikan 'model_nb_steam.pkl' ada di folder yang sama.")
        else:
            # 1. Preprocessing
            with st.spinner('Sedang memproses teks...'):
                teks_bersih = normalisasi_teks(input_ulasan)
                
            # 2. Prediksi
            vec = vectorizer.transform([teks_bersih])
            hasil = model.predict(vec)[0]
            
            # 3. Tampilkan Hasil
            st.subheader("Hasil Analisis:")
            
            if hasil == "Positif":
                st.success(f"✅ Sentimen: **POSITIF**")
                st.balloons() # Efek balon biar keren
            else:
                st.error(f"⛔ Sentimen: **NEGATIF**")
            
            # Debugging (Opsional: Tampilkan teks bersih biar dosen lihat prosesnya)
            with st.expander("Lihat Proses Cleaning (Preprocessing)"):
                st.text(f"Asli   : {input_ulasan}")
                st.text(f"Bersih : {teks_bersih}")

# Footer
st.markdown("---")
st.caption("Dibuat untuk Tugas Akhir / Skripsi (2024)")