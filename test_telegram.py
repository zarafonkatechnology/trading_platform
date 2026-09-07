"""
Test Enhanced Signal on Telegram
Run this to see how the new AI pipeline signals will appear in your Telegram
"""

import requests
import json
from datetime import datetime

# ============================================
# TELEGRAM CONFIGURATION - REPLACE WITH YOURS
# ============================================
TELEGRAM_BOT_TOKEN = "8723302516:AAGmEk4LmYg0NyfBM-DycbNLhQyFsswOd60"  # Replace with your bot token
TELEGRAM_CHAT_ID = "5888502889"      # Replace with your chat ID

# ============================================
# ENHANCED SIGNAL FORMATTER
# ============================================

def send_telegram_message(message: str):
    """Send message to Telegram"""
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    payload = {
        'chat_id': TELEGRAM_CHAT_ID,
        'text': message,
        'parse_mode': 'Markdown'
    }
    
    try:
        response = requests.post(url, json=payload, timeout=10)
        if response.status_code == 200:
            print("✅ Message sent to Telegram successfully")
            return True
        else:
            print(f"❌ Failed to send. Status: {response.status_code}")
            print(f"Response: {response.text}")
            return False
    except Exception as e:
        print(f"❌ Error sending message: {e}")
        return False


def format_enhanced_signal(symbol: str, signal_data: dict, 
                            agent_result: dict, flow_signal: dict,
                            mt4_connected: bool) -> str:
    """Format enhanced signal with AI pipeline data"""
    
    # Get agent consensus
    agent_decision = agent_result.get('decision', 'HOLD')
    agent_confidence = agent_result.get('confidence', 0)
    
    # Get flow signals
    cvd_value = flow_signal.get('cvd', 0)
    cvd_signal = "🟢 Bullish" if cvd_value > 0 else "🔴 Bearish" if cvd_value < 0 else "⚪ Neutral"
    sweep = flow_signal.get('liquidity_sweep', {}).get('swept', 'None')
    
    message = f"""
📊 *{symbol} – {signal_data['action']}*

*🤖 AI DELIBERATIVE PIPELINE*
━━━━━━━━━━━━━━━━━━━━━
🧠 *Agent Consensus:* {agent_decision} ({agent_confidence:.0f}%)
   • 📈 Analyst: {agent_result.get('analyst_score', 0):.0f}
   • ⚖️ Challenger: {agent_result.get('challenger_score', 0):.0f}
   • ✅ Validator: {agent_result.get('validator_score', 0):.0f}

📊 *Order Flow Analysis*
   • CVD: {cvd_signal} ({abs(cvd_value):.0f})
   • Liquidity Sweep: {sweep if sweep != 'None' else 'None detected'}
   • Volume Profile: {flow_signal.get('volume_profile', 'Normal')}

📊 *Signal Details*
━━━━━━━━━━━━━━━━━━━━━
• Level: {signal_data.get('level', signal_data.get('entry', 'N/A'))} ({signal_data.get('level_type', 'AI Detected')})
• Timeframe: {signal_data.get('timeframe', '15m')}
• Certainty: {signal_data.get('certainty', 0)}% ({signal_data.get('certainty_label', 'Moderate')})
• Level Strength: {signal_data.get('level_strength', 'N/A')}
• Volume Ratio: {signal_data.get('volume_ratio', 1)}x avg
• Market Regime: {signal_data.get('market_regime', 'TRENDING')}
• Trend Strength: {signal_data.get('trend_strength', 0)}%

🎯 *AI Recommendation:* {signal_data['action']} at {signal_data['entry']}
🛑 *Stop Loss:* {signal_data['stop_loss']}
✅ *Take Profit:* {signal_data['take_profit_1']} / {signal_data['take_profit_2']}

📈 *Expected Move*
   • Range: {signal_data['expected_low']} → {signal_data['expected_high']}
   • Pips: {signal_data['expected_pips']} pips
   • Max Hold: {signal_data['max_hold']} minutes

📋 *Risk Metrics*
   • Success Prob: {signal_data.get('success_probability', 0)}%
   • Momentum Strength: {signal_data.get('momentum_strength', 0)}%
   • Volume Spike: {signal_data.get('volume_spike', 0)}x
   • Risk/Reward: 1:{signal_data.get('risk_reward', 0):.1f}

🔌 *System Status*
   • MT4 Bridge: {'✅ CONNECTED' if mt4_connected else '⚠️ SIMULATED'}
   • AI Version: Deliberative Pipeline v2.0
   • Strategy: {signal_data.get('strategy', 'AI Deliberative')}

⏰ {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
"""
    return message


# ============================================
# TEST DATA (Based on your actual Telegram signals)
# ============================================

def test_nzdusd_signal():
    """Test NZDUSD signal (from your screenshot)"""
    
    print("\n" + "=" * 60)
    print("TEST 1: SENDING NZDUSD ENHANCED SIGNAL")
    print("=" * 60)
    
    signal_data = {
        'action': 'BUY',
        'entry': 0.56814,
        'stop_loss': 0.56572,
        'take_profit_1': 0.57425,
        'take_profit_2': 0.57624,
        'expected_low': 0.56670,
        'expected_high': 0.57160,
        'expected_pips': 24,
        'max_hold': 5,
        'success_probability': 95,
        'momentum_strength': 71,
        'volume_spike': 2.9,
        'risk_reward': 2.4,
        'strategy': 'Momentum Burst',
        'level': 0.56814,
        'level_type': 'Support',
        'certainty': 73,
        'certainty_label': 'Moderate',
        'level_strength': '92 (5/5 high-volume candles)',
        'volume_ratio': 1.8,
        'market_regime': 'TRENDING',
        'trend_strength': 78,
        'timeframe': '15m'
    }
    
    agent_result = {
        'decision': 'BUY',
        'confidence': 78.5,
        'analyst_score': 85,
        'challenger_score': 72,
        'validator_score': 76
    }
    
    flow_signal = {
        'cvd': 1245,
        'liquidity_sweep': {'swept': 'Support'},
        'volume_profile': 'High volume node at 0.5680',
        'score': 76
    }
    
    message = format_enhanced_signal('NZDUSD', signal_data, agent_result, flow_signal, True)
    return send_telegram_message(message)


def test_nasdaq_signal():
    """Test NASDAQ100 bullish breakout signal"""
    
    print("\n" + "=" * 60)
    print("TEST 2: SENDING NASDAQ100 BULLISH SIGNAL")
    print("=" * 60)
    
    signal_data = {
        'action': 'BUY',
        'entry': 19850.00,
        'stop_loss': 19750.00,
        'take_profit_1': 20050.00,
        'take_profit_2': 20150.00,
        'expected_low': 19800.00,
        'expected_high': 20000.00,
        'expected_pips': 150,
        'max_hold': 30,
        'success_probability': 88,
        'momentum_strength': 85,
        'volume_spike': 3.2,
        'risk_reward': 2.0,
        'strategy': 'Breakout Momentum',
        'level': 19850.00,
        'level_type': 'Resistance Break',
        'certainty': 85,
        'certainty_label': 'High',
        'level_strength': 'Strong breakout volume',
        'volume_ratio': 2.5,
        'market_regime': 'TRENDING',
        'trend_strength': 92,
        'timeframe': '15m'
    }
    
    agent_result = {
        'decision': 'BUY',
        'confidence': 85.0,
        'analyst_score': 90,
        'challenger_score': 82,
        'validator_score': 84
    }
    
    flow_signal = {
        'cvd': 3500,
        'liquidity_sweep': {'swept': 'Resistance'},
        'volume_profile': 'Breakout with high volume'
    }
    
    message = format_enhanced_signal('#NASDAQ100', signal_data, agent_result, flow_signal, True)
    return send_telegram_message(message)


def test_gold_signal():
    """Test GOLD bearish reversal signal"""
    
    print("\n" + "=" * 60)
    print("TEST 3: SENDING GOLD BEARISH SIGNAL")
    print("=" * 60)
    
    signal_data = {
        'action': 'SELL',
        'entry': 2350.00,
        'stop_loss': 2360.00,
        'take_profit_1': 2330.00,
        'take_profit_2': 2320.00,
        'expected_low': 2325.00,
        'expected_high': 2345.00,
        'expected_pips': 20,
        'max_hold': 15,
        'success_probability': 82,
        'momentum_strength': 78,
        'volume_spike': 2.1,
        'risk_reward': 2.5,
        'strategy': 'Reversal',
        'level': 2350.00,
        'level_type': 'Resistance',
        'certainty': 78,
        'certainty_label': 'Moderate',
        'level_strength': 'Double top formation',
        'volume_ratio': 1.6,
        'market_regime': 'RANGING',
        'trend_strength': 65,
        'timeframe': '15m'
    }
    
    agent_result = {
        'decision': 'SELL',
        'confidence': 76.0,
        'analyst_score': 80,
        'challenger_score': 75,
        'validator_score': 72
    }
    
    flow_signal = {
        'cvd': -2100,
        'liquidity_sweep': {'swept': 'Support'},
        'volume_profile': 'Distribution at highs'
    }
    
    message = format_enhanced_signal('GOLD', signal_data, agent_result, flow_signal, True)
    return send_telegram_message(message)


def test_mt4_disconnected():
    """Test MT4 disconnected status"""
    
    print("\n" + "=" * 60)
    print("TEST 4: SENDING SIGNAL WITH MT4 DISCONNECTED")
    print("=" * 60)
    
    signal_data = {
        'action': 'BUY',
        'entry': 1.0890,
        'stop_loss': 1.0870,
        'take_profit_1': 1.0930,
        'take_profit_2': 1.0950,
        'expected_low': 1.0880,
        'expected_high': 1.0920,
        'expected_pips': 40,
        'max_hold': 10,
        'success_probability': 75,
        'momentum_strength': 68,
        'volume_spike': 1.5,
        'risk_reward': 2.0,
        'strategy': 'Range Trade',
        'level': 1.0890,
        'level_type': 'Support',
        'certainty': 70,
        'certainty_label': 'Moderate',
        'level_strength': '3 touches',
        'volume_ratio': 1.2,
        'market_regime': 'RANGING',
        'trend_strength': 45,
        'timeframe': '15m'
    }
    
    agent_result = {
        'decision': 'BUY',
        'confidence': 68.0,
        'analyst_score': 72,
        'challenger_score': 65,
        'validator_score': 68
    }
    
    flow_signal = {
        'cvd': 450,
        'liquidity_sweep': {'swept': 'None'},
        'volume_profile': 'Normal'
    }
    
    message = format_enhanced_signal('EURUSD', signal_data, agent_result, flow_signal, False)
    return send_telegram_message(message)


# ============================================
# MAIN TEST
# ============================================

def run_all_tests():
    """Run all telegram tests"""
    
    print("\n" + "=" * 70)
    print("🚀 ENHANCED AI PIPELINE TELEGRAM TEST")
    print("=" * 70)
    print(f"Bot Token: {TELEGRAM_BOT_TOKEN[:15]}...")
    print(f"Chat ID: {TELEGRAM_CHAT_ID}")
    print("=" * 70)
    
    # Check configuration
    if TELEGRAM_BOT_TOKEN == "YOUR_BOT_TOKEN_HERE" or TELEGRAM_CHAT_ID == "YOUR_CHAT_ID_HERE":
        print("\n❌ ERROR: Please update TELEGRAM_BOT_TOKEN and TELEGRAM_CHAT_ID first!")
        print("\nHow to get them:")
        print("1. Bot Token: Message @BotFather on Telegram → /newbot → create bot → copy token")
        print("2. Chat ID: Message @userinfobot on Telegram → /start → copy your ID")
        return
    
    # Send test messages
    results = []
    
    # Test 1: NZDUSD
    results.append(('NZDUSD', test_nzdusd_signal()))
    
    # Test 2: NASDAQ
    results.append(('#NASDAQ100', test_nasdaq_signal()))
    
    # Test 3: GOLD
    results.append(('GOLD', test_gold_signal()))
    
    # Test 4: MT4 Disconnected
    results.append(('EURUSD (MT4 Offline)', test_mt4_disconnected()))
    
    # Summary
    print("\n" + "=" * 70)
    print("📊 TEST SUMMARY")
    print("=" * 70)
    
    success_count = sum(1 for _, success in results if success)
    total_count = len(results)
    
    for name, success in results:
        status = "✅" if success else "❌"
        print(f"  {status} {name}")
    
    print(f"\n✅ {success_count}/{total_count} messages sent successfully")
    
    if success_count == total_count:
        print("\n🎉 ALL TESTS PASSED! Enhanced signals are working!")
        print("\nNext steps:")
        print("1. Update your run_trading_cycle() to use format_enhanced_signal()")
        print("2. Integrate agent_result and flow_signal from your pipeline")
        print("3. Deploy to production")
    else:
        print("\n⚠️ Some messages failed. Check your bot token and chat ID.")


if __name__ == "__main__":
    run_all_tests()