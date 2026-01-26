def normalize_label(value):
    """
    Normalize any label representation to binary:
    1 = phishing
    0 = legitimate / benign
    """
    if value is None:
        raise ValueError("Label is None")

    v = str(value).strip().lower()

    # Positive / phishing labels
    phishing_keywords = {
        "phishing", "phising", "spam", "scam",
        "malicious", "fraud", "attack", "1", "1.0", "true", "yes"
    }

    # Negative / legitimate labels
    legitimate_keywords = {
        "legitimate", "legit", "benign", "ham",
        "normal", "safe", "clean", "0", "0.0", "false", "no"
    }

    if v in phishing_keywords:
        return 1

    if v in legitimate_keywords:
        return 0

    raise ValueError(f"Unknown label value: {value}")
