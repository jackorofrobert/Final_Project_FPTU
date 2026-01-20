from __future__ import annotations

import argparse
import json
from pathlib import Path

from joblib import load

from .text_cleaning import normalize_text


def read_file(path: Path) -> str:
    """
    Read email content from file (txt, eml, html).
    Ignore encoding errors to avoid crash.
    """
    try:
        return path.read_text(encoding="utf-8", errors="ignore")
    except Exception as e:
        raise RuntimeError(f"Cannot read file: {path}") from e


def main():
    parser = argparse.ArgumentParser(
        description="Phishing Email Detection - Prediction Module"
    )
    parser.add_argument(
        "--model",
        default="models/model.joblib",
        help="Path to trained model.joblib",
    )
    parser.add_argument(
        "--text",
        help="Raw email text to classify",
    )
    parser.add_argument(
        "--file",
        help="Path to email file (.txt, .eml, .html)",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Output result in JSON format",
    )

    args = parser.parse_args()

    # Validate input
    if not args.text and not args.file:
        raise ValueError("You must provide either --text or --file")

    if args.text and args.file:
        raise ValueError("Use only one of --text or --file")

    # Load email content
    if args.file:
        file_path = Path(args.file)
        if not file_path.exists():
            raise FileNotFoundError(f"File not found: {file_path}")
        raw_text = read_file(file_path)
    else:
        raw_text = args.text

    # Load model package
    pkg = load(args.model)
    model = pkg["model"]
    threshold = float(pkg.get("threshold", 0.5))

    # Preprocess & vectorize
    cleaned_text = normalize_text(raw_text)
    X = model.named_steps["features"].transform([cleaned_text])

    # Predict
    proba_phishing = float(model.named_steps["clf"].predict_proba(X)[0][1])
    pred = int(proba_phishing >= threshold)

    label_str = "PHISHING" if pred == 1 else "LEGITIMATE"

    # Output JSON (for tool / API usage)
    if args.json:
        print(
            json.dumps(
                {
                    "prediction": label_str,
                    "proba_phishing": round(proba_phishing, 6),
                    "threshold": threshold,
                },
                ensure_ascii=False,
                indent=2,
            )
        )
        return

    # Output CLI (human readable)
    print("=" * 36)
    print(" Email Classification Result")
    print("-" * 36)
    print(f"Prediction : {label_str}")
    print(f"Probability: {proba_phishing * 100:.2f} %")
    print(f"Threshold  : {threshold}")
    print("=" * 36)


if __name__ == "__main__":
    main()
