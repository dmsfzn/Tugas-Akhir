# =============================================================
# preprocess.py  —  Step 1: Load raw dataset, clean & stem text
# Output : ../data/dataset_preprocessed.csv
# =============================================================

import re
import pandas as pd
from stemmid import Stemmer
from config import INPUT_FILE, PREPROCESSED, RANDOM_STATE
from Sastrawi.StopWordRemover.StopWordRemoverFactory import StopWordRemoverFactory


# =========================
# STOPWORD (Sastrawi & Kustom)
# =========================
factory = StopWordRemoverFactory()
STOPWORDS = set(factory.get_stop_words())

# Pertahankan kata penting untuk sentimen
STOPWORDS -= {"tidak", "kurang", "belum", "ga", "tak", "udah", "ada"}

# Tambahkan kata umum/domain-specific yang tidak membawa sentimen
CUSTOM_STOPWORDS = {"motor", "sangat", "terima", "kasih", "jadi", "steam", "cuci", "yg", "saya", "ini", "itu", "dan", "di", "ke", "dari", "untuk", "dengan", "pada"}
STOPWORDS.update(CUSTOM_STOPWORDS)

FIX_KATA = {
    "nyuci": "cuci",
    "mencuci": "cuci",
    "dicuci": "cuci",
    "nyuci": "cuci",
    "nyucinya": "cuci"
}

# =========================
# FUNGSI PREPROCESSING
# =========================
def normalisasi_teks(text: str, stemmer: Stemmer) -> str:
    text = str(text).lower()

    # cleaning
    text = re.sub(r"http\S+|www\S+", "", text)

    # Normalisasi variasi 'terima kasih' sebelum tokenizing
    text = re.sub(r"\bterima\s+kasih\b", "makasih", text)
    text = re.sub(r"\bterimakasih\b", "makasih", text)
    text = re.sub(r"\bmkasih\b", "makasih", text)

    text = re.sub(r"[^a-zA-Z\s]", "", text)
    text = re.sub(r"\s+", " ", text).strip()

    # tokenizing
    tokens = text.split()

    tokens = [FIX_KATA.get(t, t) for t in tokens]

    # stopword removal
    tokens = [t for t in tokens if t not in STOPWORDS]

    # gabung kembali
    text = " ".join(tokens)

    # stemming
    text = stemmer.loads(text)

    return text


# =========================
# MAIN
# =========================
def main():
    print("Membaca dataset...")
    df = pd.read_excel(INPUT_FILE)
    df["Label"] = df["Label"].str.lower()

    print("\nDistribusi Data Natural:")
    print(df["Label"].value_counts())

    print("\nMenyiapkan Stemmer stemmid...")
    stemmer = Stemmer()

    print("Memulai proses pembersihan teks...")
    df["text_processed"] = df["Ulasan"].apply(lambda t: normalisasi_teks(t, stemmer))

    # hapus kosong
    df = df[df["text_processed"].str.strip() != ""]

    # shuffle
    df = df.sample(frac=1, random_state=RANDOM_STATE).reset_index(drop=True)

    df.to_csv(PREPROCESSED, index=False)
    print(f"\nSelesai! Dataset tersimpan sebagai '{PREPROCESSED}'")


if __name__ == "__main__":
    main()