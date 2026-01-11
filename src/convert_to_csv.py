from __future__ import annotations
import argparse
from pathlib import Path
import pandas as pd
from .data_io import load_any

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--inp", required=True)
    ap.add_argument("--out", required=True)
    args = ap.parse_args()

    df = load_any(args.inp)
    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(out, index=False)
    print("Converted to:", out)

if __name__ == "__main__":
    main()
