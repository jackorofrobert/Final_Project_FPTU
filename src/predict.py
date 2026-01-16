from __future__ import annotations
import argparse
import json
from pathlib import Path

from joblib import load

from .text_cleaning import normalize_text


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--model", default="models/model.joblib", help="Path to model.joblib")
    ap.add_argument("--text", required=True, help="Email content to classify")
    ap.add_argument("--json", action="store_true", help="Output JSON format")
    args = ap.parse_args()

    pkg = load(args.model)
    model = pkg["model"]
    feat = pkg["feature_builder"]
    thr = float(pkg.get("threshold", 0.5))

    text = args.text
    X = feat.transform([normalize_text(text)])
    proba = float(model.predict_proba(X)[0][1])
    pred = int(proba >= thr)

    label_str = "PHISHING" if pred == 1 else "BENIGN"
    pct = proba * 100.0

    if args.json:
        print(json.dumps({
            "pred": pred,
            "label": label_str,
            "proba_phishing": round(proba, 6),
            "threshold": thr
        }, ensure_ascii=False))
        return

    print("=" * 34)
    print(" Email Classification Result")
    print("-" * 34)
    print(f"Prediction : {label_str}")
    print(f"Probability: {pct:.2f} %")
    print(f"Threshold  : {thr}")
    print("=" * 34)


if __name__ == "__main__":
    main()
