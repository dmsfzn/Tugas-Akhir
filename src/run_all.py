# =============================================================
# run_all.py  —  Jalankan seluruh pipeline secara berurutan:
#   1. preprocess.py  → bersihkan & stem dataset
#   2. train.py       → latih model & simpan artefak
#   3. predict.py     → jalankan dashboard prediksi interaktif
# =============================================================

import sys
import os

# Pastikan folder src ada di path agar 'from config import ...' bekerja
sys.path.insert(0, os.path.dirname(__file__))

import preprocess
import train
import predict

if __name__ == "__main__":
    print("=" * 60)
    print("STEP 1 — PREPROCESSING")
    print("=" * 60)
    preprocess.main()

    print("\n" + "=" * 60)
    print("STEP 2 — TRAINING")
    print("=" * 60)
    train.main()

    print("\n" + "=" * 60)
    print("STEP 3 — PREDIKSI INTERAKTIF")
    print("=" * 60)
    predict.main()
