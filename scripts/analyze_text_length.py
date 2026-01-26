# -*- coding: utf-8 -*-
"""Analyze relationship between email length and labels"""
import pandas as pd
import numpy as np

print("Loading dataset...")
df = pd.read_csv('data/incoming/Merged_Dataset.csv')

# Calculate body length
df['body_length'] = df['body'].astype(str).str.len()

print("\n" + "="*60)
print("EMAIL LENGTH ANALYSIS BY LABEL")
print("="*60)

# Group by label
print("\n--- LEGITIMATE EMAILS (label=0) ---")
legit = df[df['label'] == 0.0]
print(f"Count: {len(legit):,}")
print(f"Mean length: {legit['body_length'].mean():,.0f} chars")
print(f"Median length: {legit['body_length'].median():,.0f} chars")
print(f"Min: {legit['body_length'].min():,} | Max: {legit['body_length'].max():,}")

print("\n--- PHISHING EMAILS (label=1) ---")
phish = df[df['label'] == 1.0]
print(f"Count: {len(phish):,}")
print(f"Mean length: {phish['body_length'].mean():,.0f} chars")
print(f"Median length: {phish['body_length'].median():,.0f} chars")
print(f"Min: {phish['body_length'].min():,} | Max: {phish['body_length'].max():,}")

print("\n" + "="*60)
print("LENGTH DISTRIBUTION BY RANGES")
print("="*60)

# Create length buckets
bins = [0, 100, 500, 1000, 2000, 5000, 10000, 50000, float('inf')]
labels = ['<100', '100-500', '500-1K', '1K-2K', '2K-5K', '5K-10K', '10K-50K', '>50K']
df['length_range'] = pd.cut(df['body_length'], bins=bins, labels=labels)

# Cross-tab
print("\nCount by length range:")
print(pd.crosstab(df['length_range'], df['label'], margins=True))

print("\n" + "="*60)
print("PHISHING RATE BY EMAIL LENGTH")
print("="*60)
for length_range in labels:
    subset = df[df['length_range'] == length_range]
    if len(subset) > 0:
        phishing_rate = (subset['label'] == 1.0).mean() * 100
        print(f"{length_range:>10}: {phishing_rate:5.1f}% phishing ({len(subset):,} emails)")

print("\n" + "="*60)
print("EXTREMELY LONG EMAILS (>100K chars)")
print("="*60)
extreme = df[df['body_length'] > 100000]
print(f"Total: {len(extreme):,} emails")
if len(extreme) > 0:
    print(f"Phishing: {(extreme['label'] == 1.0).sum():,}")
    print(f"Legitimate: {(extreme['label'] == 0.0).sum():,}")
    print(f"Phishing rate: {(extreme['label'] == 1.0).mean() * 100:.1f}%")

print("\n" + "="*60)
print("RECOMMENDATION")
print("="*60)
median_overall = df['body_length'].median()
print(f"\nMedian email length: {median_overall:,.0f} chars")
print("\nFor model optimization, consider:")
print("1. Truncating emails to ~5000-10000 chars (keeps 75-90% of info)")
print("2. Or using text summarization for very long emails")
print("3. Current TF-IDF with max_features=5000 should handle most cases well")
