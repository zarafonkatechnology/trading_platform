# test_login_direct.py
"""
Test login API directly
"""

import requests

BASE_URL = "http://localhost:8000/api/v1"

print("=" * 60)
print("🧪 TESTING LOGIN API DIRECTLY")
print("=" * 60)

# Test login
print("\n1️⃣ Testing login...")
data = {
    "username": "john.doe@example.com",
    "password": "Test1234!"
}

try:
    response = requests.post(
        f"{BASE_URL}/auth/login",
        data=data,
        timeout=10
    )
    print(f"   Status: {response.status_code}")
    print(f"   Response: {response.text}")
    
    if response.status_code == 200:
        json_data = response.json()
        print(f"   ✅ Login successful!")
        print(f"   Token: {json_data.get('access_token', 'N/A')[:50]}...")
    else:
        print(f"   ❌ Login failed")
        
except requests.exceptions.Timeout:
    print("   ❌ Timeout - API took too long to respond")
except requests.exceptions.ConnectionError:
    print("   ❌ Connection Error - API not running")
except Exception as e:
    print(f"   ❌ Error: {e}")