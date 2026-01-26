# -*- coding: utf-8 -*-
"""Analyze what patterns the model actually learns from the dataset"""
import pandas as pd
from sklearn.feature_extraction.text import TfidfVectorizer
import numpy as np

print("Loading dataset...")
df = pd.read_csv('data/incoming/Merged_Dataset.csv')
df = df.dropna()

print(f"Total emails: {len(df):,}")

# Fit TF-IDF 
print("\nFitting TF-IDF vectorizer...")
tfidf = TfidfVectorizer(
    max_features=5000,
    ngram_range=(1, 2),
    lowercase=True,
    stop_words="english"
)

X = tfidf.fit_transform(df['body'].astype(str))
feature_names = tfidf.get_feature_names_out()

print(f"Vocabulary size: {len(feature_names):,} unique words/phrases")

# Calculate average TF-IDF scores for each class
phishing_mask = df['label'] == 1.0
legit_mask = df['label'] == 0.0

phishing_tfidf = X[phishing_mask].mean(axis=0).A1
legit_tfidf = X[legit_mask].mean(axis=0).A1

# Find words more common in phishing emails
diff = phishing_tfidf - legit_tfidf

print("\n" + "="*60)
print("TOP 30 PHISHING INDICATORS (words more common in phishing)")
print("="*60)
phishing_indices = diff.argsort()[-30:][::-1]
for i, idx in enumerate(phishing_indices, 1):
    word = feature_names[idx]
    score = diff[idx]
    print(f"{i:2}. {word:30} (score: {score:.4f})")

print("\n" + "="*60)
print("TOP 30 LEGITIMATE INDICATORS (words more common in legitimate)")
print("="*60)
legit_indices = diff.argsort()[:30]
for i, idx in enumerate(legit_indices, 1):
    word = feature_names[idx]
    score = -diff[idx]
    print(f"{i:2}. {word:30} (score: {score:.4f})")

print("\n" + "="*60)
print("HOW THE MODEL GENERALIZES")
print("="*60)
print("""
When the model sees a NEW email like:
  "Verify your account now or it will be suspended"

It looks for patterns it learned:
  - 'verify' -> phishing indicator
  - 'account' -> phishing indicator  
  - 'suspended' -> phishing indicator (if in vocabulary)

Even though this EXACT email was never in training data,
the model recognizes the suspicious PATTERNS.

This is called GENERALIZATION - the model doesn't memorize,
it learns what makes an email suspicious.
""")

# Test with sample sentences
print("\n" + "="*60)
print("DEMO: Testing pattern matching on NEW sentences")
print("="*60)

test_sentences = [
    "Verify your account immediately to avoid suspension",
    "Click here to claim your prize of $10,000",
    "Meeting tomorrow at 3pm in conference room B",
    "Your password has expired, update it now",
    "Please find attached the quarterly report",
    "Congratulations! You have won a free iPhone"
]

print("\nTransforming test sentences...")
test_vectors = tfidf.transform(test_sentences)

for i, sentence in enumerate(test_sentences):
    # Get non-zero features for this sentence
    nonzero = test_vectors[i].nonzero()[1]
    if len(nonzero) > 0:
        matched_words = [feature_names[j] for j in nonzero]
        # Calculate "phishing score" based on matched words
        scores = [diff[j] for j in nonzero]
        avg_score = np.mean(scores)
        
        print(f"\nSentence: '{sentence}'")
        print(f"  Matched patterns: {matched_words[:10]}...")
        print(f"  Avg phishing score: {avg_score:.4f}")
        if avg_score > 0.001:
            print(f"  -> SUSPICIOUS (phishing patterns detected)")
        else:
            print(f"  -> LIKELY SAFE (legitimate patterns)")
