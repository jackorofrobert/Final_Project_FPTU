from __future__ import annotations
import json
from pathlib import Path
import pandas as pd

TEXT_CANDIDATES = ["text", "body", "email", "content", "message", "mail", "raw", "email_body"]
LABEL_CANDIDATES = ["label", "class", "target", "is_phishing", "phishing", "spam", "category"]

def load_any(path):
    import pandas as pd

    try:
        return pd.read_csv(
            path,
            encoding="utf-8",
            sep=None,
            engine="python",
            on_bad_lines="skip"   # <<< QUAN TRỌNG NHẤT
        )
    except Exception:
        return pd.read_csv(
            path,
            encoding="latin1",
            sep=None,
            engine="python",
            on_bad_lines="skip"
        )


def _pick_col(df: pd.DataFrame, candidates: list[str]) -> str | None:
    cols = {c.lower(): c for c in df.columns}
    for name in candidates:
        if name in cols:
            return cols[name]
    return None

def infer_columns(df: pd.DataFrame, text_col: str | None, label_col: str | None) -> tuple[str, str]:
    # 1) user override
    if text_col and label_col:
        return text_col, label_col

    # 2) heuristic pick
    tc = text_col or _pick_col(df, TEXT_CANDIDATES)
    lc = label_col or _pick_col(df, LABEL_CANDIDATES)

    if tc is None:
        # fallback: pick the longest average string column
        obj_cols = [c for c in df.columns if df[c].dtype == "object"]
        if not obj_cols:
            raise ValueError("No text-like column found. Provide --text-col.")
        tc = max(obj_cols, key=lambda c: df[c].astype(str).str.len().mean())

    if lc is None:
        raise ValueError("No label column found. Provide --label-col (or dataset has no labels).")

    return tc, lc

def normalize_label_series(s: pd.Series) -> pd.Series:
    # map common label styles to 0/1 (0=benign, 1=phishing)
    def to01(x):
        if pd.isna(x):
            return None
        v = str(x).strip().lower()
        if v in ["1", "true", "phish", "phishing", "spam", "malicious", "scam"]:
            return 1
        if v in ["0", "false", "benign", "legit", "legitimate", "ham", "normal"]:
            return 0
        # numeric fallback
        try:
            n = int(float(v))
            return 1 if n != 0 else 0
        except Exception:
            return None

    out = s.map(to01)
    if out.isna().mean() > 0.2:
        raise ValueError("Too many labels could not be normalized. Check label mapping or provide custom mapping.")
    return out.astype(int)
