import os

# Base directory = project root (d:\Tugas Akhir)
BASE_DIR = os.path.join(os.path.dirname(__file__), "..")
DATA_DIR = os.path.join(BASE_DIR, "data")
MODEL_DIR = os.path.join(BASE_DIR, "model")

# File paths
INPUT_FILE      = os.path.join(DATA_DIR, "dataset_TA.xlsx")
PREPROCESSED    = os.path.join(DATA_DIR, "dataset_preprocessed.csv")
MODEL_FILE      = os.path.join(MODEL_DIR, "model_mnb.pkl")
VECTORIZER_FILE = os.path.join(MODEL_DIR, "vectorizer.pkl")
TEST_DATA_FILE  = os.path.join(DATA_DIR, "data_ujian.csv")

# Shared settings
RANDOM_STATE = 42

# Emoji → sentiment token map
EMOJI_MAP = {
    "😡": " emosi_negatif ", "😠": " emosi_negatif ", "😤": " emosi_negatif ",
    "😞": " emosi_negatif ", "😢": " emosi_negatif ", "😭": " emosi_negatif ",
    "👎": " emosi_negatif ", "💔": " emosi_negatif ",
    "🙂": " emosi_positif ", "😊": " emosi_positif ", "😄": " emosi_positif ",
    "😁": " emosi_positif ", "😍": " emosi_positif ", "👍": " emosi_positif ",
    "❤️": " emosi_positif ",
}
