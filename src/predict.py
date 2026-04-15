# =============================================================
# predict.py  —  Step 3: Interactive sentiment prediction dashboard
# Input  : ../data/model_mnb.pkl, ../data/vectorizer.pkl
# =============================================================

import re
import joblib
import numpy as np
from stemmid import Stemmer
from config import MODEL_FILE, VECTORIZER_FILE


# Kamus kustom (di aplikasi web diambil dari database)
KAMUS_KUSTOM = {
    "kacau":  "negatif",
    "lelet":  "negatif",
    "parah":  "negatif",
    "nyaman": "positif",
}


def get_xai_explanation(text: str, model, vectorizer) -> list:
    """Kembalikan daftar fitur beserta arah & kekuatan kontribusinya."""
    feature_names = vectorizer.get_feature_names_out()
    classes = model.classes_
    idx_neg = np.where(classes == "negatif")[0][0]
    idx_pos = np.where(classes == "positif")[0][0]

    explanation = []
    for feature in feature_names:
        # Gunakan word boundary agar 'si' tidak terdeteksi dalam 'bersih'
        if re.search(r"\b" + re.escape(feature) + r"\b", text):
            idx_f   = np.where(feature_names == feature)[0][0]
            w_neg   = model.feature_log_prob_[idx_neg][idx_f]
            w_pos   = model.feature_log_prob_[idx_pos][idx_f]

            if w_neg < w_pos:
                arah     = "Positif"
                kekuatan = round(w_pos - w_neg, 2)
            else:
                arah     = "Negatif"
                kekuatan = round(w_neg - w_pos, 2)

            explanation.append({"fitur": feature, "arah": arah, "kekuatan": kekuatan})

    return sorted(explanation, key=lambda x: x["kekuatan"], reverse=True)


def hybrid_prediction(text: str, model, vectorizer, stemmer: Stemmer, custom_dict: dict):
    """Prediksi sentimen dengan boosting dari kamus kustom."""
    # a. Bersihkan & transform
    teks_bersih = stemmer.loads(text.lower())
    vec         = vectorizer.transform([teks_bersih])

    # b. Prediksi dasar (MNB)
    prob      = model.predict_proba(vec)[0]
    label_mnb = model.predict(vec)[0]
    conf_mnb  = max(prob) * 100

    # c. Cek kamus kustom (boosting)
    boost_label = None
    for word in teks_bersih.split():
        if word in custom_dict:
            boost_label = custom_dict[word]
            break

    final_label = boost_label if boost_label else label_mnb
    final_conf  = 99.9       if boost_label else conf_mnb

    return final_label, final_conf, teks_bersih


def main():
    # 1. Load model
    model      = joblib.load(MODEL_FILE)
    vectorizer = joblib.load(VECTORIZER_FILE)
    stemmer    = Stemmer()

    # 2. Interactive loop
    while True:
        ulasan = input("\nMasukkan ulasan (ketik 'exit' untuk keluar): ")
        if ulasan.lower() == "exit":
            break

        label, conf, bersih = hybrid_prediction(ulasan, model, vectorizer, stemmer, KAMUS_KUSTOM)
        expl = get_xai_explanation(bersih, model, vectorizer)

        print(f"\n[ HASIL DASHBOARD ]")
        print(f"> Sentimen : {label.upper()}")
        print(f"> Keyakinan: {conf:.2f}%")

        print(f"\n[ ANALISIS XAI (SKOR FITUR) ]")
        for item in expl:
            print(f"- Fitur '{item['fitur']}' cenderung {item['arah']} (Kekuatan: {item['kekuatan']})")


if __name__ == "__main__":
    main()
