"""
Test script for trusted domain feature.
Tests that LinkedIn emails are correctly identified as low-risk.
"""
import sys
sys.path.insert(0, '.')

from src.text_cleaning import extract_link_domains, extract_sender_domain, count_urls
from src.features import is_trusted_domain, calculate_domain_risk, calculate_links_risk
from src.config import TRUSTED_DOMAINS

def test_extract_link_domains():
    """Test domain extraction from URLs"""
    print("=" * 60)
    print("TEST 1: extract_link_domains()")
    print("=" * 60)
    
    # Read LinkedIn email
    with open("samples/test.txt", "r", encoding="utf-8", errors="ignore") as f:
        content = f.read()
    
    domains = extract_link_domains(content)
    print(f"Found {len(domains)} unique domains:")
    for d in domains:
        trusted = "✅ TRUSTED" if is_trusted_domain(d) else "❌"
        print(f"  - {d} {trusted}")
    
    return domains

def test_is_trusted_domain():
    """Test trusted domain checking"""
    print("\n" + "=" * 60)
    print("TEST 2: is_trusted_domain()")
    print("=" * 60)
    
    test_cases = [
        ("linkedin.com", True),
        ("www.linkedin.com", True),
        ("mail.linkedin.com", True),
        ("phishing-linkedin.com", False),
        ("linkedin.fake.com", False),
        ("google.com", True),
        ("suspicious-site.xyz", False),
        ("unknown", False),
    ]
    
    all_passed = True
    for domain, expected in test_cases:
        result = is_trusted_domain(domain)
        status = "✅ PASS" if result == expected else "❌ FAIL"
        if result != expected:
            all_passed = False
        print(f"  {status}: is_trusted_domain('{domain}') = {result} (expected: {expected})")
    
    return all_passed

def test_risk_scores():
    """Test risk score calculations"""
    print("\n" + "=" * 60)
    print("TEST 3: Risk Score Calculations")
    print("=" * 60)
    
    # Test domain risk
    print("\nDomain Risk Scores:")
    test_domains = ["linkedin.com", "google.com", "unknown", "suspicious.xyz", "phishing-bank.com"]
    for d in test_domains:
        risk = calculate_domain_risk(d)
        print(f"  {d}: {risk:.2f}")
    
    # Test links risk with trusted domains
    print("\nLinks Risk Scores:")
    
    # LinkedIn-style: many links but all trusted
    linkedin_domains = ["linkedin.com"] * 10
    risk1 = calculate_links_risk(10, linkedin_domains)
    print(f"  10 links, all linkedin.com: {risk1:.2f} (should be low ~0.1)")
    
    # Mixed: some trusted, some not
    mixed_domains = ["linkedin.com", "google.com", "suspicious.xyz"]
    risk2 = calculate_links_risk(3, mixed_domains)
    print(f"  3 links, 2/3 trusted: {risk2:.2f} (should be moderate ~0.3)")
    
    # All suspicious
    risk3 = calculate_links_risk(5, ["phishing.xyz", "scam.top"])
    print(f"  5 links, 0 trusted: {risk3:.2f} (should be high ~0.6)")
    
    # No domain info (legacy behavior)
    risk4 = calculate_links_risk(10, None)
    print(f"  10 links, no domain info: {risk4:.2f} (should be high ~0.8)")

def test_linkedin_email():
    """Test full prediction on LinkedIn email"""
    print("\n" + "=" * 60)
    print("TEST 4: LinkedIn Email Analysis")
    print("=" * 60)
    
    with open("samples/test.txt", "r", encoding="utf-8", errors="ignore") as f:
        content = f.read()
    
    # Extract features
    links_count = count_urls(content)
    link_domains = extract_link_domains(content)
    sender_domain = extract_sender_domain(content)
    
    print(f"\nExtracted Features:")
    print(f"  - Links count: {links_count}")
    print(f"  - Unique domains: {len(link_domains)}")
    print(f"  - Sender domain: {sender_domain}")
    
    # Calculate risks
    domain_risk = calculate_domain_risk(sender_domain)
    links_risk = calculate_links_risk(links_count, link_domains)
    
    print(f"\nRisk Scores (AFTER trusted domain fix):")
    print(f"  - Domain risk: {domain_risk:.2f}")
    print(f"  - Links risk: {links_risk:.2f}")
    
    # Count trusted ratio
    trusted_count = sum(1 for d in link_domains if is_trusted_domain(d))
    print(f"\nTrusted Domain Analysis:")
    print(f"  - Trusted links: {trusted_count}/{len(link_domains)} ({100*trusted_count/len(link_domains):.1f}%)")

if __name__ == "__main__":
    print("\n🧪 TRUSTED DOMAIN FEATURE TEST\n")
    
    # Run tests
    domains = test_extract_link_domains()
    passed = test_is_trusted_domain()
    test_risk_scores()
    test_linkedin_email()
    
    print("\n" + "=" * 60)
    print("TEST SUMMARY")
    print("=" * 60)
    if passed:
        print("✅ All unit tests passed!")
    else:
        print("❌ Some tests failed!")
    print("\nExpected behavior for LinkedIn email:")
    print("  - Links risk should be LOW (~0.1) because 100% linkedin.com")
    print("  - This should reduce ensemble_score significantly!")
