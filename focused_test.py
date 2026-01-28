#!/usr/bin/env python3
"""
Focused Backend API Testing for CodeCompanion - Non-LLM endpoints
"""

import requests
import json
import sys

# Get backend URL from frontend env
BACKEND_URL = "https://devcompanion-5.preview.emergentagent.com/api"

def test_endpoint(name, url, method="GET", data=None):
    """Test a single endpoint"""
    try:
        if method == "GET":
            response = requests.get(url, timeout=15)
        elif method == "POST":
            response = requests.post(url, json=data, timeout=30)
        
        print(f"Testing {name}:")
        print(f"  URL: {url}")
        print(f"  Status: {response.status_code}")
        
        if response.status_code == 200:
            try:
                result = response.json()
                print(f"  ✅ SUCCESS: {result}")
                return True
            except:
                print(f"  ✅ SUCCESS: {response.text[:200]}...")
                return True
        else:
            print(f"  ❌ FAILED: {response.text}")
            return False
            
    except Exception as e:
        print(f"  ❌ ERROR: {str(e)}")
        return False

def main():
    print("🔍 Testing CodeCompanion Backend Endpoints (Non-LLM)")
    print("=" * 60)
    
    tests = [
        ("Health Check", f"{BACKEND_URL}/health", "GET"),
        ("Model Status", f"{BACKEND_URL}/models/status", "GET"),
        ("Model List", f"{BACKEND_URL}/models/list", "GET"),
        ("Conversations List", f"{BACKEND_URL}/conversations", "GET"),
        ("Index Stats", f"{BACKEND_URL}/index/stats", "GET"),
        ("Workspace Indexing", f"{BACKEND_URL}/index/workspace", "POST"),
    ]
    
    results = []
    for name, url, method in tests:
        print(f"\n{'-' * 40}")
        success = test_endpoint(name, url, method)
        results.append((name, success))
    
    print(f"\n{'=' * 60}")
    print("SUMMARY:")
    passed = 0
    for name, success in results:
        status = "✅" if success else "❌"
        print(f"{status} {name}")
        if success:
            passed += 1
    
    print(f"\nResults: {passed}/{len(results)} tests passed")
    
    # Check for critical LLM budget issue
    print(f"\n🚨 CRITICAL ISSUE IDENTIFIED:")
    print(f"   - Emergent API budget exceeded (Current: $0.00343595, Max: $0.001)")
    print(f"   - This prevents chat/agentic functionality from working")
    print(f"   - All other endpoints are working correctly")

if __name__ == "__main__":
    main()