from __future__ import annotations
import argparse, json
from pathlib import Path
import numpy as np
import pandas as pd
from joblib import dump
from sklearn.model_selection import train_test_split
from sklearn.metrics import classification_report, f1_score, roc_auc_score
from xgboost import XGBClassifier

from .config import TrainConfig
from .data_io import load_any, infer_columns, normalize_label_series
from .text_cleaning import normalize_text
from .features import FeatureBuilder

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--data", required=True, help="Path to dataset file (csv/json/jsonl/txt)")
    ap.add_argument("--text-col", default=None)
    ap.add_argument("--label-col", default=None)
    ap.add_argument("--out", default="models/model.joblib")
    args = ap.parse_args()

    cfg = TrainConfig(text_col=args.text_col, label_col=args.label_col)
    df = load_any(args.data)

    text_col, label_col = infer_columns(df, cfg.text_col, cfg.label_col)

    df = df[[text_col, label_col]].dropna()
    df[text_col] = df[text_col].astype(str).map(normalize_text)
    y = normalize_label_series(df[label_col])
    texts = df[text_col].tolist()

    X_train, X_test, y_train, y_test = train_test_split(
        texts, y, test_size=cfg.test_size, random_state=cfg.seed, stratify=y
    )

    feat = FeatureBuilder(cfg.max_features, cfg.ngram_range, cfg.min_df)
    Xtr = feat.fit_transform(X_train)
    Xte = feat.transform(X_test)

    model = XGBClassifier(
        n_estimators=cfg.n_estimators,
        learning_rate=cfg.learning_rate,
        max_depth=cfg.max_depth,
        subsample=cfg.subsample,
        colsample_bytree=cfg.colsample_bytree,
        reg_lambda=cfg.reg_lambda,
        reg_alpha=cfg.reg_alpha,
        tree_method="hist",
        eval_metric="logloss",
        n_jobs=-1
    )
    model.fit(Xtr, y_train)

    proba = model.predict_proba(Xte)[:, 1]
    pred = (proba >= 0.5).astype(int)

    metrics = {
        "f1": float(f1_score(y_test, pred)),
        "roc_auc": float(roc_auc_score(y_test, proba)),
        "report": classification_report(y_test, pred, output_dict=True)
    }
    print("F1:", metrics["f1"])
    print("ROC-AUC:", metrics["roc_auc"])

    out_path = Path(args.out)
    out_path.parent.mkdir(parents=True, exist_ok=True)

    package = {
        "feature_builder": feat,
        "model": model,
        "threshold": 0.5,
        "text_col_used": text_col,
        "label_col_used": label_col
    }
    dump(package, out_path)

    meta_path = out_path.parent / "metadata.json"
    meta_path.write_text(json.dumps(metrics, indent=2), encoding="utf-8")
    print("Saved:", out_path)
    print("Saved:", meta_path)

if __name__ == "__main__":
    main()
