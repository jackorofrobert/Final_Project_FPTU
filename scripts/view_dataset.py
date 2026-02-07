# -*- coding: utf-8 -*-
"""
Xem ngau nhien 10 dong co label=0 (Legitimate) va 10 dong co label=1 (Phishing)
Moi lan chay se in du lieu ngau nhien khac nhau tu dataset.

Chay script:
    python scripts/view_dataset.py
"""
import pandas as pd
import sys

# Set encoding for Windows console
sys.stdout.reconfigure(encoding='utf-8')

# Load dataset
print("Loading Dataset_Ready.csv...")
df = pd.read_csv('data/incoming/Dataset_Ready.csv')

print(f"\n{'='*70}")
print(f"DATASET INFO: {len(df):,} rows, {len(df.columns)} columns")
print(f"Columns: {list(df.columns)}")
print(f"{'='*70}")

# Separate by label
df_legitimate = df[df['label'] == 0]
df_phishing = df[df['label'] == 1]

print(f"\nTong so email hop le (label=0): {len(df_legitimate):,}")
print(f"Tong so email lua dao (label=1): {len(df_phishing):,}")

# Show 10 random rows of label 0 (Legitimate)
print(f"\n{'='*70}")
print("NGAU NHIEN 10 EMAIL HOP LE (Label = 0)")
print(f"{'='*70}")
random_legit = df_legitimate.sample(n=min(10, len(df_legitimate)))
for idx, (i, row) in enumerate(random_legit.iterrows(), 1):
    body = str(row['body'])
    body_preview = body[:100].replace('\n', ' ').replace('\r', '') + '...' if len(body) > 100 else body.replace('\n', ' ').replace('\r', '')
    print(f"\n[{idx}] Index: {i}")
    print(f"    Label: {int(row['label'])} (Legitimate)")
    print(f"    Body: {body_preview}")

# Show 10 random rows of label 1 (Phishing)
print(f"\n{'='*70}")
print("NGAU NHIEN 10 EMAIL LUA DAO (Label = 1)")
print(f"{'='*70}")
random_phishing = df_phishing.sample(n=min(10, len(df_phishing)))
for idx, (i, row) in enumerate(random_phishing.iterrows(), 1):
    body = str(row['body'])
    body_preview = body[:100].replace('\n', ' ').replace('\r', '') + '...' if len(body) > 100 else body.replace('\n', ' ').replace('\r', '')
    print(f"\n[{idx}] Index: {i}")
    print(f"    Label: {int(row['label'])} (Phishing)")
    print(f"    Body: {body_preview}")

# Show label distribution
print(f"\n{'='*70}")
print("PHAN PHOI LABEL")
print(f"{'='*70}")
print(df['label'].value_counts())
print(f"\nMoi lan chay script se hien thi du lieu ngau nhien khac nhau!")
