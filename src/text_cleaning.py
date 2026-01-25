import re
from bs4 import BeautifulSoup

_whitespace_re = re.compile(r"\s+")
_url_re = re.compile(r"(https?://\S+|www\.\S+)", re.IGNORECASE)
_email_re = re.compile(r"[\w\.-]+@([\w\.-]+\.\w+)", re.IGNORECASE)

# Urgent keywords commonly found in phishing emails
URGENT_KEYWORDS = [
    'urgent', 'immediately', 'action required', 'act now', 'suspend',
    'verify', 'confirm', 'expire', 'limited time', 'final notice',
    'warning', 'alert', 'security', 'locked', 'disabled', 'blocked',
    'unauthorized', 'suspicious', 'unusual', 'violation', 'risk',
    '24 hours', '48 hours', 'deadline', 'asap', 'important'
]

def strip_html(text: str) -> str:
    if text is None:
        return ""
    s = str(text)
    # If it looks like HTML, parse; otherwise return raw
    if "<" in s and ">" in s:
        try:
            return BeautifulSoup(s, "html.parser").get_text(separator=" ")
        except Exception:
            return s
    return s

def normalize_text(text: str) -> str:
    s = strip_html(text)
    s = s.replace("\x00", " ")
    s = _whitespace_re.sub(" ", s).strip()
    return s

def count_urls(text: str) -> int:
    if text is None:
        return 0
    return len(_url_re.findall(str(text)))

def has_url(text: str) -> int:
    return 1 if count_urls(text) > 0 else 0

def exclamation_count(text: str) -> int:
    if text is None:
        return 0
    return str(text).count("!")

def length_chars(text: str) -> int:
    if text is None:
        return 0
    return len(str(text))

def detect_urgent_keywords(text: str) -> int:
    """
    Detect if text contains urgent keywords commonly used in phishing.
    
    Args:
        text: Raw email text
        
    Returns:
        1 if urgent keywords found, 0 otherwise
    """
    if text is None:
        return 0
    text_lower = str(text).lower()
    for keyword in URGENT_KEYWORDS:
        if keyword in text_lower:
            return 1
    return 0

def extract_sender_domain(text: str) -> str:
    """
    Extract sender domain from email text.
    Looks for email addresses and extracts domain.
    
    Args:
        text: Raw email text
        
    Returns:
        Domain string or 'unknown'
    """
    if text is None:
        return "unknown"
    
    # Try to find email addresses
    matches = _email_re.findall(str(text))
    if matches:
        return matches[0].lower()
    
    return "unknown"

