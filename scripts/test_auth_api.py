#!/usr/bin/env python3
"""
Test script for authentication API endpoints.
Tests signup, login, and authentication flow.
"""

import requests
import json
from datetime import datetime

BASE_URL = "http://localhost:8000"

def print_section(title):
    """Print a section header."""
    print(f"\n{'='*60}")
    print(f" {title}")
    print(f"{'='*60}\n")

def test_signup():
    """Test user signup endpoint."""
    print_section("Testing Signup")
    
    # Create unique email to avoid conflicts
    timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
    test_email = f"test_{timestamp}@ouroboros.ai"
    
    signup_data = {
        "email": test_email,
        "password": "TestPassword123!",
        "full_name": "Test User"
    }
    
    print(f"Request: POST {BASE_URL}/auth/signup")
    print(f"Body: {json.dumps(signup_data, indent=2)}")
    
    try:
        response = requests.post(
            f"{BASE_URL}/auth/signup",
            json=signup_data,
            headers={"Content-Type": "application/json"}
        )
        
        print(f"\nStatus Code: {response.status_code}")
        print(f"Response Headers: {dict(response.headers)}")
        print(f"Response Body: {json.dumps(response.json(), indent=2)}")
        
        if response.status_code == 201:
            print("\n✅ Signup successful!")
            return test_email, signup_data["password"]
        else:
            print(f"\n❌ Signup failed: {response.json().get('detail', 'Unknown error')}")
            return None, None
            
    except Exception as e:
        print(f"\n❌ Exception during signup: {str(e)}")
        return None, None

def test_login(email, password):
    """Test user login endpoint."""
    print_section("Testing Login")
    
    login_data = {
        "email": email,
        "password": password
    }
    
    print(f"Request: POST {BASE_URL}/auth/login")
    print(f"Body: {json.dumps(login_data, indent=2)}")
    
    try:
        response = requests.post(
            f"{BASE_URL}/auth/login",
            json=login_data,
            headers={"Content-Type": "application/json"}
        )
        
        print(f"\nStatus Code: {response.status_code}")
        print(f"Response Headers: {dict(response.headers)}")
        
        if response.status_code == 200:
            response_data = response.json()
            print(f"Response Body: {json.dumps(response_data, indent=2)}")
            print("\n✅ Login successful!")
            return response_data.get("access_token")
        else:
            print(f"Response Body: {json.dumps(response.json(), indent=2)}")
            print(f"\n❌ Login failed: {response.json().get('detail', 'Unknown error')}")
            return None
            
    except Exception as e:
        print(f"\n❌ Exception during login: {str(e)}")
        return None

def test_authenticated_endpoint(access_token):
    """Test accessing authenticated endpoint."""
    print_section("Testing Authenticated Endpoint")
    
    print(f"Request: GET {BASE_URL}/auth/me")
    print(f"Authorization: Bearer {access_token[:20]}...")
    
    try:
        response = requests.get(
            f"{BASE_URL}/auth/me",
            headers={"Authorization": f"Bearer {access_token}"}
        )
        
        print(f"\nStatus Code: {response.status_code}")
        
        if response.status_code == 200:
            print(f"Response Body: {json.dumps(response.json(), indent=2)}")
            print("\n✅ Authenticated request successful!")
        else:
            print(f"Response Body: {json.dumps(response.json(), indent=2)}")
            print(f"\n❌ Authenticated request failed")
            
    except Exception as e:
        print(f"\n❌ Exception during authenticated request: {str(e)}")

def main():
    """Run all authentication tests."""
    print_section("Authentication API Test Suite")
    print(f"Target: {BASE_URL}")
    print(f"Time: {datetime.now().isoformat()}")
    
    # Test 1: Signup
    email, password = test_signup()
    
    if email and password:
        # Test 2: Login with the created account
        access_token = test_login(email, password)
        
        if access_token:
            # Test 3: Access authenticated endpoint
            test_authenticated_endpoint(access_token)
    
    print_section("Test Suite Complete")

if __name__ == "__main__":
    main()
