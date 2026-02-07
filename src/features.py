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
NUMERIC_COLS = ['has_attachment', 'links_count', 'urgent_keywords', 'body_length', 'exclamation_count']
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
    urgent_keywords: int = 0,
    body_length: int = 0,
    exclamation_count: int = 0
) -> pd.DataFrame:
    """
    Prepare a single sample's features for prediction.
    
    Args:
        text: Normalized email text
        has_attachment: 0 or 1
        links_count: Number of links in email
        sender_domain: Domain of sender
        urgent_keywords: 0 or 1
        body_length: Length of email body in characters
        exclamation_count: Number of exclamation marks
        
    Returns:
        DataFrame with single row of features
    """
    return pd.DataFrame({
        TEXT_COL: [text],
        'has_attachment': [int(has_attachment)],
        'links_count': [int(links_count)],
        'sender_domain': [str(sender_domain)],
        'urgent_keywords': [int(urgent_keywords)],
        'body_length': [int(body_length)],
        'exclamation_count': [int(exclamation_count)]
    })


# Domain Classification Types
DOMAIN_TYPE_TRUSTED = "TRUSTED"
DOMAIN_TYPE_CORPORATE = "CORPORATE"
DOMAIN_TYPE_SUSPICIOUS = "SUSPICIOUS"
DOMAIN_TYPE_UNKNOWN = "UNKNOWN"

# Link Classification Types
LINK_TYPE_TRUSTED = "TRUSTED"
LINK_TYPE_SHORTENER = "SHORTENER"
LINK_TYPE_IP_BASED = "IP_BASED"
LINK_TYPE_SUSPICIOUS = "SUSPICIOUS"
LINK_TYPE_NORMAL = "NORMAL"

# Risk scores for each type
DOMAIN_RISK_SCORES = {
    DOMAIN_TYPE_TRUSTED: 0.0,
    DOMAIN_TYPE_CORPORATE: 0.05,
    DOMAIN_TYPE_SUSPICIOUS: 0.8,
    DOMAIN_TYPE_UNKNOWN: 0.2,
}

LINK_RISK_SCORES = {
    LINK_TYPE_TRUSTED: 0.0,
    LINK_TYPE_SHORTENER: 0.6,
    LINK_TYPE_IP_BASED: 0.9,
    LINK_TYPE_SUSPICIOUS: 0.8,
    LINK_TYPE_NORMAL: 0.1,
}


def is_trusted_domain(domain: str, trusted_list: list = None) -> bool:
    """
    Check if domain or its parent domain is in trusted list.
    
    Args:
        domain: Domain to check
        trusted_list: List of trusted domains (uses config if None)
        
    Returns:
        True if domain is trusted
    """
    if not domain or domain == "unknown":
        return False
    
    if trusted_list is None:
        from .config import TRUSTED_DOMAINS
        trusted_list = TRUSTED_DOMAINS
    
    domain_lower = domain.lower()
    
    for trusted in trusted_list:
        # Exact match or subdomain match
        if domain_lower == trusted or domain_lower.endswith('.' + trusted):
            return True
    
    return False


def classify_domain(domain: str) -> tuple:
    """
    Classify domain into types with corresponding risk score.
    
    Logic đơn giản hóa:
    - TRUSTED: Chỉ những domain bạn tự thêm vào TRUSTED_DOMAINS
    - SUSPICIOUS: Tất cả domain còn lại (bao gồm UNKNOWN)
    
    Args:
        domain: Domain to classify
        
    Returns:
        Tuple of (domain_type, risk_score, reason)
    """
    from .config import TRUSTED_DOMAINS
    
    if not domain or domain == "unknown":
        return (DOMAIN_TYPE_SUSPICIOUS, 0.5, "Domain không xác định → nghi ngờ")
    
    domain_lower = domain.lower()
    
    # CHỈ TRUSTED nếu nằm trong danh sách bạn tự thêm
    if is_trusted_domain(domain_lower, TRUSTED_DOMAINS):
        return (DOMAIN_TYPE_TRUSTED, 0.0, f"Domain trong whitelist của bạn")
    
    # TẤT CẢ CÒN LẠI ĐỀU LÀ SUSPICIOUS
    return (DOMAIN_TYPE_SUSPICIOUS, 0.5, "Domain không trong whitelist → nghi ngờ")


def classify_link(url: str, domain: str = None) -> tuple:
    """
    Classify link into types with corresponding risk score.
    
    Args:
        url: Full URL to classify
        domain: Extracted domain (optional, will extract if not provided)
        
    Returns:
        Tuple of (link_type, risk_score, reason)
    """
    import re
    from .config import SHORTENER_DOMAINS, TRUSTED_DOMAINS
    
    if not url:
        return (LINK_TYPE_NORMAL, 0.1, "Link rỗng")
    
    url_lower = url.lower()
    
    # Check IP_BASED (highest risk)
    ip_pattern = r'https?://\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}'
    if re.search(ip_pattern, url_lower):
        return (LINK_TYPE_IP_BASED, 0.9, "Dùng địa chỉ IP thay vì domain")
    
    # Extract domain if not provided
    if domain is None:
        match = re.search(r'(?:https?://)?(?:www\.)?([^/\s?&#]+)', url_lower)
        if match:
            domain = match.group(1).split(':')[0]
    
    if not domain:
        return (LINK_TYPE_SUSPICIOUS, 0.8, "Không thể extract domain")
    
    domain_lower = domain.lower()
    
    # Check SHORTENER
    for shortener in SHORTENER_DOMAINS:
        if domain_lower == shortener or domain_lower.endswith('.' + shortener):
            return (LINK_TYPE_SHORTENER, 0.6, f"URL rút gọn ({shortener})")
    
    # Check TRUSTED
    if is_trusted_domain(domain_lower, TRUSTED_DOMAINS):
        return (LINK_TYPE_TRUSTED, 0.0, f"Link đến domain trusted")
    
    # Check SUSPICIOUS patterns in URL
    suspicious_url_patterns = [
        (r'login|signin|verify|confirm|secure|account', "Yêu cầu đăng nhập/xác minh"),
        (r'password|credential|ssn|credit', "Yêu cầu thông tin nhạy cảm"),
        (r'\.exe|\.zip|\.rar|\.scr', "Link tải file thực thi"),
    ]
    
    for pattern, reason in suspicious_url_patterns:
        if re.search(pattern, url_lower):
            return (LINK_TYPE_SUSPICIOUS, 0.7, reason)
    
    # Default: NORMAL
    return (LINK_TYPE_NORMAL, 0.1, "Link bình thường")


def calculate_domain_risk(domain: str) -> float:
    """
    Calculate risk score for sender domain.
    Uses classify_domain internally.
    
    Args:
        domain: Sender's email domain
        
    Returns:
        Risk score between 0.0 and 1.0
    """
    _, risk_score, _ = classify_domain(domain)
    return risk_score



def calculate_links_risk(links_count: int, link_domains: list = None, urls: list = None) -> float:
    """
    Calculate risk score based on links analysis.
    Uses classify_link for each URL if available.
    
    Args:
        links_count: Number of links in email
        link_domains: List of domains from URLs (optional)
        urls: List of full URLs (optional, for detailed classification)
        
    Returns:
        Risk score between 0.0 and 1.0
    """
    if links_count == 0:
        return 0.0
    
    # If we have URLs, classify each one and average the risk
    if urls and len(urls) > 0:
        total_risk = 0.0
        for url in urls:
            _, risk, _ = classify_link(url)
            total_risk += risk
        return total_risk / len(urls)
    
    # If we only have domain info, check trust ratio
    if link_domains and len(link_domains) > 0:
        total_risk = 0.0
        for domain in link_domains:
            if is_trusted_domain(domain):
                total_risk += 0.0  # Trusted = 0 risk
            else:
                # Check if it's a known shortener
                from .config import SHORTENER_DOMAINS
                is_shortener = any(domain.lower() == s or domain.lower().endswith('.' + s) 
                                   for s in SHORTENER_DOMAINS)
                if is_shortener:
                    total_risk += 0.6
                else:
                    total_risk += 0.1  # Normal domain
        return total_risk / len(link_domains)
    
    # Fallback: risk based on count only
    if links_count == 1:
        return 0.15
    elif links_count <= 3:
        return 0.25
    elif links_count <= 5:
        return 0.4
    else:
        return 0.6


def calculate_ensemble_score(
    model_proba: float,
    urgent_keywords: int = 0,
    links_count: int = 0,
    sender_domain: str = "unknown",
    has_attachment: int = 0,
    link_domains: list = None,
    urls: list = None
) -> float:
    """
    Calculate ensemble score combining model probability with feature-based risk scores.
    
    NEW FORMULA (simplified, no separate bonus):
    - Model probability: 70%
    - Urgent keywords: 12%
    - Links risk: 10.5%
    - Domain risk: 7.5%
    Total = 100%
    
    Trust is already factored into Links Risk and Domain Risk calculations,
    so no additional bonus multiplication is needed.
    
    Args:
        model_proba: Probability from ML model (0.0 to 1.0)
        urgent_keywords: 0 or 1
        links_count: Number of links
        sender_domain: Sender's domain
        has_attachment: 0 or 1 (currently not weighted)
        link_domains: List of domains extracted from URLs
        urls: List of full URLs (optional, for detailed classification)
        
    Returns:
        Ensemble score between 0.0 and 1.0
    """
    # Feature-based risk scores (trust is already factored in)
    urgent_risk = float(urgent_keywords)  # 0 or 1
    links_risk = calculate_links_risk(links_count, link_domains, urls)
    domain_risk = calculate_domain_risk(sender_domain)
    
    # NEW WEIGHTS:
    # - Model: 70% (increased from 60%)
    # - Urgent: 12% (decreased from 15%)
    # - Links: 10.5% (decreased from 15%)
    # - Domain: 7.5% (decreased from 10%)
    # Total = 100%
    ensemble_score = (
        model_proba * 0.70 +      # Model prediction weight
        urgent_risk * 0.12 +       # Urgent keywords weight
        links_risk * 0.105 +       # Links risk weight
        domain_risk * 0.075        # Domain risk weight
    )
    
    # No separate trusted bonus - trust is already in the component scores
    # This makes the formula linear and easier to explain
    
    # Clamp to [0, 1]
    return max(0.0, min(1.0, ensemble_score))


