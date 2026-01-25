from __future__ import annotations

import argparse
import json
from pathlib import Path

import pandas as pd
from joblib import load

from .text_cleaning import normalize_text, count_urls, detect_urgent_keywords, extract_sender_domain
from .features import prepare_features, calculate_ensemble_score


def read_file(path: Path) -> str:
    """
    Read email content from file (txt, eml, html).
    Ignore encoding errors to avoid crash.
    """
    try:
        return path.read_text(encoding="utf-8", errors="ignore")
    except Exception as e:
        raise RuntimeError(f"Cannot read file: {path}") from e


def extract_features_from_text(
    raw_text: str,
    has_attachment: int = None,
    links_count: int = None,
    sender_domain: str = None,
    urgent_keywords: int = None
) -> pd.DataFrame:
    """
    Extract features from raw email text.
    If features are not provided, auto-extract from text.
    
    Args:
        raw_text: Raw email content
        has_attachment: Override for attachment flag
        links_count: Override for link count
        sender_domain: Override for sender domain
        urgent_keywords: Override for urgent flag
        
    Returns:
        DataFrame with features ready for model
    """
    normalized_text = normalize_text(raw_text)
    
    # Auto-extract if not provided
    if links_count is None:
        links_count = count_urls(raw_text)
    
    if urgent_keywords is None:
        urgent_keywords = detect_urgent_keywords(raw_text)
    
    if sender_domain is None:
        sender_domain = extract_sender_domain(raw_text)
    
    if has_attachment is None:
        has_attachment = 0  # Cannot detect from text
    
    return prepare_features(
        text=normalized_text,
        has_attachment=has_attachment,
        links_count=links_count,
        sender_domain=sender_domain,
        urgent_keywords=urgent_keywords
    )


def analyze_suspicious_segments(raw_text: str, model, threshold: float = 0.5) -> list:
    """
    Analyze email text and find suspicious segments.
    
    Args:
        raw_text: Raw email text
        model: Trained model pipeline
        threshold: Score threshold for flagging as suspicious
        
    Returns:
        List of dicts with 'text' and 'score' for suspicious segments
    """
    import re
    from .text_cleaning import URGENT_KEYWORDS
    
    suspicious_segments = []
    
    # Split into sentences/lines
    lines = re.split(r'[.\n\r]+', raw_text)
    lines = [line.strip() for line in lines if line.strip() and len(line.strip()) > 10]
    
    for line in lines:
        # Check for urgent keywords
        line_lower = line.lower()
        found_keywords = []
        for keyword in URGENT_KEYWORDS:
            if keyword in line_lower:
                found_keywords.append(keyword)
        
        # Check for URLs
        url_pattern = r'(https?://\S+|www\.\S+)'
        urls = re.findall(url_pattern, line, re.IGNORECASE)
        
        # Calculate risk score for this segment
        risk_score = 0.0
        reasons = []
        
        # Urgent keywords contribute to risk
        if found_keywords:
            risk_score += 0.3 * min(len(found_keywords), 3)  # Max 0.9
            reasons.append(f"Từ khóa khẩn cấp: {', '.join(found_keywords[:3])}")
        
        # URLs contribute to risk
        if urls:
            risk_score += 0.2 * min(len(urls), 2)  # Max 0.4
            reasons.append(f"Chứa {len(urls)} link")
        
        # Suspicious patterns
        suspicious_patterns = [
            (r'click\s*(here|this|now)', 'Yêu cầu click'),
            (r'verify\s*(your|account)', 'Yêu cầu xác minh'),
            (r'(password|credit\s*card|ssn|bank)', 'Yêu cầu thông tin nhạy cảm'),
            (r'(suspended|locked|disabled|expired)', 'Cảnh báo tài khoản'),
            (r'(winner|prize|reward|gift|free)', 'Hứa hẹn phần thưởng'),
            (r'(\$\d+|money|cash)', 'Đề cập tiền bạc'),
        ]
        
        for pattern, reason in suspicious_patterns:
            if re.search(pattern, line_lower):
                risk_score += 0.15
                if reason not in reasons:
                    reasons.append(reason)
        
        # Cap at 1.0
        risk_score = min(risk_score, 1.0)
        
        # Only include if suspicious enough
        if risk_score >= 0.2 or found_keywords or urls:
            suspicious_segments.append({
                'text': line[:150] + ('...' if len(line) > 150 else ''),
                'score': round(risk_score * 100, 1),
                'reasons': reasons
            })
    
    # Sort by score descending
    suspicious_segments.sort(key=lambda x: x['score'], reverse=True)
    
    return suspicious_segments[:10]  # Top 10 most suspicious


def main():
    parser = argparse.ArgumentParser(
        description="Phishing Email Detection - Prediction Module"
    )
    parser.add_argument(
        "--model",
        default="models/model.joblib",
        help="Path to trained model.joblib",
    )
    parser.add_argument(
        "--text",
        help="Raw email text to classify",
    )
    parser.add_argument(
        "--file",
        help="Path to email file (.txt, .eml, .html)",
    )
    parser.add_argument(
        "--has-attachment",
        type=int,
        choices=[0, 1],
        help="Override: email has attachment (0 or 1)",
    )
    parser.add_argument(
        "--links-count",
        type=int,
        help="Override: number of links in email",
    )
    parser.add_argument(
        "--sender-domain",
        help="Override: sender's email domain",
    )
    parser.add_argument(
        "--urgent-keywords",
        type=int,
        choices=[0, 1],
        help="Override: contains urgent keywords (0 or 1)",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Output result in JSON format",
    )

    args = parser.parse_args()

    # Validate input
    if not args.text and not args.file:
        raise ValueError("You must provide either --text or --file")

    if args.text and args.file:
        raise ValueError("Use only one of --text or --file")

    # Load email content
    if args.file:
        file_path = Path(args.file)
        if not file_path.exists():
            raise FileNotFoundError(f"File not found: {file_path}")
        raw_text = read_file(file_path)
    else:
        raw_text = args.text

    # Load model package
    pkg = load(args.model)
    model = pkg["model"]
    threshold = float(pkg.get("threshold", 0.5))

    # Extract features
    X = extract_features_from_text(
        raw_text=raw_text,
        has_attachment=args.has_attachment,
        links_count=args.links_count,
        sender_domain=args.sender_domain,
        urgent_keywords=args.urgent_keywords
    )

    # Predict
    proba_phishing = float(model.predict_proba(X)[0][1])
    
    # Extract link domains for trusted check
    from .text_cleaning import extract_link_domains
    link_domains = extract_link_domains(raw_text)
    
    # Calculate ensemble score
    ensemble_score = calculate_ensemble_score(
        model_proba=proba_phishing,
        urgent_keywords=int(X['urgent_keywords'].iloc[0]),
        links_count=int(X['links_count'].iloc[0]),
        sender_domain=X['sender_domain'].iloc[0],
        has_attachment=int(X['has_attachment'].iloc[0]),
        link_domains=link_domains
    )
    
    # Use ensemble_score for final prediction
    pred = int(ensemble_score >= threshold)
    label_str = "PHISHING" if pred == 1 else "LEGITIMATE"

    # Analyze suspicious segments
    suspicious_segments = analyze_suspicious_segments(raw_text, model, threshold)

    # Output JSON (for tool / API usage)
    if args.json:
        result = {
            "prediction": label_str,
            "proba_phishing": round(proba_phishing, 6),
            "ensemble_score": round(ensemble_score, 6),
            "threshold": threshold,
            "features": {
                "links_count": int(X['links_count'].iloc[0]),
                "has_attachment": int(X['has_attachment'].iloc[0]),
                "urgent_keywords": int(X['urgent_keywords'].iloc[0]),
                "sender_domain": X['sender_domain'].iloc[0]
            },
            "suspicious_segments": suspicious_segments
        }
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return

    # Output CLI (human readable)
    print("=" * 60)
    print(" Email Classification Result")
    print("-" * 60)
    print(f"Prediction     : {label_str}")
    print(f"Model Prob     : {proba_phishing * 100:.2f} %")
    print(f"Ensemble Score : {ensemble_score * 100:.2f} %")
    print(f"Threshold      : {threshold}")
    print("-" * 60)
    print("Extracted Features:")
    print(f"  - Links count    : {int(X['links_count'].iloc[0])}")
    print(f"  - Has attachment : {int(X['has_attachment'].iloc[0])}")
    print(f"  - Urgent keywords: {int(X['urgent_keywords'].iloc[0])}")
    print(f"  - Sender domain  : {X['sender_domain'].iloc[0]}")
    
    # ========== DETAILED SCORE BREAKDOWN ==========
    from .features import calculate_links_risk, calculate_domain_risk, is_trusted_domain
    
    links_risk = calculate_links_risk(int(X['links_count'].iloc[0]), link_domains)
    domain_risk = calculate_domain_risk(X['sender_domain'].iloc[0])
    urgent_risk = float(X['urgent_keywords'].iloc[0])
    
    print("-" * 60)
    print("📊 CHI TIẾT TÍNH ĐIỂM (Score Breakdown):")
    print("-" * 60)
    print("Công thức: Ensemble = Model×60% + Urgent×15% + Links×15% + Domain×10%")
    print()
    print(f"  1. Model Probability : {proba_phishing:.4f} × 0.60 = {proba_phishing * 0.60:.4f}")
    print(f"  2. Urgent Keywords   : {urgent_risk:.4f} × 0.15 = {urgent_risk * 0.15:.4f}")
    print(f"  3. Links Risk        : {links_risk:.4f} × 0.15 = {links_risk * 0.15:.4f}")
    print(f"  4. Domain Risk       : {domain_risk:.4f} × 0.10 = {domain_risk * 0.10:.4f}")
    print("  " + "-" * 40)
    base_score = proba_phishing * 0.60 + urgent_risk * 0.15 + links_risk * 0.15 + domain_risk * 0.10
    print(f"  → Base Score (trước bonus): {base_score:.4f} ({base_score * 100:.2f}%)")
    
    # Show trust bonus calculation
    sender_is_trusted = is_trusted_domain(X['sender_domain'].iloc[0])
    links_are_trusted = False
    if link_domains and len(link_domains) > 0:
        trusted_count = sum(1 for d in link_domains if is_trusted_domain(d))
        trust_ratio = trusted_count / len(link_domains)
        links_are_trusted = trust_ratio >= 0.8
    
    print()
    print("🛡️ TRUSTED EMAIL BONUS:")
    print(f"  - Sender domain trusted? : {'✅ Có' if sender_is_trusted else '❌ Không'}")
    print(f"  - Links 80%+ trusted?    : {'✅ Có' if links_are_trusted else '❌ Không'}")
    if link_domains:
        trusted_count = sum(1 for d in link_domains if is_trusted_domain(d))
        print(f"    ({trusted_count}/{len(link_domains)} domains trusted = {100*trusted_count/len(link_domains):.1f}%)")
    
    if sender_is_trusted and links_are_trusted:
        print(f"  → Áp dụng: Giảm 40% (×0.6)")
        print(f"  → Final Score: {base_score:.4f} × 0.6 = {base_score * 0.6:.4f} ({base_score * 0.6 * 100:.2f}%)")
    elif sender_is_trusted or links_are_trusted:
        print(f"  → Áp dụng: Giảm 20% (×0.8)")
        print(f"  → Final Score: {base_score:.4f} × 0.8 = {base_score * 0.8:.4f} ({base_score * 0.8 * 100:.2f}%)")
    else:
        print(f"  → Không áp dụng bonus")
        print(f"  → Final Score: {base_score:.4f} ({base_score * 100:.2f}%)")
    
    print()
    print(f"📌 Kết luận: {ensemble_score * 100:.2f}% {'≥' if ensemble_score >= threshold else '<'} {threshold * 100:.0f}% → {label_str}")
    
    # Show suspicious segments
    if suspicious_segments:
        print("-" * 60)
        print("Suspicious Text Segments:")
        print("-" * 60)
        for i, seg in enumerate(suspicious_segments, 1):
            score = seg['score']
            # Color coding based on score
            if score >= 60:
                level = "🔴 HIGH"
            elif score >= 30:
                level = "🟠 MEDIUM"
            else:
                level = "🟡 LOW"
            
            print(f"\n[{i}] {level} - Score: {score}%")
            print(f"    Text: \"{seg['text']}\"")
            if seg['reasons']:
                print(f"    Reasons: {', '.join(seg['reasons'])}")
    else:
        print("-" * 60)
        print("No suspicious text segments detected.")
    
    print("=" * 60)


if __name__ == "__main__":
    main()
