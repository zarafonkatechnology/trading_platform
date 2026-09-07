#!/usr/bin/env python3
"""
Test creating a conversation
"""

import requests
import json

BASE = "http://localhost:5000"

# Test creating a conversation
print("Testing conversation creation...")
response = requests.post(f"{BASE}/api/agent_conversation", json={
    "from_agent": "Agent_A",
    "to_agent": "Agent_B", 
    "message": "Hello, this is a test message!",
    "message_type": "direct"
})

print(f"Status: {response.status_code}")
print(f"Response: {response.text}")

# Check if conversation appears
print("\nChecking conversations...")
response = requests.get(f"{BASE}/api/agent_conversations")
print(f"Conversations: {response.text}")
