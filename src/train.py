# =============================================================
# train.py  —  Step 2: Train Multinomial NB model with TF-IDF
# Input  : ../data/dataset_preprocessed.csv
# Output : ../data/model_mnb.pkl, vectorizer.pkl, data_ujian.csv
# =============================================================

import pandas as pd
import joblib
from sklearn.model_selection import train_test_split, cross_val_score
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.naive_bayes import MultinomialNB
from sklearn.metrics import accuracy_score, classification_report, confusion_matrix
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
    vectorizer = TfidfVectorizer(ngram_range=(1, 2), sublinear_tf=True, min_df=2, max_df=0.95, max_features=50000)
    X_train_vec = vectorizer.fit_transform(X_train)
    X_test_vec  = vectorizer.transform(X_test)

    # 4. Oversampling
    ros = RandomOverSampler(random_state=RANDOM_STATE)
    X_train_bal, y_train_bal = ros.fit_resample(X_train_vec, y_train)

    # === CROSS VALIDATION ===
    cv_scores = cross_val_score(
        MultinomialNB(alpha=0.5),
        X_train_bal,
        y_train_bal,
        cv=5
    )

    print("\n=== CROSS VALIDATION ===")
    print("Skor tiap fold:", cv_scores)
    print(f"Rata-rata CV: {cv_scores.mean()*100:.2f}%")

    # 5. Training
    model = MultinomialNB(alpha=0.5)
    model.fit(X_train_bal, y_train_bal)

    # 6. Simpan model & data uji
    joblib.dump(model, MODEL_FILE)
    joblib.dump(vectorizer, VECTORIZER_FILE)

    df_test = pd.DataFrame({"text_processed": X_test, "Label": y_test})
    df_test.to_csv(TEST_DATA_FILE, index=False)

    # Evaluasi
    y_pred = model.predict(X_test_vec)

    print("\n=== EVALUASI MODEL ===")
    print("Distribusi setelah oversampling:", pd.Series(y_train_bal).value_counts().to_dict())

    # Accuracy
    acc = accuracy_score(y_test, y_pred)
    print(f"Akurasi: {acc*100:.2f}%")

    # Classification Report
    print("\nClassification Report:")
    print(classification_report(y_test, y_pred))

    # Confusion Matrix
    print("\nConfusion Matrix:")
    print(confusion_matrix(y_test, y_pred))

    # Hasil oversampling
    print(f"Model berhasil dilatih dengan {X_train_bal.shape[0]} data (setelah oversampling).")

if __name__ == "__main__":
    main()
