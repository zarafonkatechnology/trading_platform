# test_learning_system.py
"""
Test the Self-Learning AI Trading System
"""

import time
from datetime import datetime
from trading_controller import trading_controller
from deepseek_coach import DeepSeekCoach

def test_learning():
    print("=" * 60)
    print("🧪 TESTING SELF-LEARNING AI SYSTEM")
    print("=" * 60)
    
    # Initialize coach
    coach = DeepSeekCoach()
    
    # Test 1: Get agent votes
    print("\n[1] Getting agent votes...")
    symbol = 'EURUSD'
    analysis = trading_controller.analyze_market(symbol)
    
    print(f"\n📊 Analysis for {symbol}:")
    print(f"   Action: {analysis['action']}")
    print(f"   Confidence: {analysis['confidence']}%")
    
    # Simulate actual result
    actual_result = random.choice(['UP', 'DOWN', 'SIDEWAYS'])
    print(f"\n📈 Actual Result: {actual_result}")
    
    # Test 2: Evaluate agents
    print("\n[2] Evaluating agents...")
    agent_votes = analysis.get('agent_signals', {})
    results = coach.evaluate_agent_votes(symbol, agent_votes, actual_result)
    
    print("\n📊 Agent Results:")
    for agent, result in results.items():
        status = "✅" if result['correct'] else "❌"
        print(f"   {status} {agent}: {result['vote']} ({result['confidence']}%)")
        print(f"      XP: {result['xp']}, Tokens: {result['tokens']}")
    
    # Test 3: Get DeepSeek feedback
    print("\n[3] Getting DeepSeek feedback...")
    feedback = coach.get_deepseek_feedback(symbol, results, actual_result)
    
    print(f"\n📖 DeepSeek Analysis:")
    if feedback.get('analysis'):
        print(f"   {feedback['analysis']}")
    
    if feedback.get('rules'):
        print(f"\n📋 Rules to Learn:")
        for rule in feedback['rules']:
            print(f"   📌 {rule}")
    
    if feedback.get('lesson'):
        print(f"\n🎓 Lesson: {feedback['lesson']}")
    
    print("\n" + "=" * 60)
    print("✅ Test Complete!")
    print("=" * 60)

if __name__ == "__main__":
    import random
    test_learning()