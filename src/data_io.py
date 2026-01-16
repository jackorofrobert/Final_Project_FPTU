from __future__ import annotations
import json
import hashlib
import shutil
from pathlib import Path
from typing import Iterable, Optional, Tuple, List

import pandas as pd

from .config import TEXT_COL_CANDIDATES, LABEL_COL_CANDIDATES

def _safe_read_csv(path: Path) -> pd.DataFrame:
    # Robust CSV reader for Windows/Excel messy files
    # - sep=None + engine=python => auto delimiter sniff
    # - on_bad_lines=skip => skip broken rows
    # - encoding fallback
    try:
        return pd.read_csv(path, encoding="utf-8", sep=None, engine="python", on_bad_lines="skip")
    except UnicodeDecodeError:
        return pd.read_csv(path, encoding="latin1", sep=None, engine="python", on_bad_lines="skip")
    except Exception:
        # last resort: try common separators
        for sep in [",", ";", "\t", "|"]:
            try:
                return pd.read_csv(path, encoding="latin1", sep=sep, engine="python", on_bad_lines="skip")
            except Exception:
                continue
        raise

def load_any(path: str | Path) -> pd.DataFrame:
    p = Path(path)
    suffix = p.suffix.lower()

    if suffix in [".csv", ".tsv", ".txt"]:
        return _safe_read_csv(p)
    if suffix in [".xlsx", ".xls"]:
        # requires openpyxl (xlsx)
        return pd.read_excel(p)
    if suffix in [".json"]:
        # Supports JSON lines or normal JSON list
        try:
            return pd.read_json(p, lines=True)
        except Exception:
            with open(p, "r", encoding="utf-8", errors="ignore") as f:
                obj = json.load(f)
            return pd.DataFrame(obj)

    raise ValueError(f"Unsupported file type: {p.name}")

def normalize_columns(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    df.columns = [str(c).strip().lower() for c in df.columns]
    return df

def auto_detect_columns(df: pd.DataFrame, text_col: Optional[str], label_col: Optional[str]) -> Tuple[str, str]:
    cols = [c.lower().strip() for c in df.columns]

    def pick(candidates: List[str]) -> Optional[str]:
        for cand in candidates:
            if cand in cols:
                return cand
        return None

    t = (text_col or "").strip().lower() if text_col else None
    l = (label_col or "").strip().lower() if label_col else None

    if not t:
        t = pick(TEXT_COL_CANDIDATES)
    if not l:
        l = pick(LABEL_COL_CANDIDATES)

    # Fallback heuristics:
    # - text col: first object/string-like col with longest avg length
    if not t:
        obj_cols = [c for c in cols if df[c].dtype == "object"]
        if not obj_cols:
            raise ValueError("Could not auto-detect text column (no object columns found). Use --text-col.")
        avg_len = {c: df[c].astype(str).map(len).mean() for c in obj_cols}
        t = max(avg_len, key=avg_len.get)

    # - label col: first numeric/bool col with <= 10 unique values
    if not l:
        cand_cols = []
        for c in cols:
            s = df[c]
            nunq = s.nunique(dropna=True)
            if nunq <= 10:
                cand_cols.append(c)
        if cand_cols:
            # prefer numeric-like
            for c in cand_cols:
                if pd.api.types.is_numeric_dtype(df[c]) or pd.api.types.is_bool_dtype(df[c]):
                    l = c
                    break
            l = l or cand_cols[0]

    if not l:
        raise ValueError("Could not auto-detect label column. Use --label-col.")

    return t, l

def coerce_label(y: pd.Series) -> pd.Series:
    # Convert common label formats to {0,1}
    y2 = y.copy()

    if y2.dtype == "object":
        y2 = y2.astype(str).str.strip().str.lower()
        mapping = {
            "1": 1, "0": 0,
            "phishing": 1, "spam": 1, "malicious": 1, "fraud": 1,
            "benign": 0, "legit": 0, "legitimate": 0, "ham": 0, "normal": 0
        }
        y2 = y2.map(lambda v: mapping.get(v, v))
    y2 = pd.to_numeric(y2, errors="coerce")
    y2 = y2.fillna(0).astype(int)
    y2 = y2.map(lambda v: 1 if v != 0 else 0)
    return y2

def file_fingerprint(path: Path, max_bytes: int = 2_000_000) -> str:
    # hash of file content (first max_bytes) to avoid duplicates
    h = hashlib.sha256()
    with open(path, "rb") as f:
        h.update(f.read(max_bytes))
    return h.hexdigest()[:16]

def is_dataset_file(p: Path) -> bool:
    return p.is_file() and p.suffix.lower() in [".csv", ".tsv", ".txt", ".xlsx", ".xls", ".json"]

def list_dataset_files(data_dir: Path, exclude_dirs: Iterable[Path]) -> List[Path]:
    exclude_dirs = {d.resolve() for d in exclude_dirs}
    files: List[Path] = []
    for p in data_dir.rglob("*"):
        if not is_dataset_file(p):
            continue
        # exclude if inside any excluded dir
        rp = p.resolve()
        if any(str(rp).startswith(str(ed)) for ed in exclude_dirs):
            continue
        files.append(p)
    return sorted(files)

def cache_to_history(files: List[Path], history_dir: Path) -> List[Path]:
    """
    Copy datasets into history_dir with hashed filenames so even if user deletes originals,
    the system retains a copy.
    """
    history_dir.mkdir(parents=True, exist_ok=True)
    cached_paths: List[Path] = []

    for f in files:
        fp = file_fingerprint(f)
        dst = history_dir / f"{f.stem}__{fp}{f.suffix.lower()}"
        if not dst.exists():
            shutil.copy2(f, dst)
        cached_paths.append(dst)
    return cached_paths
