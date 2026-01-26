from __future__ import annotations

import argparse
import hashlib
from pathlib import Path
import json

import pandas as pd
from joblib import dump
from sklearn.model_selection import train_test_split
from sklearn.metrics import classification_report

from .features import build_feature_pipeline, FEATURE_COLS, TEXT_COL, NUMERIC_COLS, CATEGORICAL_COLS
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

def ensure_feature_columns(df: pd.DataFrame, text_col: str = 'body') -> pd.DataFrame:
    """
    Ensure all required feature columns exist.
    Auto-extract features from email body when columns don't exist.
    
    Args:
        df: DataFrame with at least a text column
        text_col: Name of the text column to extract features from
    """
    from .text_cleaning import (
        count_urls, detect_urgent_keywords, extract_sender_domain,
        detect_attachment_mention, exclamation_count, length_chars
    )
    
    # Get text content for feature extraction
    text_content = df[text_col].astype(str) if text_col in df.columns else df.iloc[:, 0].astype(str)
    
    # Auto-extract has_attachment from body
    if 'has_attachment' not in df.columns:
        print("[AUTO] Extracting 'has_attachment' from email body...")
        df['has_attachment'] = text_content.apply(detect_attachment_mention)
    
    # Auto-extract links_count from body
    if 'links_count' not in df.columns:
        print("[AUTO] Extracting 'links_count' from email body...")
        df['links_count'] = text_content.apply(count_urls)
    
    # Auto-extract urgent_keywords from body
    if 'urgent_keywords' not in df.columns:
        print("[AUTO] Extracting 'urgent_keywords' from email body...")
        df['urgent_keywords'] = text_content.apply(detect_urgent_keywords)
    
    # Auto-extract sender_domain from body
    if 'sender_domain' not in df.columns:
        print("[AUTO] Extracting 'sender_domain' from email body...")
        df['sender_domain'] = text_content.apply(extract_sender_domain)
    
    # NEW: Auto-extract body_length
    if 'body_length' not in df.columns:
        print("[AUTO] Extracting 'body_length' from email body...")
        df['body_length'] = text_content.apply(length_chars)
    
    # NEW: Auto-extract exclamation_count
    if 'exclamation_count' not in df.columns:
        print("[AUTO] Extracting 'exclamation_count' from email body...")
        df['exclamation_count'] = text_content.apply(exclamation_count)
    
    # Convert types
    df['has_attachment'] = df['has_attachment'].fillna(0).astype(int)
    df['links_count'] = df['links_count'].fillna(0).astype(int)
    df['urgent_keywords'] = df['urgent_keywords'].fillna(0).astype(int)
    df['sender_domain'] = df['sender_domain'].fillna('unknown').astype(str)
    df['body_length'] = df['body_length'].fillna(0).astype(int)
    df['exclamation_count'] = df['exclamation_count'].fillna(0).astype(int)
    
    return df


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

    # 6. Ensure all feature columns exist (auto-extract from text)
    df = ensure_feature_columns(df, text_col)

    # 7. Create the 'text' column used by pipeline
    df[TEXT_COL] = df[text_col].astype(str)

    # 8. Select only needed columns
    required_cols = [label_col] + FEATURE_COLS
    df = df[required_cols].dropna()

    # 9. Normalize labels
    df[label_col] = df[label_col].apply(normalize_label)

    print("\nLabel distribution after normalization:")
    print(df[label_col].value_counts())

    print("\nFeature columns used:")
    for col in FEATURE_COLS:
        print(f"  - {col}")

    X = df[FEATURE_COLS]
    y = df[label_col]

    # 10. Train / test split
    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.2, stratify=y, random_state=42
    )

    print(f"\nTraining samples: {len(X_train)}")
    print(f"Testing samples: {len(X_test)}")

    # 11. Train model
    pipeline = build_feature_pipeline()
    pipeline.fit(X_train, y_train)

    # 12. Find optimal threshold using F1 score
    print("\nFinding optimal threshold...")
    y_proba = pipeline.predict_proba(X_test)[:, 1]
    
    best_threshold = 0.5
    best_f1 = 0.0
    
    for threshold in [0.3, 0.35, 0.4, 0.45, 0.5, 0.55, 0.6, 0.65, 0.7]:
        y_pred_thresh = (y_proba >= threshold).astype(int)
        from sklearn.metrics import f1_score
        f1 = f1_score(y_test, y_pred_thresh, average='weighted')
        print(f"  Threshold {threshold:.2f}: F1 = {f1:.4f}")
        if f1 > best_f1:
            best_f1 = f1
            best_threshold = threshold
    
    print(f"\n>>> Optimal threshold: {best_threshold} (F1 = {best_f1:.4f})")

    # 13. Evaluate with optimal threshold
    y_pred = (y_proba >= best_threshold).astype(int)
    print("\nClassification Report (with optimal threshold):")
    print(classification_report(y_test, y_pred))

    # 14. Save model
    out_dir = Path(args.out)
    out_dir.mkdir(parents=True, exist_ok=True)

    dump(
        {
            "model": pipeline,
            "threshold": best_threshold,
            "feature_cols": FEATURE_COLS,
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
                "feature_cols": FEATURE_COLS,
                "optimal_threshold": best_threshold,
                "optimal_f1_score": round(best_f1, 4),
                "label_distribution": y.value_counts().to_dict(),
            },
            f,
            indent=2,
        )

    print("\n==============================")
    print(" Model training completed")
    print("==============================")
    print(f"Datasets used     : {len(list(history.glob('dataset_*.csv')))}")
    print(f"Samples used      : {len(df)}")
    print(f"Feature cols      : {len(FEATURE_COLS)}")
    print(f"Optimal threshold : {best_threshold}")


if __name__ == "__main__":
    main()
