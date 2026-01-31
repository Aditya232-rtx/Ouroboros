
import requests
import json

API_URL = "http://localhost:8000"

def test_auth():
    email = "test@example.com"
    password = "password123"
    full_name = "Test User"
    
    print("🚀 Testing Authentication Flow...")
    
    # 1. Signup
    print("\n1. Signup...")
    signup_data = {
        "email": email,
        "password": password,
        "full_name": full_name
    }
    resp = requests.post(f"{API_URL}/auth/signup", json=signup_data)
    if resp.status_code == 201:
        print("✅ Signup successful")
    elif resp.status_code == 400 and "already registered" in resp.text:
         print("⚠️ User already exists (OK)")
    else:
        print(f"❌ Signup failed: {resp.status_code} - {resp.text}")
        return

    # 2. Login
    print("\n2. Login...")
    login_data = {
        "email": email,
        "password": password
    }
    session = requests.Session()
    resp = session.post(f"{API_URL}/auth/login", json=login_data)
    
    if resp.status_code == 200:
        print("✅ Login successful")
        print("   Cookies:", session.cookies.get_dict())
        tokens = resp.json()
        print("   Access Token (Body):", tokens.get("access_token")[:20] + "...")
    else:
        print(f"❌ Login failed: {resp.status_code} - {resp.text}")
        return

    # 3. Check /auth/me (using cookies)
    print("\n3. Check /auth/me (Cookie Auth)...")
    resp = session.get(f"{API_URL}/auth/me")
    if resp.status_code == 200:
        print("✅ /auth/me successful")
        print("   User:", resp.json())
    else:
        print(f"❌ /auth/me failed: {resp.status_code} - {resp.text}")

if __name__ == "__main__":
    test_auth()
