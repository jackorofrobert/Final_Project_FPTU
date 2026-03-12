from __future__ import annotations

import argparse
import json
from pathlib import Path

import pandas as pd
from joblib import load

from .text_cleaning import normalize_text, count_urls, detect_urgent_keywords, extract_sender_domain
from .features import prepare_features, calculate_ensemble_score
from .config import SUSPICIOUS_MARGIN

# Classification levels
CLASS_LEGITIMATE = "LEGITIMATE"
CLASS_SUSPICIOUS = "SUSPICIOUS"
CLASS_PHISHING = "PHISHING"


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
    suspicious_margin = float(pkg.get("suspicious_margin", SUSPICIOUS_MARGIN))

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
    
    # Extract full URLs and domains for risk scoring
    from .text_cleaning import extract_link_domains
    import re as _re
    urls = _re.findall(r'(https?://\S+|www\.\S+)', raw_text, _re.IGNORECASE)
    link_domains = extract_link_domains(raw_text)

    # Calculate ensemble score (now returns dict)
    ensemble_result = calculate_ensemble_score(
        model_proba=proba_phishing,
        urgent_keywords=int(X['urgent_keywords'].iloc[0]),
        links_count=int(X['links_count'].iloc[0]),
        sender_domain=X['sender_domain'].iloc[0],
        has_attachment=int(X['has_attachment'].iloc[0]),
        link_domains=link_domains,
        urls=urls,
    )
    
    ensemble_score = ensemble_result['ensemble_score']
    formula_details = ensemble_result['formula_details']
    
    # Multi-level classification based on how much score exceeds threshold
    if ensemble_score < threshold:
        classification = CLASS_LEGITIMATE
    elif ensemble_score < threshold + suspicious_margin:
        classification = CLASS_SUSPICIOUS
    else:
        classification = CLASS_PHISHING
    
    pred = 0 if classification == CLASS_LEGITIMATE else 1

    # Analyze suspicious segments
    suspicious_segments = analyze_suspicious_segments(raw_text, model, threshold)

    # Output JSON (for tool / API usage)
    if args.json:
        result = {
            "prediction": pred,
            "classification": classification,
            "proba_phishing": round(proba_phishing, 6),
            "ensemble_score": round(ensemble_score, 6),
            "threshold": threshold,
            "suspicious_margin": suspicious_margin,
            "formula_details": formula_details,
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
    print(f"Prediction     : {classification}")
    print(f"Model Prob     : {proba_phishing * 100:.2f} %")
    print(f"Ensemble Score : {ensemble_score * 100:.2f} %")
    print(f"Threshold      : {threshold} (SUSPICIOUS: {threshold} - {threshold + suspicious_margin}, PHISHING: > {threshold + suspicious_margin})")
    print("-" * 60)
    print("Extracted Features:")
    print(f"  - Links count    : {int(X['links_count'].iloc[0])}")
    print(f"  - Has attachment : {int(X['has_attachment'].iloc[0])}")
    print(f"  - Urgent keywords: {int(X['urgent_keywords'].iloc[0])}")
    print(f"  - Sender domain  : {X['sender_domain'].iloc[0]}")
    
    # ========== DETAILED SCORE BREAKDOWN from formula_details ==========
    fd = formula_details
    
    print("-" * 60)
    print("📊 CHI TIẾT TÍNH ĐIỂM (Score Breakdown):")
    print("-" * 60)
    print("Công thức: Ensemble = Model×70% + Urgent×12% + Links×10.5% + Sender×7.5%")
    print()
    print(f"  1. {fd['model']['description']}")
    print(f"  2. {fd['urgent_keywords']['description']}")
    print(f"  3. {fd['links']['description']}")
    print(f"  4. {fd['domain']['description']}")
    print("  " + "-" * 40)
    print(f"  → Ensemble Score: {ensemble_score:.4f} ({ensemble_score * 100:.2f}%)")
    
    print()
    print("🏷️ PHÂN LOẠI CHI TIẾT:")
    domain_info = fd['domain']
    links_info = fd['links']
    print(f"  - Sender Domain: {domain_info['domain_name']} → {domain_info['domain_type']}")
    print(f"    {domain_info['reason']}")
    print(f"  - Links: {links_info['count']} links, risk = {links_info['raw_score']:.2%}")
    
    # Show link details if available
    if links_info.get('details'):
        print(f"    Chi tiết links:")
        for ld in links_info['details']:
            print(f"      - {ld['url']} → {ld['type']} (risk: {ld['risk']}) - {ld['reason']}")
    
    print()
    # Multi-level classification explanation
    if classification == CLASS_LEGITIMATE:
        status_icon = "✅"
        explanation = f"{ensemble_score * 100:.2f}% < {threshold * 100:.0f}% (threshold)"
    elif classification == CLASS_SUSPICIOUS:
        status_icon = "⚠️"
        explanation = f"{threshold * 100:.0f}% ≤ {ensemble_score * 100:.2f}% < {(threshold + suspicious_margin) * 100:.0f}%"
    else:
        status_icon = "🚨"
        explanation = f"{ensemble_score * 100:.2f}% ≥ {(threshold + suspicious_margin) * 100:.0f}% (threshold + margin)"
    
    print(f"📌 Kết luận: {status_icon} {classification}")
    print(f"   {explanation}")
    
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
