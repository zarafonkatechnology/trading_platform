#!/usr/bin/env python3
"""
Simple Telegram Test
"""

import requests
import os
from dotenv import load_dotenv

load_dotenv()

TOKEN = os.getenv('TELEGRAM_BOT_TOKEN')
CHAT_ID = os.getenv('TELEGRAM_CHAT_ID')

print("=" * 50)
print("TELEGRAM TEST")
print("=" * 50)
print(f"Token: {TOKEN[:15]}..." if TOKEN else "Token: NOT FOUND")
print(f"Chat ID: {CHAT_ID}" if CHAT_ID else "Chat ID: NOT FOUND")

if not TOKEN:
    print("\n❌ ERROR: TELEGRAM_BOT_TOKEN not in .env file")
    print("Add this line to .env:")
    print("TELEGRAM_BOT_TOKEN=your_bot_token_from_botfather")
    exit(1)

if not CHAT_ID:
    print("\n❌ ERROR: TELEGRAM_CHAT_ID not in .env file")
    print("\nTo get your Chat ID:")
    print("1. Send a message to your bot on Telegram")
    print("2. Run this command:")
    print(f"   curl https://api.telegram.org/bot{TOKEN}/getUpdates")
    print("3. Find your chat_id in the response")
    exit(1)

# Test 1: Get bot info
print("\n[1] Testing bot connection...")
url = f"https://api.telegram.org/bot{TOKEN}/getMe"
try:
    response = requests.get(url, timeout=10)
    if response.status_code == 200:
        data = response.json()
        if data.get('ok'):
            print(f"✅ Bot connected: @{data['result']['username']}")
        else:
            print(f"❌ Bot error: {data}")
            exit(1)
    else:
        print(f"❌ HTTP Error: {response.status_code}")
        exit(1)
except Exception as e:
    print(f"❌ Connection error: {e}")
    exit(1)

# Test 2: Send a test message
print("\n[2] Sending test message...")
url = f"https://api.telegram.org/bot{TOKEN}/sendMessage"
payload = {
    'chat_id': CHAT_ID,
    'text': '✅ *Test Message* - Your trading bot is working!',
    'parse_mode': 'Markdown'
}

try:
    response = requests.post(url, json=payload, timeout=10)
    if response.status_code == 200:
        data = response.json()
        if data.get('ok'):
            print("✅ Message sent successfully!")
            print("   Check your Telegram bot now!")
        else:
            print(f"❌ API Error: {data.get('description')}")
    else:
        print(f"❌ HTTP Error: {response.status_code}")
        print(f"   Response: {response.text}")
except Exception as e:
    print(f"❌ Error: {e}")

print("\n" + "=" * 50)
