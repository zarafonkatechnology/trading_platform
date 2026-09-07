#!/usr/bin/env python3
"""
Test Telegram receiver - Send a test signal to your bot
"""

import os
import requests
from dotenv import load_dotenv

load_dotenv()

TOKEN = os.getenv('TELEGRAM_BOT_TOKEN')
CHAT_ID = os.getenv('TELEGRAM_CHAT_ID')

if not TOKEN:
    print("❌ TELEGRAM_BOT_TOKEN not found in .env")
    exit(1)

if not CHAT_ID:
    print("❌ TELEGRAM_CHAT_ID not found in .env")
    print("Send a message to your bot first, then check:")
    print(f"https://api.telegram.org/bot{TOKEN}/getUpdates")
    exit(1)

# Send a test signal
url = f"https://api.telegram.org/bot{TOKEN}/sendMessage"

# Test signal 1: Gold BUY
message1 = "GOLD BUY 2350"

print(f"Sending: {message1}")
response = requests.post(url, json={
    'chat_id': CHAT_ID,
    'text': message1
})

if response.status_code == 200:
    print("✅ Test signal sent to Telegram!")
    print("Check your bot - it should respond")
else:
    print(f"❌ Error: {response.status_code}")
