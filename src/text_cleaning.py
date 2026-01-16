import re
from bs4 import BeautifulSoup

_whitespace_re = re.compile(r"\s+")
_url_re = re.compile(r"(https?://\S+|www\.\S+)", re.IGNORECASE)

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
