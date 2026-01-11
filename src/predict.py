from __future__ import annotations
import argparse
from joblib import load
from .text_cleaning import normalize_text

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--model", default="models/model.joblib")
    ap.add_argument("--text", required=True, help="Raw email text/body")
    args = ap.parse_args()

    pkg = load(args.model)
    feat = pkg["feature_builder"]
    model = pkg["model"]
    thr = float(pkg.get("threshold", 0.5))

    text = normalize_text(args.text)
    X = feat.transform([text])
    proba = float(model.predict_proba(X)[:, 1][0])
    pred = int(proba >= thr)

    print({"pred": pred, "proba_phishing": round(proba, 6), "threshold": thr})

if __name__ == "__main__":
    main()
