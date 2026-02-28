#!/usr/bin/env python3
"""
API testing script to verify all endpoints return correct response models.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

import asyncio
from app.main import create_app
from fastapi.testclient import TestClient


def test_response_models():
    """Test that all endpoints return correct response models."""
    app = create_app()
    client = TestClient(app)
    
    print("Testing API Response Models...")
    print("=" * 60)
    
    # Test 1: Auth Status (unauthenticated)
    print("\n1. Testing /api/v1/auth/status (unauthenticated)")
    response = client.get("/api/v1/auth/status")
    print(f"   Status: {response.status_code}")
    data = response.json()
    print(f"   Response: {data}")
    assert data['success'] == True
    assert data['data']['authenticated'] == False
    print("   ✓ Pass")
    
    # Test 2: OAuth Connect
    print("\n2. Testing /api/v1/auth/connect")
    response = client.post("/api/v1/auth/connect")
    print(f"   Status: {response.status_code}")
    data = response.json()
    print(f"   Response keys: {list(data.keys())}")
    assert data['success'] == True
    assert 'authorization_url' in data['data']
    assert 'state' in data['data']
    print("   ✓ Pass")
    
    # Test 3: Prediction Analyze (without auth)
    print("\n3. Testing /api/v1/predictions/analyze (no auth)")
    response = client.post("/api/v1/predictions/analyze", json={
        "email_text": "Dear customer, please verify your account by clicking this link: http://suspicious-site.com/verify",
        "subject": "Urgent: Account Verification Required"
    })
    print(f"   Status: {response.status_code}")
    data = response.json()
    print(f"   Response keys: {list(data['data'].keys())}")
    assert data['success'] == True
    assert 'prediction' in data['data']
    assert 'classification' in data['data']
    assert 'probability' in data['data']
    assert 'ensemble_score' in data['data']
    assert 'is_phishing' in data['data']
    assert 'is_suspicious' in data['data']
    print(f"   Classification: {data['data']['classification']}")
    print(f"   Probability: {data['data']['probability']}")
    print(f"   Ensemble Score: {data['data']['ensemble_score']}")
    print("   ✓ Pass")
    
    # Test 4: Prediction Analyze (legitimate email)
    print("\n4. Testing /api/v1/predictions/analyze (legitimate email)")
    response = client.post("/api/v1/predictions/analyze", json={
        "email_text": "Hi, this is a normal email from your friend. How are you doing today?",
        "subject": "Hello"
    })
    print(f"   Status: {response.status_code}")
    data = response.json()
    print(f"   Classification: {data['data']['classification']}")
    print(f"   Probability: {data['data']['probability']}")
    print(f"   Is Phishing: {data['data']['is_phishing']}")
    assert data['success'] == True
    print("   ✓ Pass")
    
    # Test 5: Missing email text
    print("\n5. Testing /api/v1/predictions/analyze (missing email_text)")
    response = client.post("/api/v1/predictions/analyze", json={
        "email_text": ""
    })
    print(f"   Status: {response.status_code}")
    data = response.json()
    print(f"   Response: {data}")
    assert data['success'] == False
    assert response.status_code == 400
    print("   ✓ Pass")
    
    # Test 6: Email list (requires auth - should fail)
    print("\n6. Testing /api/v1/emails/list (no auth - should fail)")
    response = client.get("/api/v1/emails/list")
    print(f"   Status: {response.status_code}")
    data = response.json()
    print(f"   Response: {data}")
    assert data['success'] == False
    assert response.status_code == 401
    print("   ✓ Pass")
    
    # Test 7: History (requires auth - should fail)
    print("\n7. Testing /api/v1/history/predictions (no auth - should fail)")
    response = client.get("/api/v1/history/predictions")
    print(f"   Status: {response.status_code}")
    data = response.json()
    print(f"   Response: {data}")
    assert data['success'] == False
    assert response.status_code == 401
    print("   ✓ Pass")
    
    print("\n" + "=" * 60)
    print("All tests passed! ✓")
    print("\nResponse model structure verified:")
    print("  - All responses have 'success' field")
    print("  - Success responses have 'data' field")
    print("  - Error responses have appropriate status codes")
    print("  - Prediction responses include all required fields")


if __name__ == "__main__":
    try:
        test_response_models()
    except AssertionError as e:
        print(f"\n✗ Test failed: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"\n✗ Error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
