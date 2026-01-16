from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent

DATA_DIR_DEFAULT = PROJECT_ROOT / "data"
INCOMING_DIR = DATA_DIR_DEFAULT / "incoming"
HISTORY_DIR = DATA_DIR_DEFAULT / "history"

MODELS_DIR = PROJECT_ROOT / "models"
MODELS_DIR.mkdir(parents=True, exist_ok=True)

RANDOM_SEED = 42
DEFAULT_THRESHOLD = 0.5

# Common column name candidates
TEXT_COL_CANDIDATES = [
    "body", "email_body", "content", "message", "text", "email_text", "mail", "raw_text"
]
LABEL_COL_CANDIDATES = [
    "label", "class", "target", "is_phishing", "phishing", "spam", "y"
]
