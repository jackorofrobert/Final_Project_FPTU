import re
from bs4 import BeautifulSoup

_ws = re.compile(r"\s+")
_url = re.compile(r"(https?://\S+|www\.\S+)", re.IGNORECASE)

def strip_html(text: str) -> str:
    if not isinstance(text, str):
        text = "" if text is None else str(text)
    if "<" in text and ">" in text:
        try:
            soup = BeautifulSoup(text, "lxml")
            text = soup.get_text(" ")
        except Exception:
            pass
    return text

def normalize_text(text: str) -> str:
    text = strip_html(text)
    text = text.replace("\x00", " ")
    text = _ws.sub(" ", text).strip()
    return text

def find_urls(text: str) -> list[str]:
    if not isinstance(text, str):
        return []
    return _url.findall(text)
