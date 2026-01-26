# -*- coding: utf-8 -*-
"""Properly clean and prepare the dataset for training"""
import pandas as pd
import numpy as np

print("Loading original dataset with proper quoting...")
# Read with explicit quoting to handle multiline body content
df = pd.read_csv(
    'data/incoming/Merged_Dataset_Clean.csv',
    quoting=1,  # QUOTE_ALL
    on_bad_lines='skip',  # Skip problematic rows
    engine='python'
)

print(f"Loaded rows: {len(df):,}")
print(f"Columns: {list(df.columns)}")

# Convert label to numeric, coerce errors to NaN
df['label'] = pd.to_numeric(df['label'], errors='coerce')

# Check for valid labels
print(f"\nBefore cleaning:")
print(f"  Valid labels: {df['label'].notna().sum():,}")
print(f"  Invalid/NaN labels: {df['label'].isna().sum():,}")

# Keep only rows with valid labels (0.0 or 1.0)
df_clean = df[df['label'].isin([0.0, 1.0])].copy()
df_clean = df_clean.dropna(subset=['body', 'label'])

# Remove rows where body is too short (likely parsing errors)
df_clean = df_clean[df_clean['body'].str.len() > 10]

print(f"\nAfter cleaning:")
print(f"  Total rows: {len(df_clean):,}")
print(f"  Label distribution:")
print(df_clean['label'].value_counts())

# Save as proper CSV
output_path = 'data/incoming/Dataset_Ready.csv'
df_clean.to_csv(output_path, index=False, quoting=1)
print(f"\nSaved to: {output_path}")
