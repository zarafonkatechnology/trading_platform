#!/usr/bin/env python3
"""
Test script for teaching API endpoints
"""

import requests
import json

BASE_URL = "http://localhost:5000"

def test_teach_agent():
    print("\n" + "="*50)
    print("TEST: Teach Agent")
    print("="*50)
    
    data = {
        "agent_name": "Agent_A",
        "topic": "Bollinger Band Strategy",
        "content": "When price touches lower band with RSI below 30, expect bounce. When price touches upper band with RSI above 70, expect reversal.",
        "teacher": "Instructor"
    }
    
    response = requests.post(f"{BASE_URL}/api/teach_agent", json=data)
    print(f"Status: {response.status_code}")
    result = response.json()
    print(f"Success: {result.get('success')}")
    if result.get('success'):
        print(f"Message: {result.get('message')}")
        if result.get('agent'):
            print(f"Agent XP: {result['agent'].get('xp_points')}")
            print(f"Agent Tokens: {result['agent'].get('token_balance')}")
    else:
        print(f"Error: {result.get('error')}")
    
    return result.get('success', False)

def test_teach_all_agents():
    print("\n" + "="*50)
    print("TEST: Teach All Agents (Broadcast)")
    print("="*50)
    
    data = {
        "topic": "Market Regime Detection",
        "content": "Important: When volatility exceeds 2%, reduce position size by 50%. When trend strength > 60, follow trend direction.",
        "teacher": "Instructor"
    }
    
    response = requests.post(f"{BASE_URL}/api/teach_all_agents", json=data)
    print(f"Status: {response.status_code}")
    result = response.json()
    print(f"Success: {result.get('success')}")
    if result.get('success'):
        print(f"Message: {result.get('message')}")
        print(f"Total XP awarded: {result.get('total_xp')}")
        print(f"Total Tokens awarded: {result.get('total_tokens')}")
        print(f"Agents affected: {result.get('agents_affected')}")
    else:
        print(f"Error: {result.get('error')}")
    
    return result.get('success', False)

def test_get_knowledge_exchanges():
    print("\n" + "="*50)
    print("TEST: Get Knowledge Exchanges")
    print("="*50)
    
    response = requests.get(f"{BASE_URL}/api/knowledge_exchanges")
    print(f"Status: {response.status_code}")
    result = response.json()
    print(f"Success: {result.get('success')}")
    if result.get('success'):
        print(f"Total exchanges: {result.get('total')}")
        for ex in result.get('exchanges', [])[:3]:
            print(f"  - {ex.get('from_agent')} → {ex.get('to_agent')}: {ex.get('topic')}")
    else:
        print(f"Error: {result.get('error')}")
    
    return result.get('success', False)

def test_agent_status():
    print("\n" + "="*50)
    print("TEST: Agent Status After Teaching")
    print("="*50)
    
    response = requests.get(f"{BASE_URL}/api/agents")
    print(f"Status: {response.status_code}")
    result = response.json()
    if result.get('success'):
        print("\nUpdated Agent Status:")
        for agent in result.get('agents', []):
            print(f"  {agent['name']}: XP={agent['xp_points']}, Tokens={agent['token_balance']}, Knowledge Shared={agent.get('knowledge_shared_count', 0)}")
    else:
        print(f"Error: {result.get('error')}")
    
    return result.get('success', False)

if __name__ == "__main__":
    print("\n" + "="*50)
    print("TEACHING API TEST SUITE")
    print("="*50)
    
    # Make sure server is running
    try:
        response = requests.get(f"{BASE_URL}/health")
        print("✅ Server is running")
    except:
        print("❌ Server is not running. Start with: python app.py")
        exit(1)
    
    # Run tests
    test_teach_agent()
    test_teach_all_agents()
    test_get_knowledge_exchanges()
    test_agent_status()
    
    print("\n" + "="*50)
    print("TEST COMPLETE")
    print("="*50)
