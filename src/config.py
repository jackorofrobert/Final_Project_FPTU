from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent

DATA_DIR_DEFAULT = PROJECT_ROOT / "data"
INCOMING_DIR = DATA_DIR_DEFAULT / "incoming"
HISTORY_DIR = DATA_DIR_DEFAULT / "history"

MODELS_DIR = PROJECT_ROOT / "models"
MODELS_DIR.mkdir(parents=True, exist_ok=True)

RANDOM_SEED = 42
DEFAULT_THRESHOLD = 0.5

# Multi-level classification margins
# SUSPICIOUS zone: threshold < score <= threshold + SUSPICIOUS_MARGIN
# PHISHING zone: score > threshold + SUSPICIOUS_MARGIN
SUSPICIOUS_MARGIN = 0.2  # 20% margin above threshold for suspicious classification

# Common column name candidates
TEXT_COL_CANDIDATES = [
    "body", "email_body", "content", "message", "text", "email_text", "mail", "raw_text"
]
LABEL_COL_CANDIDATES = [
    "label", "class", "target", "is_phishing", "phishing", "spam", "y"
]

# =============================================================================
# TRUSTED DOMAINS - WHITELIST CỦA BẠN
# =============================================================================
# Chỉ domain trong danh sách này mới được coi là TRUSTED (Risk = 0%)
# Tất cả domain khác sẽ là SUSPICIOUS (Risk = 50%)
# 
# Cách thêm domain:
#   'example.com',           # Domain chính
#   'mail.example.com',      # Subdomain cụ thể
# =============================================================================
TRUSTED_DOMAINS = [
    # Thêm domain của bạn ở đây, ví dụ:
    # 'company.com',
    # 'partner.vn',
    'spktfpt.online'
]

# URL Shortener domains - often used to hide malicious links
SHORTENER_DOMAINS = [
    'bit.ly', 'bitly.com', 'tinyurl.com', 'goo.gl', 't.co',
    'ow.ly', 'is.gd', 'buff.ly', 'j.mp', 'rb.gy',
    'cutt.ly', 'short.io', 'tiny.cc', 'shorturl.at',
]


