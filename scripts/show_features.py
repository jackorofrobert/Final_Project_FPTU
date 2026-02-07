# -*- coding: utf-8 -*-
"""
Script hiển thị chi tiết các features được trích xuất từ email.
Bao gồm phân loại chi tiết Domain và Link.

Chạy:
    python scripts/show_features.py --file samples/test.txt
    python scripts/show_features.py --text "Your email content here"
"""

import sys
import re
import argparse
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

# Set encoding for Windows console
if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8')


def read_file(path: Path) -> str:
    """Read file content with error handling"""
    try:
        return path.read_text(encoding="utf-8", errors="ignore")
    except Exception as e:
        raise RuntimeError(f"Cannot read file: {path}") from e


def extract_urls(text: str) -> list:
    """Extract all URLs from text"""
    url_pattern = r'(https?://[^\s<>"\']+|www\.[^\s<>"\']+)'
    return re.findall(url_pattern, text, re.IGNORECASE)


def show_features(raw_text: str, show_text_preview: bool = True):
    """
    Extract and display all features from email text.
    Includes detailed domain and link classification.
    """
    from src.text_cleaning import (
        normalize_text, count_urls, detect_urgent_keywords,
        extract_sender_domain, extract_link_domains, 
        detect_attachment_mention, exclamation_count, length_chars
    )
    from src.features import (
        is_trusted_domain, calculate_domain_risk, calculate_links_risk,
        classify_domain, classify_link, calculate_ensemble_score,
        DOMAIN_TYPE_TRUSTED, DOMAIN_TYPE_CORPORATE, 
        DOMAIN_TYPE_SUSPICIOUS, DOMAIN_TYPE_UNKNOWN,
        LINK_TYPE_TRUSTED, LINK_TYPE_SHORTENER, LINK_TYPE_IP_BASED,
        LINK_TYPE_SUSPICIOUS, LINK_TYPE_NORMAL
    )
    from src.config import TRUSTED_DOMAINS, SHORTENER_DOMAINS, CORPORATE_TLDS
    
    print("=" * 75)
    print("       TRÍCH XUẤT FEATURES TỪ EMAIL (Feature Extraction)")
    print("=" * 75)
    
    # ========== TEXT PREVIEW ==========
    if show_text_preview:
        print("\n📧 NỘI DUNG EMAIL (preview 400 ký tự đầu):")
        print("-" * 75)
        preview = raw_text[:400].replace('\n', ' ').replace('\r', '')
        print(f"  {preview}...")
        print("-" * 75)
    
    # ========== EXTRACT ALL FEATURES ==========
    normalized_text = normalize_text(raw_text)
    links_count = count_urls(raw_text)
    urgent_keywords = detect_urgent_keywords(raw_text)
    sender_domain = extract_sender_domain(raw_text)
    link_domains = extract_link_domains(raw_text)
    urls = extract_urls(raw_text)
    has_attachment = detect_attachment_mention(raw_text)
    exclaim_count = exclamation_count(raw_text)
    body_len = length_chars(raw_text)
    
    print("\n📊 CÁC FEATURES ĐƯỢC TRÍCH XUẤT:")
    print("=" * 75)
    
    # Feature table
    print(f"""
+----------------------+------------------+----------------------------------------+
| Feature              | Giá trị          | Giải thích                             |
+----------------------+------------------+----------------------------------------+
| text (normalized)    | {len(normalized_text):>10} chars | Nội dung email sau khi làm sạch       |
| body_length          | {body_len:>16} | Độ dài email gốc (ký tự)               |
| links_count          | {links_count:>16} | Số lượng URL/link trong email          |
| has_attachment       | {has_attachment:>16} | Có đề cập đính kèm? (0/1)              |
| urgent_keywords      | {urgent_keywords:>16} | Có từ khóa khẩn cấp? (0/1)             |
| exclamation_count    | {exclaim_count:>16} | Số dấu chấm than (!)                   |
| sender_domain        | {sender_domain:>16} | Domain người gửi                       |
+----------------------+------------------+----------------------------------------+
""")
    
    # ========== SENDER DOMAIN CLASSIFICATION ==========
    print("\n📨 PHÂN LOẠI SENDER DOMAIN:")
    print("=" * 75)
    
    domain_type, domain_risk, domain_reason = classify_domain(sender_domain)
    
    # Type icons (simplified to 2 types)
    domain_icons = {
        DOMAIN_TYPE_TRUSTED: "✅ TRUSTED",
        DOMAIN_TYPE_SUSPICIOUS: "⚠️ SUSPICIOUS",
    }
    
    print(f"  Domain: {sender_domain}")
    print(f"  Loại: {domain_icons.get(domain_type, '⚠️ SUSPICIOUS')}")
    print(f"  Lý do: {domain_reason}")
    print(f"  Risk Score: {domain_risk:.2f} ({domain_risk * 100:.0f}%)")
    
    print("\n  Bảng phân loại Domain (Logic đơn giản):")
    print("  +-------------+-------+--------------------------------------------+")
    print("  | Loại        | Risk  | Mô tả                                      |")
    print("  +-------------+-------+--------------------------------------------+")
    print("  | TRUSTED     |   0%  | Domain bạn tự thêm vào whitelist           |")
    print("  | SUSPICIOUS  |  50%  | Tất cả domain khác (không trong whitelist) |")
    print("  +-------------+-------+--------------------------------------------+")
    
    # ========== LINK CLASSIFICATION ==========
    print("\n🔗 PHÂN LOẠI LINK:")
    print("=" * 75)
    
    if urls:
        print(f"  Tổng số link: {len(urls)}")
        print(f"  Unique domains: {len(link_domains)}")
        
        # Link icons
        link_icons = {
            LINK_TYPE_TRUSTED: "✅ TRUSTED",
            LINK_TYPE_SHORTENER: "🔗 SHORTENER",
            LINK_TYPE_IP_BASED: "🚨 IP_BASED",
            LINK_TYPE_SUSPICIOUS: "⚠️ SUSPICIOUS",
            LINK_TYPE_NORMAL: "📄 NORMAL"
        }
        
        print("\n  Chi tiết từng link:")
        print("  " + "-" * 70)
        
        # Group and classify links
        for i, url in enumerate(urls[:10], 1):  # Max 10 links
            link_type, link_risk, link_reason = classify_link(url)
            url_display = url[:50] + "..." if len(url) > 50 else url
            print(f"\n  [{i}] {url_display}")
            print(f"      Loại: {link_icons.get(link_type, link_type)}")
            print(f"      Risk: {link_risk:.0%} - {link_reason}")
        
        if len(urls) > 10:
            print(f"\n  ... và {len(urls) - 10} link khác")
        
        print("\n  Bảng phân loại Link:")
        print("  +-------------+-------+----------------------------------------+")
        print("  | Loại        | Risk  | Mô tả                                  |")
        print("  +-------------+-------+----------------------------------------+")
        print("  | TRUSTED     |   0%  | Link đến domain tin cậy                |")
        print("  | SHORTENER   |  60%  | URL rút gọn (bit.ly, tinyurl...)       |")
        print("  | IP_BASED    |  90%  | Dùng IP thay domain (192.168.1.1)      |")
        print("  | SUSPICIOUS  |  80%  | Có pattern lừa đảo trong URL           |")
        print("  | NORMAL      |  10%  | Link bình thường                       |")
        print("  +-------------+-------+----------------------------------------+")
    else:
        print("  Không tìm thấy link nào trong email.")
    
    # ========== RISK SCORES CALCULATION ==========
    print("\n⚠️ TÍNH TOÁN RISK SCORES:")
    print("=" * 75)
    
    links_risk = calculate_links_risk(links_count, link_domains, urls)
    
    print(f"  1. Urgent Risk:  {urgent_keywords:.2f} ({urgent_keywords * 100:.0f}%)")
    print(f"     Có từ khóa khẩn cấp? {'Có' if urgent_keywords else 'Không'}")
    
    print(f"\n  2. Links Risk:   {links_risk:.2f} ({links_risk * 100:.0f}%)")
    print(f"     Dựa trên: {links_count} links, phân loại từng link")
    
    print(f"\n  3. Domain Risk:  {domain_risk:.2f} ({domain_risk * 100:.0f}%)")
    print(f"     Dựa trên: sender = '{sender_domain}' ({domain_type})")
    
    # ========== FORMULA EXPLANATION ==========
    print("\n📐 CÔNG THỨC TÍNH ĐIỂM (Ensemble Score):")
    print("=" * 75)
    print("""
  Công thức:
  ┌──────────────────────────────────────────────────────────────────────┐
  │  Ensemble = Model×70% + Urgent×12% + Links×10.5% + Domain×7.5%       │
  │                                                                      │
  │  - Model:  Xác suất từ mô hình ML (XGBoost)                         │
  │  - Urgent: Có từ khóa khẩn cấp? (0 hoặc 1)                          │
  │  - Links:  Risk trung bình của các link (đã phân loại)              │
  │  - Domain: Risk của sender domain (đã phân loại)                    │
  │                                                                      │
  │  → Tổng trọng số = 100% (không có bonus riêng)                      │
  └──────────────────────────────────────────────────────────────────────┘
""")
    
    # Calculate example score (without model)
    example_score = urgent_keywords * 0.12 + links_risk * 0.105 + domain_risk * 0.075
    print(f"  Ví dụ với email này (chưa có Model, giả sử Model=50%):")
    print(f"    = 0.50 × 70% + {urgent_keywords} × 12% + {links_risk:.2f} × 10.5% + {domain_risk:.2f} × 7.5%")
    print(f"    = 0.35 + {urgent_keywords * 0.12:.4f} + {links_risk * 0.105:.4f} + {domain_risk * 0.075:.4f}")
    print(f"    = {0.35 + example_score:.4f} ({(0.35 + example_score) * 100:.2f}%)")
    
    # ========== TRUSTED DOMAINS LIST ==========
    print("\n📋 CẤU HÌNH (config.py):")
    print("=" * 75)
    
    print(f"\n  TRUSTED_DOMAINS ({len(TRUSTED_DOMAINS)} domains):")
    print(f"    {', '.join(TRUSTED_DOMAINS[:8])}...")
    
    print(f"\n  SHORTENER_DOMAINS ({len(SHORTENER_DOMAINS)} domains):")
    print(f"    {', '.join(SHORTENER_DOMAINS[:6])}...")
    
    print(f"\n  CORPORATE_TLDS ({len(CORPORATE_TLDS)} TLDs):")
    print(f"    {', '.join(CORPORATE_TLDS)}")
    
    print("\n" + "=" * 75)
    print("                    KẾT THÚC TRÍCH XUẤT FEATURES")
    print("=" * 75)
    
    return {
        'text_length': len(normalized_text),
        'body_length': body_len,
        'links_count': links_count,
        'has_attachment': has_attachment,
        'urgent_keywords': urgent_keywords,
        'exclamation_count': exclaim_count,
        'sender_domain': sender_domain,
        'domain_type': domain_type,
        'domain_risk': domain_risk,
        'link_domains': link_domains,
        'links_risk': links_risk,
    }


def main():
    parser = argparse.ArgumentParser(
        description="Hiển thị chi tiết các features được trích xuất từ email"
    )
    parser.add_argument(
        "--file",
        help="Đường dẫn đến file email (.txt, .eml, .html)"
    )
    parser.add_argument(
        "--text",
        help="Nội dung email dạng text"
    )
    parser.add_argument(
        "--no-preview",
        action="store_true",
        help="Không hiển thị preview nội dung email"
    )
    
    args = parser.parse_args()
    
    # Validate input
    if not args.file and not args.text:
        print("Bạn cần cung cấp --file hoặc --text")
        print("\nVí dụ:")
        print("  python scripts/show_features.py --file samples/test.txt")
        print("  python scripts/show_features.py --text \"Click here to verify your account!\"")
        return
    
    # Get email content
    if args.file:
        file_path = Path(args.file)
        if not file_path.exists():
            print(f"Không tìm thấy file: {file_path}")
            return
        raw_text = read_file(file_path)
        print(f"\n📂 File: {file_path}")
    else:
        raw_text = args.text
        print("\n📝 Sử dụng text từ command line")
    
    # Show features
    show_features(raw_text, show_text_preview=not args.no_preview)


if __name__ == "__main__":
    main()
