from __future__ import annotations
import argparse
import json
from pathlib import Path

import numpy as np
import pandas as pd
from joblib import dump

from sklearn.model_selection import train_test_split
from sklearn.metrics import f1_score, roc_auc_score, confusion_matrix, classification_report

from xgboost import XGBClassifier

from .config import (
    DATA_DIR_DEFAULT, INCOMING_DIR, HISTORY_DIR,
    MODELS_DIR, RANDOM_SEED, DEFAULT_THRESHOLD
)
from .data_io import (
    load_any, normalize_columns, auto_detect_columns, coerce_label,
    list_dataset_files, cache_to_history
)
from .features import FeatureBuilder


def load_all_from_folder(data_dir: Path) -> pd.DataFrame:
    """
    Read all dataset files under data_dir EXCEPT history (to avoid double).
    Also, ensure datasets are cached into history for "memory".
    """
    data_dir = data_dir.resolve()
    incoming = (data_dir / "incoming").resolve()
    history = (data_dir / "history").resolve()

    incoming.mkdir(parents=True, exist_ok=True)
    history.mkdir(parents=True, exist_ok=True)

    # 1) Files currently present (incoming + other places under data_dir excluding history)
    current_files = list_dataset_files(data_dir, exclude_dirs=[history])

    # 2) Cache everything we can into history (so deletion of originals won't matter later)
    cached_now = cache_to_history(current_files, history_dir=history)

    # 3) Load ALL history + current (but history already has copies, so just load history to be safe)
    history_files = list_dataset_files(history, exclude_dirs=[])

    if not history_files:
        raise ValueError(
            "No datasets found. Put datasets into data/incoming/ (csv/xlsx/json) then train again."
        )

    dfs = []
    for f in history_files:
        df = load_any(f)
        df = normalize_columns(df)
        dfs.append(df)

    return pd.concat(dfs, ignore_index=True)


def build_model() -> XGBClassifier:
    # Sensible defaults for text classification
    return XGBClassifier(
        n_estimators=400,
        max_depth=6,
        learning_rate=0.08,
        subsample=0.9,
        colsample_bytree=0.8,
        reg_lambda=1.0,
        reg_alpha=0.0,
        min_child_weight=1.0,
        objective="binary:logistic",
        eval_metric="logloss",
        n_jobs=0,
        random_state=RANDOM_SEED
    )


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--data", default=None, help="Path to a single dataset file (csv/xlsx/json)")
    ap.add_argument("--data-dir", default=str(DATA_DIR_DEFAULT), help="Folder containing datasets (default: data/)")
    ap.add_argument("--text-col", default=None, help="Name of the text column (optional auto-detect)")
    ap.add_argument("--label-col", default=None, help="Name of the label column (optional auto-detect)")
    ap.add_argument("--threshold", type=float, default=DEFAULT_THRESHOLD, help="Decision threshold")
    ap.add_argument("--model-out", default=str(MODELS_DIR / "model.joblib"), help="Output model path")
    args = ap.parse_args()

    if args.data:
        df = load_any(args.data)
        df = normalize_columns(df)
        # also cache that dataset into history for memory
        data_dir = Path(args.data_dir)
        HISTORY_DIR.mkdir(parents=True, exist_ok=True)
        cache_to_history([Path(args.data)], history_dir=HISTORY_DIR)
    else:
        df = load_all_from_folder(Path(args.data_dir))

    text_col, label_col = auto_detect_columns(df, args.text_col, args.label_col)

    X_text = df[text_col].astype(str).fillna("")
    y = coerce_label(df[label_col])

    # Drop empties
    mask = X_text.str.strip().ne("") & y.notna()
    X_text = X_text[mask].tolist()
    y = y[mask].astype(int).tolist()

    if len(set(y)) < 2:
        raise ValueError("Training data must contain both classes (0 and 1).")

    X_train, X_test, y_train, y_test = train_test_split(
        X_text, y, test_size=0.2, random_state=RANDOM_SEED, stratify=y
    )

    feat = FeatureBuilder(max_features=50000, ngram_range=(1, 2), min_df=2, use_numeric=True)
    Xtr = feat.fit_transform(X_train)
    Xte = feat.transform(X_test)

    model = build_model()

    # handle imbalance
    pos = sum(y_train)
    neg = len(y_train) - pos
    if pos > 0:
        model.set_params(scale_pos_weight=max(1.0, neg / pos))

    model.fit(Xtr, np.array(y_train, dtype=int))

    proba = model.predict_proba(Xte)[:, 1]
    pred = (proba >= args.threshold).astype(int)

    f1 = float(f1_score(y_test, pred))
    try:
        auc = float(roc_auc_score(y_test, proba))
    except Exception:
        auc = None

    cm = confusion_matrix(y_test, pred).tolist()
    report = classification_report(y_test, pred, digits=4)

    metadata = {
        "text_col": text_col,
        "label_col": label_col,
        "threshold": args.threshold,
        "f1": f1,
        "roc_auc": auc,
        "confusion_matrix": cm,
        "n_samples": len(y),
        "n_train": len(y_train),
        "n_test": len(y_test),
        "notes": "Dataset memory implemented via data/history cache; training uses accumulated datasets."
    }

    MODELS_DIR.mkdir(parents=True, exist_ok=True)
    model_out = Path(args.model_out)
    model_out.parent.mkdir(parents=True, exist_ok=True)

    bundle = {
        "feature_builder": feat,
        "model": model,
        "threshold": args.threshold,
        "text_col": text_col,
        "label_col": label_col
    }

    dump(bundle, model_out)

    meta_path = model_out.parent / "metadata.json"
    meta_path.write_text(json.dumps(metadata, indent=2), encoding="utf-8")

    print("=== TRAINING DONE ===")
    print(f"Samples: {metadata['n_samples']} (train={metadata['n_train']}, test={metadata['n_test']})")
    print(f"Detected columns: text_col='{text_col}', label_col='{label_col}'")
    print(f"F1: {f1:.4f}")
    if auc is not None:
        print(f"ROC-AUC: {auc:.4f}")
    print("Confusion Matrix:", cm)
    print("\nClassification Report:\n", report)
    print(f"\nSaved model: {model_out}")
    print(f"Saved metadata: {meta_path}")
    print("\nDataset memory: cached datasets are stored in data/history/ (do not delete if you want memory).")


if __name__ == "__main__":
    main()
