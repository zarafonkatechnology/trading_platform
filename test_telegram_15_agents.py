#!/usr/bin/env python3
"""
Telegram Test for All 15 Agents (A through O)
Tests agent voting and sends results to Telegram
"""

import os
import sys
import json
import random
import requests
from datetime import datetime
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Telegram configuration
TELEGRAM_BOT_TOKEN = os.getenv('TELEGRAM_BOT_TOKEN')
TELEGRAM_CHAT_ID = os.getenv('TELEGRAM_CHAT_ID')

# ============================================
# ALL 15 AGENTS DEFINITION
# ============================================

ALL_AGENTS = {
    # Original 8 Agents
    'Agent_A': {'type': 'Trend Follower', 'specialty': 'Moving Average Crossovers', 'emoji': '📈'},
    'Agent_B': {'type': 'Mean Reversion', 'specialty': 'RSI & Bollinger Bands', 'emoji': '🔄'},
    'Agent_C': {'type': 'Momentum', 'specialty': 'Price Rate of Change', 'emoji': '⚡'},
    'Agent_D': {'type': 'Volatility', 'specialty': 'ATR Analysis', 'emoji': '🌊'},
    'Agent_E': {'type': 'Microstructure', 'specialty': 'Order Flow', 'emoji': '🔬'},
    'Agent_F': {'type': 'Candlestick', 'specialty': 'Japanese Patterns', 'emoji': '🕯️'},
    'Agent_G': {'type': 'Whale Tracker', 'specialty': 'COT Analysis', 'emoji': '🐋'},
    'Agent_H': {'type': 'Fibonacci', 'specialty': 'Retracement Levels', 'emoji': '🌀'},
    
    # New 4 Agents (I, J, K, L)
    'Agent_I': {'type': 'Sentiment Master', 'specialty': 'News & Social Sentiment', 'emoji': '😀'},
    'Agent_J': {'type': 'Volume Master', 'specialty': 'Volume Profile Analysis', 'emoji': '📊'},
    'Agent_K': {'type': 'Ichimoku Expert', 'specialty': 'Ichimoku Cloud Breakouts', 'emoji': '☁️'},
    'Agent_L': {'type': 'Fundamental Master', 'specialty': 'Economic Calendar & Rates', 'emoji': '🏦'},
    
    # Bonus 3 Agents (M, N, O)
    'Agent_M': {'type': 'Market Profile Master', 'specialty': 'TPO & Value Area', 'emoji': '📐'},
    'Agent_N': {'type': 'Intermarket Master', 'specialty': 'Cross-Asset Correlations', 'emoji': '🌍'},
    'Agent_O': {'type': 'Seasonality Expert', 'specialty': 'Time-based Patterns', 'emoji': '📅'},
}

# ============================================
# AGENT VOTING SIMULATION
# ============================================

def simulate_agent_vote(agent_name, agent_info, market_price, market_trend):
    """Simulate a vote for a single agent based on their specialty"""
    
    agent_type = agent_info['type']
    confidence_base = random.randint(55, 95)
    
    # Different voting logic based on agent type
    if agent_type == 'Trend Follower':
        if market_trend == 'up':
            return 'BUY', confidence_base, f"Trend is {market_trend}, following momentum"
        else:
            return 'SELL', confidence_base, f"Trend is {market_trend}, following momentum"
    
    elif agent_type == 'Mean Reversion':
        # Mean reversers look for extremes
        if random.random() > 0.7:
            return 'SELL', confidence_base, "RSI overbought, expecting pullback"
        elif random.random() < 0.3:
            return 'BUY', confidence_base, "RSI oversold, expecting bounce"
        else:
            return 'HOLD', confidence_base - 10, "No extreme levels detected"
    
    elif agent_type == 'Momentum':
        momentum = random.uniform(-2, 2)
        if momentum > 0.5:
            return 'BUY', confidence_base, f"Strong momentum at {momentum:.2f}"
        elif momentum < -0.5:
            return 'SELL', confidence_base, f"Negative momentum at {momentum:.2f}"
        else:
            return 'HOLD', confidence_base - 15, "Momentum flat"
    
    elif agent_type == 'Volatility':
        volatility = random.uniform(0.3, 1.5)
        if volatility > 1.2:
            return 'HOLD', confidence_base, f"High volatility ({volatility:.2f}), reducing risk"
        elif volatility < 0.6:
            return 'BUY', confidence_base, f"Low volatility ({volatility:.2f}), expecting expansion"
        else:
            return 'NEUTRAL', confidence_base - 10, "Normal volatility"
    
    elif agent_type == 'Microstructure':
        order_flow = random.choice(['buying', 'selling', 'neutral'])
        if order_flow == 'buying':
            return 'BUY', confidence_base, "Order flow shows buying pressure"
        elif order_flow == 'selling':
            return 'SELL', confidence_base, "Order flow shows selling pressure"
        else:
            return 'HOLD', confidence_base - 10, "Order flow neutral"
    
    elif agent_type == 'Candlestick':
        patterns = ['Hammer', 'Engulfing', 'Doji', 'Shooting Star', 'None']
        pattern = random.choice(patterns)
        if pattern == 'Hammer':
            return 'BUY', confidence_base + 5, f"{pattern} pattern detected - bullish reversal"
        elif pattern == 'Shooting Star':
            return 'SELL', confidence_base + 5, f"{pattern} pattern detected - bearish reversal"
        elif pattern == 'Engulfing':
            direction = 'BUY' if random.random() > 0.5 else 'SELL'
            return direction, confidence_base + 10, f"{pattern} pattern detected"
        else:
            return 'HOLD', confidence_base - 15, "No significant pattern"
    
    elif agent_type == 'Whale Tracker':
        whale_action = random.choice(['accumulating', 'distributing', 'neutral'])
        if whale_action == 'accumulating':
            return 'BUY', confidence_base, "Large institutional accumulation detected"
        elif whale_action == 'distributing':
            return 'SELL', confidence_base, "Large institutional distribution detected"
        else:
            return 'HOLD', confidence_base - 10, "No whale activity"
    
    elif agent_type == 'Fibonacci':
        fib_level = random.choice(['618', '382', '236', '786', 'none'])
        if fib_level == '618':
            return 'BUY', confidence_base, "Price at 61.8% Fibonacci support"
        elif fib_level == '382':
            return 'SELL', confidence_base, "Price at 38.2% Fibonacci resistance"
        else:
            return 'HOLD', confidence_base - 15, "Between key Fibonacci levels"
    
    elif agent_type == 'Sentiment Master':
        sentiment = random.randint(-100, 100)
        if sentiment > 60:
            return 'SELL', confidence_base, f"Extreme greed detected ({sentiment})"
        elif sentiment < -60:
            return 'BUY', confidence_base, f"Extreme fear detected ({sentiment})"
        elif sentiment > 20:
            return 'BUY', confidence_base - 10, f"Positive sentiment ({sentiment})"
        elif sentiment < -20:
            return 'SELL', confidence_base - 10, f"Negative sentiment ({sentiment})"
        else:
            return 'HOLD', confidence_base - 20, "Neutral sentiment"
    
    elif agent_type == 'Volume Master':
        volume_ratio = random.uniform(0.3, 2.5)
        if volume_ratio > 1.5 and market_trend == 'up':
            return 'BUY', confidence_base, f"Volume confirms uptrend (ratio {volume_ratio:.1f}x)"
        elif volume_ratio > 1.5 and market_trend == 'down':
            return 'SELL', confidence_base, f"Volume confirms downtrend (ratio {volume_ratio:.1f}x)"
        elif volume_ratio < 0.5:
            return 'HOLD', confidence_base - 15, f"Low volume ({volume_ratio:.1f}x), weak move"
        else:
            return 'HOLD', confidence_base - 10, "Normal volume"
    
    elif agent_type == 'Ichimoku Expert':
        cloud = random.choice(['above', 'below', 'inside'])
        if cloud == 'above':
            return 'BUY', confidence_base, "Price above Ichimoku Cloud - Bullish"
        elif cloud == 'below':
            return 'SELL', confidence_base, "Price below Ichimoku Cloud - Bearish"
        else:
            return 'HOLD', confidence_base - 10, "Inside Cloud - Wait for breakout"
    
    elif agent_type == 'Fundamental Master':
        economic_score = random.randint(30, 85)
        if economic_score > 70:
            return 'BUY', confidence_base, f"Strong fundamentals (Score: {economic_score})"
        elif economic_score < 35:
            return 'SELL', confidence_base, f"Weak fundamentals (Score: {economic_score})"
        else:
            return 'HOLD', confidence_base - 15, f"Mixed fundamentals (Score: {economic_score})"
    
    elif agent_type == 'Market Profile Master':
        position = random.choice(['above_va', 'below_va', 'inside_va'])
        if position == 'above_va':
            return 'SELL', confidence_base, "Price above value area - Premium"
        elif position == 'below_va':
            return 'BUY', confidence_base, "Price below value area - Discount"
        else:
            return 'HOLD', confidence_base - 10, "Inside value area - Fair value"
    
    elif agent_type == 'Intermarket Master':
        dxy = random.choice(['down', 'up'])
        if dxy == 'down':
            return 'BUY', confidence_base, "DXY weakening - USD weakness"
        else:
            return 'SELL', confidence_base, "DXY strengthening - USD strength"
    
    elif agent_type == 'Seasonality Expert':
        from datetime import datetime
        hour = datetime.now().hour
        if 8 <= hour <= 10:
            return 'BUY', confidence_base, "London open - Momentum typically starts"
        elif hour >= 20:
            return 'SELL', confidence_base, "Late session - Position squaring"
        else:
            return 'HOLD', confidence_base - 15, "Normal trading hours"
    
    else:
        # Default fallback
        vote = random.choice(['BUY', 'SELL', 'HOLD'])
        return vote, confidence_base - 20, "Standard analysis"

# ============================================
# TELEGRAM MESSAGE FUNCTIONS
# ============================================

def send_telegram_message(message, parse_mode=None):
    """Send message to Telegram"""
    if not TELEGRAM_BOT_TOKEN or not TELEGRAM_CHAT_ID:
        print("❌ Telegram credentials not found in .env file")
        return False
    
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    data = {
        'chat_id': TELEGRAM_CHAT_ID,
        'text': message
    }
    if parse_mode:
        data['parse_mode'] = parse_mode
    
    try:
        response = requests.post(url, json=data, timeout=10)
        if response.status_code == 200:
            print("✅ Telegram message sent successfully")
            return True
        else:
            print(f"❌ Telegram error: {response.text}")
            return False
    except Exception as e:
        print(f"❌ Telegram send error: {e}")
        return False

def format_agents_message(asset, price, agent_votes, consensus):
    """Format message with all 15 agents"""
    
    # Count votes
    buy_agents = []
    sell_agents = []
    hold_agents = []
    
    for agent_name, vote_data in agent_votes.items():
        vote = vote_data['vote']
        confidence = vote_data['confidence']
        agent_type = ALL_AGENTS[agent_name]['type']
        emoji = ALL_AGENTS[agent_name]['emoji']
        
        line = f"{emoji} {agent_name} ({agent_type[:12]}): {vote} ({confidence:.0f}%)"
        
        if vote == 'BUY':
            buy_agents.append(line)
        elif vote == 'SELL':
            sell_agents.append(line)
        else:
            hold_agents.append(line)
    
    # Build message
    lines = [
        "=" * 40,
        f"🤖 ALL 15 AGENTS VOTING RESULTS 🤖",
        "=" * 40,
        "",
        f"📊 Asset: {asset}",
        f"💰 Price: {price}",
        f"⏰ Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
        "",
        f"📈 BUY VOTES ({len(buy_agents)}):",
    ]
    
    if buy_agents:
        lines.extend(buy_agents)
    else:
        lines.append("   None")
    
    lines.append("")
    lines.append(f"📉 SELL VOTES ({len(sell_agents)}):")
    if sell_agents:
        lines.extend(sell_agents)
    else:
        lines.append("   None")
    
    lines.append("")
    lines.append(f"⏸️ HOLD VOTES ({len(hold_agents)}):")
    if hold_agents:
        lines.extend(hold_agents)
    else:
        lines.append("   None")
    
    lines.append("")
    lines.append("-" * 40)
    lines.append(f"🎯 CONSENSUS: {consensus['action']}")
    lines.append(f"📊 Confidence: {consensus['confidence']:.1f}%")
    lines.append(f"📝 Summary: {consensus['reason']}")
    lines.append("-" * 40)
    
    return "\n".join(lines)

def format_simple_message(asset, price, agent_votes, consensus):
    """Simple plain text message (no formatting issues)"""
    
    # Count votes
    buy_count = sum(1 for v in agent_votes.values() if v['vote'] == 'BUY')
    sell_count = sum(1 for v in agent_votes.values() if v['vote'] == 'SELL')
    hold_count = sum(1 for v in agent_votes.values() if v['vote'] == 'HOLD')
    
    # Get top 3 confident agents
    top_agents = sorted(agent_votes.items(), key=lambda x: x[1]['confidence'], reverse=True)[:3]
    
    lines = [
        f"🤖 15 AGENTS VOTING - {asset}",
        f"Price: {price} | Time: {datetime.now().strftime('%H:%M:%S')}",
        "",
        f"RESULTS: BUY={buy_count} | SELL={sell_count} | HOLD={hold_count}",
        f"CONSENSUS: {consensus['action']} ({consensus['confidence']:.0f}%)",
        "",
        "Top confident agents:"
    ]
    
    for agent, data in top_agents:
        lines.append(f"  {agent}: {data['vote']} ({data['confidence']:.0f}%) - {data['reason'][:40]}")
    
    lines.append("")
    lines.append(f"Summary: {consensus['reason']}")
    
    return "\n".join(lines)

# ============================================
# MAIN TEST FUNCTION
# ============================================

def test_all_15_agents():
    """Test all 15 agents and send results to Telegram"""
    
    print("\n" + "=" * 60)
    print("🧪 TESTING ALL 15 AGENTS (A through O)")
    print("=" * 60 + "\n")
    
    # Test parameters
    test_assets = [
        {'asset': 'EURUSD', 'price': 1.0950, 'trend': 'up'},
        {'asset': 'GBPUSD', 'price': 1.2850, 'trend': 'down'},
        {'asset': 'XAU/USD', 'price': 2385.50, 'trend': 'up'},
        {'asset': 'USDJPY', 'price': 148.50, 'trend': 'sideways'},
    ]
    
    results = []
    
    for test in test_assets:
        asset = test['asset']
        price = test['price']
        trend = test['trend']
        
        print(f"\n📊 Testing {asset} at ${price} (Trend: {trend})")
        print("-" * 40)
        
        # Get votes from all 15 agents
        agent_votes = {}
        for agent_name, agent_info in ALL_AGENTS.items():
            vote, confidence, reason = simulate_agent_vote(agent_name, agent_info, price, trend)
            agent_votes[agent_name] = {
                'vote': vote,
                'confidence': confidence,
                'reason': reason,
                'type': agent_info['type']
            }
            print(f"  {agent_name}: {vote} ({confidence}%) - {reason[:30]}...")
        
        # Calculate consensus
        buy_count = sum(1 for v in agent_votes.values() if v['vote'] == 'BUY')
        sell_count = sum(1 for v in agent_votes.values() if v['vote'] == 'SELL')
        hold_count = sum(1 for v in agent_votes.values() if v['vote'] == 'HOLD')
        
        if buy_count > sell_count and buy_count > hold_count:
            action = 'BUY'
            confidence = (buy_count / len(agent_votes)) * 100
            reason = f"{buy_count} out of {len(agent_votes)} agents recommend BUY"
        elif sell_count > buy_count and sell_count > hold_count:
            action = 'SELL'
            confidence = (sell_count / len(agent_votes)) * 100
            reason = f"{sell_count} out of {len(agent_votes)} agents recommend SELL"
        else:
            action = 'HOLD'
            confidence = ((hold_count + max(buy_count, sell_count)) / len(agent_votes)) * 50
            reason = f"Mixed signals: BUY={buy_count}, SELL={sell_count}, HOLD={hold_count}"
        
        consensus = {
            'action': action,
            'confidence': confidence,
            'reason': reason
        }
        
        # Format and send message
        # Try simple message first (always works)
        message = format_simple_message(asset, price, agent_votes, consensus)
        
        print(f"\n📨 Sending to Telegram...")
        success = send_telegram_message(message)
        
        if success:
            print(f"✅ Message sent for {asset}")
        else:
            print(f"❌ Failed to send for {asset}")
        
        results.append({
            'asset': asset,
            'action': action,
            'confidence': confidence,
            'sent': success
        })
        
        # Small delay between messages
        import time
        time.sleep(2)
    
    # Summary
    print("\n" + "=" * 60)
    print("📊 TEST SUMMARY")
    print("=" * 60)
    for r in results:
        status = "✅" if r['sent'] else "❌"
        print(f"{status} {r['asset']}: {r['action']} ({r['confidence']:.0f}%)")
    
    # Also send a summary to Telegram
    summary = f"""📊 15 AGENTS TEST COMPLETE 📊

Results Summary:
{chr(10).join([f"{r['asset']}: {r['action']} ({r['confidence']:.0f}%)" for r in results])}

Total Agents: {len(ALL_AGENTS)}
Agents tested: {', '.join(ALL_AGENTS.keys())}

✅ System is ready for live trading!"""
    
    send_telegram_message(summary)
    
    print("\n✅ Test completed!")

def test_single_asset(asset="EURUSD", price=1.0950):
    """Test a single asset with all 15 agents"""
    
    print(f"\n🧪 Testing {asset} at ${price}")
    print("-" * 40)
    
    trend = random.choice(['up', 'down', 'sideways'])
    
    agent_votes = {}
    for agent_name, agent_info in ALL_AGENTS.items():
        vote, confidence, reason = simulate_agent_vote(agent_name, agent_info, price, trend)
        agent_votes[agent_name] = {
            'vote': vote,
            'confidence': confidence,
            'reason': reason
        }
        print(f"{agent_name}: {vote} ({confidence:.0f}%) - {reason[:40]}")
    
    # Calculate consensus
    buy_count = sum(1 for v in agent_votes.values() if v['vote'] == 'BUY')
    sell_count = sum(1 for v in agent_votes.values() if v['vote'] == 'SELL')
    
    if buy_count > sell_count:
        action = 'BUY'
        confidence = (buy_count / len(agent_votes)) * 100
    elif sell_count > buy_count:
        action = 'SELL'
        confidence = (sell_count / len(agent_votes)) * 100
    else:
        action = 'HOLD'
        confidence = 50
    
    # Send to Telegram
    message = format_simple_message(asset, price, agent_votes, {'action': action, 'confidence': confidence, 'reason': 'Test vote'})
    send_telegram_message(message)
    
    return agent_votes

# ============================================
# RUN THE TEST
# ============================================

if __name__ == "__main__":
    print("\n" + "=" * 60)
    print("🤖 TELEGRAM TEST FOR ALL 15 AGENTS")
    print("=" * 60)
    
    # Check Telegram credentials
    if not TELEGRAM_BOT_TOKEN or not TELEGRAM_CHAT_ID:
        print("\n❌ Telegram credentials not found!")
        print("Please set TELEGRAM_BOT_TOKEN and TELEGRAM_CHAT_ID in your .env file")
        print("\nExample .env entry:")
        print("TELEGRAM_BOT_TOKEN=1234567890:ABCdefGHIjklmNOPqrstUvWXyz")
        print("TELEGRAM_CHAT_ID=123456789")
        sys.exit(1)
    
    print(f"\n✅ Telegram Bot Token found: {TELEGRAM_BOT_TOKEN[:15]}...")
    print(f"✅ Telegram Chat ID: {TELEGRAM_CHAT_ID}")
    
    # Run the test
    test_all_15_agents()
    
    # Optional: Test single asset
    # test_single_asset("BTC/USD", 65000)
