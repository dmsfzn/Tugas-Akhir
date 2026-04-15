# =============================================================
# train.py  —  Step 2: Train Multinomial NB model with TF-IDF
# Input  : ../data/dataset_preprocessed.csv
# Output : ../data/model_mnb.pkl, vectorizer.pkl, data_ujian.csv
# =============================================================

import pandas as pd
import joblib
from sklearn.model_selection import train_test_split
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.naive_bayes import MultinomialNB
from sklearn.metrics import accuracy_score
from imblearn.over_sampling import RandomOverSampler
from config import PREPROCESSED, MODEL_FILE, VECTORIZER_FILE, TEST_DATA_FILE, RANDOM_STATE


def main():
    # 1. Load data
    df = pd.read_csv(PREPROCESSED).dropna(subset=["text_processed", "Label"])
    X = df["text_processed"]
    y = df["Label"]

    # 2. Stratified split (80% train, 20% test)
    X_train, X_test, y_train, y_test = train_test_split(
        X, y,
        test_size=0.2,
        random_state=RANDOM_STATE,
        stratify=y
    )

    # 3. TF-IDF vectorization
    vectorizer = TfidfVectorizer(ngram_range=(1, 2))
    X_train_vec = vectorizer.fit_transform(X_train)
    X_test_vec  = vectorizer.transform(X_test)

    # 4. Oversampling
    ros = RandomOverSampler(random_state=RANDOM_STATE)
    X_train_bal, y_train_bal = ros.fit_resample(X_train_vec, y_train)
    print("Distribusi setelah oversampling:", pd.Series(y_train_bal).value_counts().to_dict())

    # 5. Training
    model = MultinomialNB(alpha=1.0)
    model.fit(X_train_bal, y_train_bal)
    print("Urutan Kelas di Model:", model.classes_)

    # 6. Simpan model & data uji
    joblib.dump(model, MODEL_FILE)
    joblib.dump(vectorizer, VECTORIZER_FILE)

    df_test = pd.DataFrame({"text_processed": X_test, "Label": y_test})
    df_test.to_csv(TEST_DATA_FILE, index=False)

    print("=== PROSES SELESAI ===")
    print(f"Model berhasil dilatih dengan {X_train_bal.shape[0]} data (setelah oversampling).")
    print(f"Akurasi pada data uji: {accuracy_score(y_test, model.predict(X_test_vec))*100:.2f}%")
    print(f"Data uji disimpan di: {TEST_DATA_FILE}")


if __name__ == "__main__":
    main()
