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
    "kacau":  -1,
    "lelet":  -1,
    "parah":  -1,
    "kotor":  -1,
    "lama":   -1,
    "nyaman":  1,
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
    # a. Preprocessing
    teks_bersih = stemmer.loads(text.lower())
    vec         = vectorizer.transform([teks_bersih])

    # b. Prediksi ML
    prob      = model.predict_proba(vec)[0]
    label_mnb = model.predict(vec)[0]
    conf_mnb  = max(prob) * 100

    # c. Lexicon scoring
    lex_score, neg_count, pos_count = lexicon_scoring(text.lower(), custom_dict)

    # d. Hybrid logic (combine, bukan overwrite)
    final_label = label_mnb
    final_conf  = conf_mnb

    if lex_score > 0 and label_mnb == "negatif":
        final_label = "positif"
        final_conf += 5
    elif lex_score < 0 and label_mnb == "positif":
        final_label = "negatif"
        final_conf += 5

    return {
        "label": final_label,
        "confidence": final_conf,
        "clean_text": teks_bersih,
        "lexicon_score": lex_score,
        "neg_count": neg_count,
        "pos_count": pos_count
    }

def lexicon_scoring(text: str, lexicon: dict):
    words = text.split()
    
    score = 0
    neg_count = 0
    pos_count = 0

    for w in words:
        if w in lexicon:
            val = lexicon[w]
            score += val

            if val < 0:
                neg_count += 1
            else:
                pos_count += 1

    return score, neg_count, pos_count

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

        result = hybrid_prediction(ulasan, model, vectorizer, stemmer, KAMUS_KUSTOM)

        label   = result["label"]
        conf    = result["confidence"]
        bersih  = result["clean_text"]
        lex_sc  = result["lexicon_score"]
        neg_cnt = result["neg_count"]
        pos_cnt = result["pos_count"]
        expl = get_xai_explanation(bersih, model, vectorizer)

        print(f"\n[ HASIL DASHBOARD ]")
        print(f"> Sentimen : {label.upper()}")
        print(f"> Keyakinan: {conf:.2f}%")
        print(f"> Lexicon Score: {lex_sc}")
        print(f"> Kata Negatif : {neg_cnt}")
        print(f"> Kata Positif : {pos_cnt}")
        if lex_sc < 0:
            print("→ Terdapat indikasi sentimen NEGATIF dari kamus leksikon")
        elif lex_sc > 0:
            print("→ Terdapat indikasi sentimen POSITIF dari kamus leksikon")
        else:
            print("→ Tidak ditemukan kata dalam kamus leksikon")

        print(f"\n[ ANALISIS XAI - LEKSIKON ]")
        for word in bersih.split():
            if word in KAMUS_KUSTOM:
                print(f"- Kata '{word}' → Skor: {KAMUS_KUSTOM[word]}")

        print(f"\n[ ANALISIS XAI - MACHINE LEARNING ]")
        for item in expl:
            print(f"- Fitur '{item['fitur']}' cenderung {item['arah']} (Kekuatan: {item['kekuatan']})")


if __name__ == "__main__":
    main()
