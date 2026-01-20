from __future__ import annotations

import argparse
import hashlib
from pathlib import Path
import json

import pandas as pd
from joblib import dump
from sklearn.model_selection import train_test_split
from sklearn.metrics import classification_report

from .features import build_feature_pipeline
from .label_utils import normalize_label
from .data_io import load_any


# =========================
# Utility functions
# =========================

def file_hash(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        while True:
            chunk = f.read(8192)
            if not chunk:
                break
            h.update(chunk)
    return h.hexdigest()[:16]


def build_text_column(df: pd.DataFrame, preferred: str) -> str:
    """
    Ensure a text column exists.
    Priority:
    1. Preferred column (if exists)
    2. subject + email_text
    3. email_text
    4. subject
    """
    cols = [c.lower() for c in df.columns]

    if preferred in cols:
        return preferred

    if "subject" in cols and "email_text" in cols:
        print("[AUTO] Build text from subject + email_text")
        df["__text__"] = (
            df["subject"].astype(str) + " " + df["email_text"].astype(str)
        )
        return "__text__"

    if "email_text" in cols:
        print("[AUTO] Use email_text as text")
        return "email_text"

    if "subject" in cols:
        print("[AUTO] Use subject as text")
        return "subject"

    raise KeyError(
        f"No usable text columns found. Available columns: {list(df.columns)}"
    )


def resolve_label_column(df: pd.DataFrame, preferred: str) -> str:
    cols = [c.lower() for c in df.columns]

    if preferred in cols:
        return preferred

    common_label_cols = [
        "label", "class", "target", "category", "type"
    ]

    for c in common_label_cols:
        if c in cols:
            print(f"[AUTO] Label column mapped -> '{c}'")
            return c

    raise KeyError(
        f"No label column found. Available columns: {list(df.columns)}"
    )


def cache_incoming_datasets(incoming: Path, history: Path):
    history.mkdir(parents=True, exist_ok=True)

    for f in incoming.iterdir():
        if not f.is_file():
            continue
        if f.suffix.lower() not in [".csv", ".xlsx"]:
            continue

        h = file_hash(f)
        cached = history / f"dataset_{h}.csv"

        if cached.exists():
            print(f"[SKIP] Dataset already cached: {f.name}")
            continue

        print(f"[CACHE] New dataset detected: {f.name}")
        df = load_any(f)
        df.to_csv(cached, index=False, encoding="utf-8")
        print(f"        -> cached as {cached.name}")


def load_history_datasets(history: Path) -> pd.DataFrame:
    frames = []

    for f in history.glob("dataset_*.csv"):
        print(f"[LOAD] {f.name}")
        frames.append(pd.read_csv(f))

    if not frames:
        raise RuntimeError("No datasets found in history directory")

    return pd.concat(frames, ignore_index=True)


# =========================
# Main training logic
# =========================

def main():
    parser = argparse.ArgumentParser(
        description="Train phishing detection model with dataset memory"
    )
    parser.add_argument("--data-dir", required=True, help="Data directory")
    parser.add_argument("--text-col", required=True, help="Preferred text column name")
    parser.add_argument("--label-col", required=True, help="Preferred label column name")
    parser.add_argument("--out", default="models", help="Output directory")

    args = parser.parse_args()

    data_dir = Path(args.data_dir)
    incoming = data_dir / "incoming"
    history = data_dir / "history"

    if not incoming.exists():
        raise FileNotFoundError("incoming folder not found")

    # 1. Cache all incoming datasets
    cache_incoming_datasets(incoming, history)

    # 2. Load all historical datasets
    df = load_history_datasets(history)

    # 3. Normalize column names
    df.columns = [c.strip().lower() for c in df.columns]

    # 4. Resolve / build text column
    text_col = build_text_column(df, args.text_col.lower())

    # 5. Resolve label column
    label_col = resolve_label_column(df, args.label_col.lower())

    df = df[[text_col, label_col]].dropna()

    # 6. Normalize labels
    df[label_col] = df[label_col].apply(normalize_label)

    print("\nLabel distribution after normalization:")
    print(df[label_col].value_counts())

    X = df[text_col].astype(str)
    y = df[label_col]

    # 7. Train / test split
    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.2, stratify=y, random_state=42
    )

    # 8. Train model
    pipeline = build_feature_pipeline()
    pipeline.fit(X_train, y_train)

    # 9. Evaluate
    y_pred = pipeline.predict(X_test)
    print("\nClassification Report:")
    print(classification_report(y_test, y_pred))

    # 10. Save model
    out_dir = Path(args.out)
    out_dir.mkdir(parents=True, exist_ok=True)

    dump(
        {
            "model": pipeline,
            "threshold": 0.5,
            "label_mapping": {
                "1": "phishing",
                "0": "legitimate"
            }
        },
        out_dir / "model.joblib"
    )

    with open(out_dir / "metadata.json", "w", encoding="utf-8") as f:
        json.dump(
            {
                "num_datasets": len(list(history.glob("dataset_*.csv"))),
                "num_samples": len(df),
                "label_distribution": y.value_counts().to_dict(),
            },
            f,
            indent=2,
        )

    print("\n==============================")
    print(" Model training completed")
    print("==============================")
    print(f"Datasets used : {len(list(history.glob('dataset_*.csv')))}")
    print(f"Samples used  : {len(df)}")


if __name__ == "__main__":
    main()
