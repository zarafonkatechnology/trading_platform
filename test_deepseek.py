#!/usr/bin/env python3
"""
Test DeepSeek API connection
"""

import os
import requests
from dotenv import load_dotenv

load_dotenv()

API_KEY = os.getenv('DEEPSEEK_API_KEY')
API_URL = os.getenv('DEEPSEEK_API_URL', 'https://api.deepseek.com/v1/chat/completions')

print("=" * 50)
print("TESTING DEEPSEEK API")
print("=" * 50)

if not API_KEY:
    print("❌ DEEPSEEK_API_KEY not found in .env")
    print("   Get your API key from: https://platform.deepseek.com/")
    exit(1)

print(f"✅ API Key found: {API_KEY[:10]}...")
print(f"✅ API URL: {API_URL}")

headers = {
    'Authorization': f'Bearer {API_KEY}',
    'Content-Type': 'application/json'
}

data = {
    'model': 'deepseek-chat',
    'messages': [
        {'role': 'user', 'content': 'Say "Hello! DeepSeek is working!"'}
    ],
    'max_tokens': 50
}

try:
    response = requests.post(API_URL, headers=headers, json=data, timeout=30)
    print(f"\nResponse Status: {response.status_code}")
    
    if response.status_code == 200:
        result = response.json()
        content = result['choices'][0]['message']['content']
        print(f"✅ DeepSeek Response: {content}")
    else:
        print(f"❌ Error: {response.status_code}")
        print(f"Response: {response.text}")
        
except Exception as e:
    print(f"❌ Connection error: {e}")
