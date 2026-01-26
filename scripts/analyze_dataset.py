# -*- coding: utf-8 -*-
import pandas as pd

# Read dataset
print("Loading dataset...")
df = pd.read_csv('data/incoming/Merged_Dataset.csv')

print("\n" + "="*50)
print("DATASET STATISTICS")
print("="*50)

print(f"\nTotal emails: {len(df):,}")
print(f"Columns: {list(df.columns)}")

print("\n" + "-"*50)
print("LABEL DISTRIBUTION")
print("-"*50)
label_counts = df['label'].value_counts()
print(label_counts)

print("\n" + "-"*50)
print("LABEL PERCENTAGE")
print("-"*50)
label_pct = df['label'].value_counts(normalize=True) * 100
for label, pct in label_pct.items():
    label_name = "Legitimate (0)" if label == 0.0 else "Phishing (1)"
    print(f"{label_name}: {pct:.2f}%")

print("\n" + "-"*50)
print("EMAIL BODY LENGTH STATISTICS")
print("-"*50)
df['body_length'] = df['body'].astype(str).str.len()
print(df['body_length'].describe())

print("\n" + "-"*50)
print("SAMPLE PHISHING EMAILS (label=1)")
print("-"*50)
phishing = df[df['label'] == 1.0]
if len(phishing) > 0:
    print(f"Total phishing emails: {len(phishing):,}")
    print("\n--- Sample 1 ---")
    print(phishing['body'].iloc[0][:500] + "..." if len(str(phishing['body'].iloc[0])) > 500 else phishing['body'].iloc[0])
    if len(phishing) > 1:
        print("\n--- Sample 2 ---")
        print(phishing['body'].iloc[1][:500] + "..." if len(str(phishing['body'].iloc[1])) > 500 else phishing['body'].iloc[1])
    if len(phishing) > 2:
        print("\n--- Sample 3 ---")
        print(phishing['body'].iloc[2][:500] + "..." if len(str(phishing['body'].iloc[2])) > 500 else phishing['body'].iloc[2])
else:
    print("No phishing emails found in dataset")

print("\n" + "-"*50)
print("SAMPLE LEGITIMATE EMAILS (label=0)")  
print("-"*50)
legit = df[df['label'] == 0.0]
if len(legit) > 0:
    print(f"Total legitimate emails: {len(legit):,}")
    print("\n--- Sample 1 ---")
    print(legit['body'].iloc[0][:500] + "..." if len(str(legit['body'].iloc[0])) > 500 else legit['body'].iloc[0])
