#!/usr/bin/env python3
"""
Telegram Bot for Multi-Agent Trading System
Complete working version with /vote, /consensus, /pipeline, /sr commands
"""

import telebot
import requests
import time
import json
import logging
from agent_activation import RegimeActivationIntegration
from mt4_price_provider import get_mt4_prices
# Then create instance:
regime_activation = RegimeActivationIntegration()

from datetime import datetime

# ============ CONFIGURATION ============
TELEGRAM_BOT_TOKEN = "8723302516:AAGmEk4LmYg0NyfBM-DycbNLhQyFsswOd60"
API_BASE_URL = "http://localhost:5000/api"

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

bot = telebot.TeleBot(TELEGRAM_BOT_TOKEN)
logger.info("✅ Bot instance created")

# ============ OANDA HELPERS (using your existing bridge) ============
def get_current_price(pair):
    """Fetch current price from MT4"""
    try:
        mt4 = get_mt4_prices()
        price_data = mt4.get_price(pair.replace('/', '_'))
        current_price = price_data.get('mid') if price_data.get('success') else None
        if resp.status_code == 200:
            data = resp.json()
            if data.get('success'):
                return data.get('mid', data.get('bid', 0))
        return None
    except Exception as e:
        logger.error(f"Price fetch error: {e}")
        return None

def get_recent_candles(pair, count=100, granularity="H1"):
    """Fetch recent candles from MT4 (limited support)"""
    try:
        # resp = requests.get(f"{API_BASE_URL}/oanda/history/{pair}?count={count}&granularity={granularity}", timeout=10)
        candles = [] 
        if resp.status_code == 200:
            data = resp.json()
            if data.get('success'):
                return data.get('candles', [])
        return []
    except Exception as e:
        logger.error(f"Candle fetch error: {e}")
        return []

def get_volume_profile(pair):
    """Simulate volume profile (can be extended with real data)"""
    return {'avg_volume': 15000, 'volume_ratio': 1.2}

def get_mtf_alignment(pair):
    """Simulate multi‑timeframe alignment (1 = bullish, 0 = bearish)"""
    return 0.7

# ============ API HELPER ============
def api_call(endpoint, method='GET', data=None):
    try:
        url = f"{API_BASE_URL}{endpoint}"
        if method == 'GET':
            response = requests.get(url, timeout=10)
        else:
            response = requests.post(url, json=data, timeout=10)
        if response.status_code == 200:
            return response.json()
        else:
            return {'success': False, 'error': f'HTTP {response.status_code}'}
    except Exception as e:
        return {'success': False, 'error': str(e)}

def check_system_health():
    result = api_call('/health')
    return result.get('status') == 'healthy'

# ============ COMMAND HANDLERS ============
@bot.message_handler(commands=['start'])
def send_welcome(message):
    welcome_text = """
🤖 <b>Multi-Agent Trading Bot</b>

Welcome! I have access to 23 AI trading agents.

<b>Commands:</b>
/vote &lt;pair&gt; - Layer-based voting consensus
/consensus &lt;pair&gt; - Simple agent consensus
/pipeline &lt;pair&gt; - Run 4-layer trading pipeline
/sr &lt;pair&gt; - Supply/Demand analysis (Agent_R Ultimate)
/status - Check system health
/agents - List all agents
/teach - Force DeepSeek teaching
/help - Show this message

<b>Examples:</b>
/vote EURUSD
/sr GOLD
"""
    bot.reply_to(message, welcome_text, parse_mode='HTML')

@bot.message_handler(commands=['help'])
def send_help(message):
    help_text = """
<b>📚 Available Commands</b>

/vote &lt;pair&gt; - Layer-based voting
/consensus &lt;pair&gt; - Simple consensus
/pipeline &lt;pair&gt; - Full pipeline
/sr &lt;pair&gt; - S/R with Monte Carlo & Volume
/status - System health
/agents - List agents
/teach - Force teaching
"""
    bot.reply_to(message, help_text, parse_mode='HTML')

@bot.message_handler(commands=['status'])
def system_status(message):
    status_msg = bot.reply_to(message, "🟡 Checking system status...")
    if check_system_health():
        bot.edit_message_text("✅ <b>Trading System: ONLINE</b>", chat_id=message.chat.id, message_id=status_msg.message_id, parse_mode='HTML')
    else:
        bot.edit_message_text("❌ <b>Trading System: OFFLINE</b>", chat_id=message.chat.id, message_id=status_msg.message_id, parse_mode='HTML')

@bot.message_handler(commands=['agents'])
def list_agents(message):
    status_msg = bot.reply_to(message, "📊 Fetching agents...")
    result = api_call('/agents/roles')
    if result.get('success'):
        agents = result.get('agents', [])
        text = "<b>🤖 Agent Roles</b>\n\n"
        for agent in agents[:15]:
            text += f"• <b>{agent['name']}</b>: {agent.get('role', 'Trading Agent')}\n"
        bot.edit_message_text(text, chat_id=message.chat.id, message_id=status_msg.message_id, parse_mode='HTML')
    else:
        bot.edit_message_text(f"❌ Error: {result.get('error')}", chat_id=message.chat.id, message_id=status_msg.message_id)

@bot.message_handler(commands=['sr'])
def sr_command(message):
    """Supply/Demand analysis using Agent_R Ultimate (Monte Carlo + Volume)"""
    try:
        args = message.text.split()
        pair = args[1].upper() if len(args) > 1 else "EURUSD"
        
        status_msg = bot.reply_to(message, f"🏛️ Running S/R analysis for {pair}...")
        
        # 1. Get current price
        current_price = get_current_price(pair)
        if not current_price:
            bot.edit_message_text("❌ Could not fetch current price. Is MT4 running with EA attached?", 
                          chat_id=message.chat.id, message_id=status_msg.message_id)
            return
        
        # 2. Fetch recent candles (100 H1 candles)
        candles = get_recent_candles(pair, count=100, granularity="H1")
        if not candles:
            bot.edit_message_text("⚠️ No candle data. Using simulated zone detection.", 
                                  chat_id=message.chat.id, message_id=status_msg.message_id)
        
        # 3. Initialize Agent_R Ultimate
        from backend.agents.agent_r_ultimate import AgentRUltimate
        agent_r = AgentRUltimate()
        
        # 4. Update with candle data (if any)
        if candles:
            agent_r.update_from_candles(candles)
        
        # 5. Simulate Agent_J volume data (or fetch from real agent)
        volume_data = {
            'current_volume': 25000,
            'avg_volume': 15000,
            'volume_ratio': 1.67,
            'volume_surge': True
        }
        agent_r.update_from_agent_j(volume_data)
        
        # 6. Run analysis
        signal_data = {
            'price': current_price,
            'volume': 25000,
            'weekly_trend': 'up',
            'daily_trend': 'up',
            'volatility': 0.005
        }
        result = agent_r.analyze(signal_data)
        
        # 7. Build response
        response = f"""
🏛️ <b>Agent_R Ultimate – S/R Analysis for {pair}</b>
━━━━━━━━━━━━━━━━━━━━━

🎯 <b>Vote:</b> {result['vote']}
📊 <b>Confidence:</b> {result['confidence']}%
💰 <b>Position Size:</b> {result['position_size']*100}%
✅ <b>Genuine:</b> {'Yes' if result['is_genuine'] else 'No'}
📉 <b>Manipulation Score:</b> {result['manipulation_score']}

📍 <b>Active Level:</b> {result['level_info']['price']:.5f} ({result['level_info']['type']})
💪 <b>Strength:</b> {result['level_info']['strength']}%
🔄 <b>Touches:</b> {result['level_info']['touches']}

🎲 <b>Monte Carlo Probabilities:</b>
   📈 Breakout Up: {result['monte_carlo']['breakout_up']}%
   📉 Breakout Down: {result['monte_carlo']['breakout_down']}%
   🔄 Bounce: {result['monte_carlo']['bounce']}%

💵 <b>Estimated Hidden Funds:</b> ${result['hidden_funds_estimate']:,.0f}

💬 <b>Reasoning:</b> {result['reasoning'][:200]}...
"""
        bot.edit_message_text(response, chat_id=message.chat.id, message_id=status_msg.message_id, parse_mode='HTML')
        
    except Exception as e:
        bot.edit_message_text(f"❌ Error: {str(e)}", chat_id=message.chat.id, message_id=status_msg.message_id)
        logger.exception("SR command failed")

@bot.message_handler(commands=['consensus'])
def get_consensus(message):
    args = message.text.split()
    pair = args[1].upper() if len(args) > 1 else "EURUSD"
    status_msg = bot.reply_to(message, f"🗳️ Getting consensus for {pair}...")
    result = api_call('/advisor/consensus', method='POST', data={'asset_type': pair})
    if result.get('success'):
        text = f"<b>📊 Consensus for {pair}</b>\n\n🎯 Final: {result.get('final_recommendation', 'HOLD')}\n📈 Confidence: {result.get('confidence', 50)}%"
        bot.edit_message_text(text, chat_id=message.chat.id, message_id=status_msg.message_id, parse_mode='HTML')
    else:
        bot.edit_message_text(f"❌ Error: {result.get('error')}", chat_id=message.chat.id, message_id=status_msg.message_id)

@bot.message_handler(commands=['vote'])
def cmd_vote(message):
    try:
        args = message.text.split()
        pair = args[1].upper() if len(args) > 1 else "EURUSD"
        status_msg = bot.reply_to(message, f"🗳️ Getting layer-based consensus for {pair}...")
        response = requests.post("http://localhost:5000/api/consensus/layer", json={"pair": pair}, timeout=15)
        if response.status_code == 200:
            data = response.json()
            if data.get('success'):
                consensus = data.get('result', {}).get('consensus', {})
                layer_scores = consensus.get('layer_scores', {})
                msg = f"📊 <b>Layer-Based Voting for {pair}</b>\n━━━━━━━━━━━━━━━━━━━━━\n\n"
                msg += f"🔵 DIRECTION (35%): {layer_scores.get('direction', 0):.1f}\n"
                msg += f"🟢 CONFIRMATION (30%): {layer_scores.get('confirmation', 0):.1f}\n"
                msg += f"🟡 ENTRY (25%): {layer_scores.get('entry', 0):.1f}\n"
                msg += f"🔴 RISK (10%): {layer_scores.get('risk', 0):.1f}\n\n"
                msg += f"━━━━━━━━━━━━━━━━━━━━━\n"
                msg += f"🎯 <b>Decision:</b> {consensus.get('action', 'HOLD')} ({consensus.get('confidence', 0)}%)\n"
                bot.edit_message_text(msg, chat_id=message.chat.id, message_id=status_msg.message_id, parse_mode='HTML')
            else:
                bot.edit_message_text(f"❌ {data.get('error')}", chat_id=message.chat.id, message_id=status_msg.message_id)
        else:
            bot.edit_message_text("❌ Trading system offline", chat_id=message.chat.id, message_id=status_msg.message_id)
    except Exception as e:
        bot.edit_message_text(f"❌ Error: {str(e)}", chat_id=message.chat.id, message_id=status_msg.message_id)
@bot.message_handler(commands=['agents_active'])
def show_active_agents(message):
    """Show which agents are currently active"""
    status = regime_activation.activation_manager.get_regime_summary()
    
    active_list = status.get('active_list', [])
    inactive_list = status.get('inactive_list', [])
    
    response = f"""
🎯 <b>CURRENT MARKET REGIME</b>
━━━━━━━━━━━━━━━━━━━━━
📊 <b>Regime:</b> {status.get('regime', 'Unknown')}
📈 <b>Confidence:</b> {status.get('confidence', 0)}%

✅ <b>ACTIVE AGENTS</b> ({len(active_list)})
"""
    for agent in active_list[:15]:
        response += f"   • {agent}\n"
    
    if inactive_list:
        response += f"\n❌ <b>INACTIVE AGENTS</b> ({len(inactive_list)})\n"
        for agent in inactive_list[:10]:
            response += f"   • {agent}\n"
    
    bot.reply_to(message, response, parse_mode='HTML')
@bot.message_handler(commands=['agent_weights'])
def show_agent_weights(message):
    """Show current agent weights based on regime"""
    weights = regime_activation.get_active_agent_weights()
    
    sorted_weights = sorted(weights.items(), key=lambda x: x[1], reverse=True)
    
    response = "<b>⚖️ AGENT WEIGHTS BY REGIME</b>\n━━━━━━━━━━━━━━━━━━━━━\n\n"
    
    for agent, weight in sorted_weights[:15]:
        bar_length = int(weight * 10)
        bar = "█" * bar_length + "░" * (10 - bar_length)
        response += f"• <b>{agent}</b>: {bar} {weight:.1f}x\n"
    
    bot.reply_to(message, response, parse_mode='HTML')
@bot.message_handler(commands=['regime_history'])
def show_regime_history(message):
    """Show recent regime changes"""
    history = regime_activation.activation_manager.regime_history[-10:]
    
    if not history:
        bot.reply_to(message, "No regime history yet")
        return
    
    response = "<b>📜 RECENT REGIME CHANGES</b>\n━━━━━━━━━━━━━━━━━━━━━\n\n"
    
    for regime, timestamp in history[-10:]:
        time_str = timestamp.strftime("%H:%M:%S")
        response += f"• {time_str} → {regime.value}\n"
    
    bot.reply_to(message, response, parse_mode='HTML')

@bot.message_handler(commands=['agent_profile'])
def show_agent_profile(message):
    """Show profile for a specific agent"""
    args = message.text.split()
    agent_name = args[1] if len(args) > 1 else None
    
    if not agent_name:
        bot.reply_to(message, "Usage: /agent_profile Agent_A")
        return
    
    profiles = regime_activation.activation_manager.agent_profiles
    profile = profiles.get(agent_name)
    
    if not profile:
        bot.reply_to(message, f"Agent {agent_name} not found")
        return
    
    # Use HTML instead of Markdown to avoid parsing issues
    response = f"""
<b>📋 AGENT PROFILE: {agent_name}</b>
━━━━━━━━━━━━━━━━━━━━━
🔧 <b>Type:</b> {profile.agent_type}

✅ <b>Preferred Regimes:</b>
"""
    for regime in profile.preferred_regimes:
        response += f"   • {regime.value}\n"
    
    if profile.avoided_regimes:
        response += f"\n❌ <b>Avoided Regimes:</b>\n"
        for regime in profile.avoided_regimes:
            response += f"   • {regime.value}\n"
    
    response += f"\n📊 <b>Currently Active:</b> {'✅ YES' if profile.current_activation else '❌ NO'}"
    response += f"\n⚖️ <b>Current Weight:</b> {regime_activation.activation_manager.get_agent_weight(agent_name):.1f}x"
    
    bot.reply_to(message, response, parse_mode='HTML')
@bot.message_handler(commands=['pipeline'])
def run_pipeline(message):
    args = message.text.split()
    pair = args[1].upper() if len(args) > 1 else "EURUSD"
    status_msg = bot.reply_to(message, f"🔄 Running pipeline for {pair}...")
    result = api_call('/trading/pipeline', method='POST', data={'pair': pair})
    if result.get('success'):
        decision = result.get('decision', {})
        text = f"<b>🏆 Pipeline for {pair}</b>\n\n🎯 Action: {decision.get('action', 'HOLD')}\n📊 Confidence: {decision.get('confidence', 0)}%\n💡 Reason: {decision.get('reason', 'N/A')}"
        bot.edit_message_text(text, chat_id=message.chat.id, message_id=status_msg.message_id, parse_mode='HTML')
    else:
        bot.edit_message_text(f"❌ Error: {result.get('error')}", chat_id=message.chat.id, message_id=status_msg.message_id)

@bot.message_handler(commands=['teach'])
def force_teach(message):
    status_msg = bot.reply_to(message, "🧠 Teaching all agents...")
    result = api_call('/teach_all', method='POST', data={'topic': 'trading strategy'})
    if result.get('success'):
        text = f"✅ Taught {result.get('agents_taught', 0)} agents! XP awarded: {result.get('total_xp_awarded', 0)}"
        bot.edit_message_text(text, chat_id=message.chat.id, message_id=status_msg.message_id)
    else:
        bot.edit_message_text(f"❌ Error: {result.get('error')}", chat_id=message.chat.id, message_id=status_msg.message_id)
from momentum_burst import MomentumBurstIntegration

# Initialize momentum burst strategy
momentum_burst = MomentumBurstIntegration()
momentum_burst.set_telegram_bot(bot)

@bot.message_handler(commands=['momentum'])
def momentum_status(message):
    """Get momentum burst strategy status"""
    status_msg = momentum_burst.get_status_message()
    bot.reply_to(message, status_msg, parse_mode='Markdown')


@bot.message_handler(commands=['fast_scan'])
def fast_scan(message):
    """Force scan for momentum opportunities"""
    bot.reply_to(message, "⚡ Scanning for momentum bursts...")
    trades = momentum_burst.scan_and_trade()
    if trades:
        bot.reply_to(message, f"✅ Executed {len(trades)} momentum trades")
    else:
        bot.reply_to(message, "📊 No momentum bursts detected")
@bot.message_handler(commands=['momentum_prob'])
def momentum_probability(message):
    """Get current momentum probability analysis for an asset"""
    args = message.text.split()
    asset = args[1] if len(args) > 1 else "NAS100/USD"
    
    # Get current price (implement your price fetch)
    current_price = get_current_price(asset)
    volume_ratio = get_volume_ratio(asset)
    
    # Create temporary detector for analysis
    from momentum_burst import MomentumBurstDetector
    detector = MomentumBurstDetector()
    
    # Update with latest data
    detector.update_price(asset, current_price, volume_ratio * 10000)
    
    # Analyze both directions
    buy_analysis = detector.calculate_probability_and_range(asset, 'BUY', current_price)
    sell_analysis = detector.calculate_probability_and_range(asset, 'SELL', current_price)
    
    response = f"""
📊 *MOMENTUM ANALYSIS - {asset}*
━━━━━━━━━━━━━━━━━━━━━

🟢 *BUY SIGNAL*
   Probability: {buy_analysis['success_probability']:.0f}%
   Expected Range: {buy_analysis['expected_entry_range'][0]:.2f} → {buy_analysis['expected_entry_range'][1]:.2f}
   Risk/Reward: 1:{buy_analysis['risk_reward_ratio']:.1f}
   Momentum: {buy_analysis['momentum_strength']:.0f}%

🔴 *SELL SIGNAL*
   Probability: {sell_analysis['success_probability']:.0f}%
   Expected Range: {sell_analysis['expected_entry_range'][0]:.2f} → {sell_analysis['expected_entry_range'][1]:.2f}
   Risk/Reward: 1:{sell_analysis['risk_reward_ratio']:.1f}
   Momentum: {sell_analysis['momentum_strength']:.0f}%

💡 *Recommendation:* {'BUY' if buy_analysis['success_probability'] > sell_analysis['success_probability'] else 'SELL'}
"""
    bot.reply_to(message, response, parse_mode='Markdown')
@bot.message_handler(commands=['test_momentum'])
def test_momentum(message):
    """Simulate a momentum burst for testing"""
    # Simulate a trade
    test_trade = {
        'asset': 'NAS100/USD',
        'direction': 'BUY',
        'entry_price': 18250.00,
        'confidence': 85,
        'stop_loss': 18230.00,
        'take_profit_1': 18280.00,
        'take_profit_2': 18300.00,
        'max_hold_minutes': 5,
        'probability_analysis': {
            'success_probability': 78,
            'expected_entry_range': (18240, 18270),
            'expected_return_pct': 0.35,
            'risk_reward_ratio': 2.5,
            'momentum_strength': 72
        }
    }
    
    # Send simulated signal
    prob = test_trade['probability_analysis']
    prob_bar = '█' * int(prob['success_probability'] / 10) + '░' * (10 - int(prob['success_probability'] / 10))
    
    message_text = f"""
🧪 *TEST MOMENTUM SIGNAL*

📊 *Asset:* {test_trade['asset']}
🎯 *Action:* {test_trade['direction']}
📈 *Entry Price:* {test_trade['entry_price']:.2f}

━━━━━━━━━━━━━━━━━━━━━
*📈 PROBABILITY ANALYSIS*
━━━━━━━━━━━━━━━━━━━━━
🎲 *Success Probability:* {prob['success_probability']:.0f}% {prob_bar}
💪 *Momentum Strength:* {prob['momentum_strength']:.0f}%

━━━━━━━━━━━━━━━━━━━━━
*📊 EXPECTED PRICE RANGE*
━━━━━━━━━━━━━━━━━━━━━
📍 *Expected Range:* {prob['expected_entry_range'][0]:.2f} → {prob['expected_entry_range'][1]:.2f}
📈 *Expected Return:* +{prob['expected_return_pct']:.2f}%
⚖️ *Risk/Reward:* 1:{prob['risk_reward_ratio']:.1f}

━━━━━━━━━━━━━━━━━━━━━
*🛡️ RISK MANAGEMENT*
━━━━━━━━━━━━━━━━━━━━━
🛑 *Stop Loss:* {test_trade['stop_loss']:.2f}
✅ *TP1:* {test_trade['take_profit_1']:.2f}
✅ *TP2:* {test_trade['take_profit_2']:.2f}
⏱️ *Max Hold:* {test_trade['max_hold_minutes']} minutes

⚠️ *THIS IS A TEST SIGNAL*
"""
    bot.reply_to(message, message_text, parse_mode='Markdown')
@bot.message_handler(func=lambda message: True)
def handle_unknown(message):
    bot.reply_to(message, "❓ Unknown command. Type /help")

# ============ BOT RUNNER ============
def run_bot():
    print("=" * 50)
    print("🤖 Multi-Agent Trading Bot")
    print("=" * 50)
    print(f"📍 Bot Token: {TELEGRAM_BOT_TOKEN[:15]}...")
    print("📋 Commands: /vote, /consensus, /pipeline, /sr, /status, /agents, /teach, /help")
    print("=" * 50)
    if check_system_health():
        print("✅ Trading system ONLINE")
    else:
        print("⚠️ Trading system OFFLINE – start app_code.py")
    print("✅ Bot running... Press Ctrl+C to stop")
    bot.infinity_polling(timeout=60)

if __name__ == '__main__':
    run_bot()
