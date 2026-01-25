"""
Feature pipeline for phishing detection model.
Combines text features (TF-IDF) with numeric and categorical features.
"""
from sklearn.pipeline import Pipeline
from sklearn.compose import ColumnTransformer
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.preprocessing import OneHotEncoder, StandardScaler
from xgboost import XGBClassifier
import pandas as pd
import numpy as np

# Define feature columns
TEXT_COL = 'text'
NUMERIC_COLS = ['has_attachment', 'links_count', 'urgent_keywords']
CATEGORICAL_COLS = ['sender_domain']
FEATURE_COLS = [TEXT_COL] + NUMERIC_COLS + CATEGORICAL_COLS


def build_feature_pipeline():
    """
    Build feature extraction + classifier pipeline.
    
    The pipeline combines:
    1. TF-IDF vectorization for text features
    2. Standard scaling for numeric features  
    3. One-hot encoding for categorical features
    
    Returns:
        sklearn Pipeline object ready for training
    """
    
    # Text feature extraction
    text_pipeline = Pipeline([
        ('tfidf', TfidfVectorizer(
            max_features=5000,
            ngram_range=(1, 2),
            lowercase=True,
            stop_words="english"
        ))
    ])
    
    # Numeric feature scaling
    numeric_pipeline = Pipeline([
        ('scaler', StandardScaler())
    ])
    
    # Categorical feature encoding
    categorical_pipeline = Pipeline([
        ('onehot', OneHotEncoder(
            handle_unknown='ignore',
            sparse_output=False
        ))
    ])
    
    # Combine all feature transformers
    preprocessor = ColumnTransformer(
        transformers=[
            ('text', text_pipeline, TEXT_COL),
            ('numeric', numeric_pipeline, NUMERIC_COLS),
            ('categorical', categorical_pipeline, CATEGORICAL_COLS)
        ],
        remainder='drop'  # Drop any columns not specified
    )
    
    # XGBoost classifier
    clf = XGBClassifier(
        n_estimators=200,
        max_depth=6,
        learning_rate=0.1,
        subsample=0.8,
        colsample_bytree=0.8,
        eval_metric="logloss",
        use_label_encoder=False,
        random_state=42
    )
    
    # Full pipeline
    pipeline = Pipeline(
        steps=[
            ("preprocessor", preprocessor),
            ("clf", clf),
        ]
    )
    
    return pipeline


def prepare_features(
    text: str,
    has_attachment: int = 0,
    links_count: int = 0,
    sender_domain: str = "unknown",
    urgent_keywords: int = 0
) -> pd.DataFrame:
    """
    Prepare a single sample's features for prediction.
    
    Args:
        text: Normalized email text
        has_attachment: 0 or 1
        links_count: Number of links in email
        sender_domain: Domain of sender
        urgent_keywords: 0 or 1
        
    Returns:
        DataFrame with single row of features
    """
    return pd.DataFrame({
        TEXT_COL: [text],
        'has_attachment': [int(has_attachment)],
        'links_count': [int(links_count)],
        'sender_domain': [str(sender_domain)],
        'urgent_keywords': [int(urgent_keywords)]
    })


# Suspicious domain patterns commonly found in phishing
SUSPICIOUS_DOMAIN_PATTERNS = [
    'secure-', 'account-', 'login-', 'verify-', 'update-',
    'alert-', 'billing-', 'support-', '-security', '-alert',
    '-verify', '-confirm', 'paypal', 'amazon', 'microsoft',
    'apple', 'google', 'facebook', 'bank', 'netflix'
]


def calculate_domain_risk(domain: str) -> float:
    """
    Calculate risk score for sender domain.
    
    Args:
        domain: Sender's email domain
        
    Returns:
        Risk score between 0.0 and 1.0
    """
    if not domain or domain == "unknown":
        return 0.3  # Unknown domain has moderate risk
    
    domain_lower = domain.lower()
    
    # Check for suspicious patterns
    for pattern in SUSPICIOUS_DOMAIN_PATTERNS:
        if pattern in domain_lower:
            return 0.8  # High risk
    
    # Check for unusual TLDs
    suspicious_tlds = ['.xyz', '.top', '.click', '.link', '.info', '.biz']
    for tld in suspicious_tlds:
        if domain_lower.endswith(tld):
            return 0.6  # Moderate-high risk
    
    # Normal domains
    return 0.1  # Low risk


def calculate_links_risk(links_count: int) -> float:
    """
    Calculate risk score based on number of links.
    
    Args:
        links_count: Number of links in email
        
    Returns:
        Risk score between 0.0 and 1.0
    """
    if links_count == 0:
        return 0.0
    elif links_count == 1:
        return 0.2
    elif links_count <= 3:
        return 0.4
    elif links_count <= 5:
        return 0.6
    else:
        return 0.8  # Many links is suspicious


def calculate_ensemble_score(
    model_proba: float,
    urgent_keywords: int = 0,
    links_count: int = 0,
    sender_domain: str = "unknown",
    has_attachment: int = 0
) -> float:
    """
    Calculate ensemble score combining model probability with feature-based risk scores.
    
    Weights:
    - Model probability: 60%
    - Urgent keywords: 15%
    - Links risk: 15%
    - Domain risk: 10%
    
    Args:
        model_proba: Probability from ML model (0.0 to 1.0)
        urgent_keywords: 0 or 1
        links_count: Number of links
        sender_domain: Sender's domain
        has_attachment: 0 or 1 (currently not weighted)
        
    Returns:
        Ensemble score between 0.0 and 1.0
    """
    # Feature-based risk scores
    urgent_risk = float(urgent_keywords)  # 0 or 1
    links_risk = calculate_links_risk(links_count)
    domain_risk = calculate_domain_risk(sender_domain)
    
    # Weighted combination
    ensemble_score = (
        model_proba * 0.60 +      # Model prediction weight
        urgent_risk * 0.15 +       # Urgent keywords weight
        links_risk * 0.15 +        # Links risk weight
        domain_risk * 0.10         # Domain risk weight
    )
    
    # Clamp to [0, 1]
    return max(0.0, min(1.0, ensemble_score))

