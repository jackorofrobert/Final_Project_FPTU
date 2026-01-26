# -*- coding: utf-8 -*-
"""Check and clean the dataset for proper labels"""
import pandas as pd

print("Loading dataset...")
df = pd.read_csv('data/incoming/Merged_Dataset.csv')

print(f"Total rows: {len(df):,}")
print(f"Columns: {list(df.columns)}")

# Check label column
print("\n=== LABEL COLUMN CHECK ===")
print(f"Label dtype: {df['label'].dtype}")
print(f"\nUnique labels (first 20):")
print(df['label'].value_counts().head(20))

# Check for invalid labels (not 0.0 or 1.0)
valid_labels = [0.0, 1.0, 0, 1]
invalid_mask = ~df['label'].isin(valid_labels)
invalid_count = invalid_mask.sum()

print(f"\n=== INVALID LABELS ===")
print(f"Number of invalid labels: {invalid_count:,}")

if invalid_count > 0:
    print("\nSample of invalid labels:")
    print(df[invalid_mask]['label'].head(10))
    
    # Remove invalid rows
    print("\nCleaning dataset...")
    df_clean = df[~invalid_mask].copy()
    df_clean['label'] = pd.to_numeric(df_clean['label'], errors='coerce')
    df_clean = df_clean.dropna(subset=['label'])
    
    print(f"Clean dataset rows: {len(df_clean):,}")
    print(f"Removed: {len(df) - len(df_clean):,} rows")
    
    # Save cleaned dataset
    output_path = 'data/incoming/Merged_Dataset_Clean.csv'
    df_clean.to_csv(output_path, index=False)
    print(f"\nSaved cleaned dataset to: {output_path}")
    
    print("\n=== CLEANED LABEL DISTRIBUTION ===")
    print(df_clean['label'].value_counts())
else:
    print("All labels are valid!")
