#!/usr/bin/env python3
"""
Command line interface to check agent status
"""

import requests
import json
import sys

BASE_URL = "http://localhost:5000/api"

def print_active_agents():
    resp = requests.get(f"{BASE_URL}/agents/active")
    data = resp.json()
    
    print("\n" + "=" * 50)
    print(f"🎯 MARKET REGIME: {data.get('regime', 'Unknown')}")
    print("=" * 50)
    
    print(f"\n✅ ACTIVE AGENTS ({data.get('active_count', 0)}):")
    for agent in data.get('active_agents', [])[:15]:
        print(f"   • {agent}")
    
    print(f"\n❌ INACTIVE AGENTS ({data.get('inactive_count', 0)}):")
    for agent in data.get('inactive_agents', [])[:10]:
        print(f"   • {agent}")

def print_agent_weights():
    resp = requests.get(f"{BASE_URL}/agents/weights")
    data = resp.json()
    
    print("\n" + "=" * 50)
    print(f"⚖️ AGENT WEIGHTS (Regime: {data.get('regime', 'Unknown')})")
    print("=" * 50)
    
    weights = data.get('weights', {})
    sorted_weights = sorted(weights.items(), key=lambda x: x[1], reverse=True)
    
    for agent, weight in sorted_weights[:15]:
        bar = "█" * int(weight * 10)
        print(f"   {agent:12} [{bar:10}] {weight:.1f}x")

def print_agent_profile(agent_name):
    resp = requests.get(f"{BASE_URL}/agents/profile/{agent_name}")
    
    if resp.status_code != 200:
        print(f"Agent {agent_name} not found")
        return
    
    data = resp.json()
    print("\n" + "=" * 50)
    print(f"📋 AGENT PROFILE: {data['name']}")
    print("=" * 50)
    print(f"Type: {data['type']}")
    print(f"Active: {'✅ Yes' if data['is_active'] else '❌ No'}")
    print(f"Current Weight: {data['current_weight']:.1f}x")
    
    print("\n✅ Preferred Regimes:")
    for regime in data.get('preferred_regimes', []):
        print(f"   • {regime}")
    
    print("\n❌ Avoided Regimes:")
    for regime in data.get('avoided_regimes', []):
        print(f"   • {regime}")

if __name__ == '__main__':
    if len(sys.argv) < 2:
        print("Usage:")
        print("   python cli_agents.py active      - Show active agents")
        print("   python cli_agents.py weights     - Show agent weights")
        print("   python cli_agents.py profile <agent> - Show agent profile")
        sys.exit(1)
    
    command = sys.argv[1]
    
    if command == 'active':
        print_active_agents()
    elif command == 'weights':
        print_agent_weights()
    elif command == 'profile' and len(sys.argv) > 2:
        print_agent_profile(sys.argv[2])
    else:
        print("Unknown command")
