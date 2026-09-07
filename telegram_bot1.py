#!/usr/bin/env python3
"""
Telegram Bot for Multi-Agent Trading System
Supports Agent_N (Intermarket) and Agent_W (Whisper)
"""

import telebot
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton
import requests
import json
import os
from datetime import datetime

# Configuration
TELEGRAM_BOT_TOKEN = os.getenv('TELEGRAM_BOT_TOKEN', '8723302516:AAGmEk4LmYg0NyfBM-DycbNLhQyFsswOd60')
API_BASE_URL = "http://localhost:5000/api"

# Initialize bot
bot = telebot.TeleBot(TELEGRAM_BOT_TOKEN)

# Store user sessions (which agent they're talking to)
user_sessions = {}

# Agent list with descriptions
AGENTS = {
    'Agent_A': '📈 Trend Follower - Moving Average Expert',
    'Agent_B': '🔄 Mean Reversion - RSI & Bollinger Bands',
    'Agent_C': '⚡ Momentum - Price Rate of Change',
    'Agent_D': '📊 Volatility - ATR Analysis',
    'Agent_E': '🔬 Microstructure - Order Flow',
    'Agent_F': '🕯️ Candlestick - Japanese Patterns',
    'Agent_G': '🐋 Whale Tracker - COT Analysis',
    'Agent_H': '📐 Fibonacci - Retracement Levels',
    'Agent_I': '📰 Sentiment Master - News Analysis',
    'Agent_J': '📊 Volume Master - Order Flow',
    'Agent_K': '☁️ Ichimoku Expert - Cloud Breakouts',
    'Agent_L': '💰 Fundamental Master - Economic Calendar',
    'Agent_M': '📈 Market Profile - TPO Analysis',
    'Agent_N': '🌍 Intermarket Master - Cross-Asset Correlations',  # NEW
    'Agent_O': '📅 Seasonality Expert - Time Patterns',
    'Agent_P': '🕵️ Whisper Analyst - Dark Pool Leaks',
    'Agent_Q': '🐋 Dark Pool Whale - FINRA TRF',
    'Agent_R': '🏔️ Supply & Demand - Support/Resistance',
    'Agent_S': '🎯 Sentiment Pro - Advanced NLP',
    'Agent_T': '📊 Volume Controller - Confirmation',
    'Agent_U': '🔗 Intermarket Pro - Advanced Correlations',
    'Agent_V': '🔄 Seasonality Pro - Cycle Analysis',
    'Agent_W': '🤝 Consensus Agent - Multi-Agent Coordinator'  # NEW
}

# Agent specializations
AGENT_SPECIALIZATIONS = {
    'Agent_N': """
🌍 INTERMARKET MASTER - Agent_N

Specializes in:
• Dollar Index (DXY) correlations
• Gold-EUR inverse relationship  
• Bond market signals
• S&P 500 risk sentiment
• VIX fear gauge analysis

Example questions:
- "What's the dollar index doing?"
- "How does gold affect EURUSD?"
- "Is the market in risk-on mode?"
- "What's the VIX telling us?"
""",
    'Agent_W': """
🤝 CONSENSUS AGENT - Agent_W

Specializes in:
• Coordinating all 22 agents
• Aggregating votes to find consensus
• Resolving conflicting signals
• Weighted voting analysis
• Final trading recommendations

Example questions:
- "What's the consensus on EURUSD?"
- "Which agents agree on this trade?"
- "What's the overall sentiment?"
- "Give me the final recommendation"
"""
}

@bot.message_handler(commands=['start'])
def send_welcome(message):
    """Welcome message with agent list"""
    user_name = message.from_user.first_name
    welcome_text = f"""
🤖 *Welcome to Multi-Agent Trading System, {user_name}!*

I have access to 23 specialized AI trading agents.

*Available Agents:*

{chr(10).join([f'{k}: {v}' for k, v in AGENTS.items()])}

*Commands:*
/agents - List all agents
/agent_N - Chat with Agent_N (Intermarket Master)
/agent_W - Chat with Agent_W (Consensus Agent)
/ask [agent_name] [question] - Ask any agent a question
/consensus [pair] - Get consensus from all agents
/help - Show this message

*Example:* `/ask Agent_N What is the dollar index doing?`
    """
    bot.reply_to(message, welcome_text, parse_mode='Markdown')

@bot.message_handler(commands=['help'])
def send_help(message):
    help_text = """
📚 *Help Guide*

*To chat with an agent:*
1. Use /agent_N to talk to Agent_N
2. Use /agent_W to talk to Agent_W
3. Or use /ask [agent] [question]

*Examples:*
`/ask Agent_N Is gold correlated with EURUSD?`
`/ask Agent_W What's the consensus on GBPUSD?`
`/consensus EURUSD`

*Agent_N (Intermarket Master)*
- Analyzes correlations between assets
- Dollar Index, Gold, Bonds, Stocks

*Agent_W (Consensus Agent)*
- Aggregates all 22 agents' votes
- Gives final trading recommendation
    """
    bot.reply_to(message, help_text, parse_mode='Markdown')

@bot.message_handler(commands=['agents'])
def list_agents(message):
    """List all available agents"""
    agent_list = "*🤖 Available Agents:*\n\n"
    for name, desc in AGENTS.items():
        agent_list += f"• *{name}*: {desc}\n"
    
    agent_list += "\nUse /ask [agent_name] [question] to ask any agent!"
    bot.reply_to(message, agent_list, parse_mode='Markdown')

@bot.message_handler(commands=['agent_N'])
def agent_n_chat(message):
    """Start chat with Agent_N (Intermarket Master)"""
    user_sessions[message.chat.id] = 'Agent_N'
    
    response = f"""
🤖 *You are now chatting with Agent_N (Intermarket Master)*

{AGENT_SPECIALIZATIONS['Agent_N']}

Send me your question about intermarket analysis!
Type /end to stop chatting.
    """
    bot.reply_to(message, response, parse_mode='Markdown')

@bot.message_handler(commands=['agent_W'])
def agent_w_chat(message):
    """Start chat with Agent_W (Consensus Agent)"""
    user_sessions[message.chat.id] = 'Agent_W'
    
    response = f"""
🤖 *You are now chatting with Agent_W (Consensus Agent)*

{AGENT_SPECIALIZATIONS['Agent_W']}

Send me your trading question or ask for consensus!
Type /end to stop chatting.
    """
    bot.reply_to(message, response, parse_mode='Markdown')

@bot.message_handler(commands=['ask'])
def ask_agent(message):
    """Ask any agent a question - /ask Agent_Name question"""
    try:
        text = message.text.replace('/ask', '').strip()
        parts = text.split(' ', 1)
        
        if len(parts) < 2:
            bot.reply_to(message, "❌ Usage: /ask [agent_name] [question]\nExample: /ask Agent_N What is the dollar index doing?")
            return
        
        agent_name = parts[0]
        question = parts[1]
        
        # Validate agent
        if agent_name not in AGENTS:
            bot.reply_to(message, f"❌ Agent '{agent_name}' not found. Use /agents to see available agents.")
            return
        
        # Send typing indicator
        bot.send_chat_action(message.chat.id, 'typing')
        
        # Call the chat API
        response = requests.post(
            f"{API_BASE_URL}/chat/ask",
            json={"agent_name": agent_name, "question": question},
            timeout=30
        )
        
        if response.status_code == 200:
            data = response.json()
            if data.get('success'):
                answer = data.get('response')
                # Format response
                formatted = f"🤖 *{agent_name}*:\n\n{answer}\n\n✨ +{data.get('xp_gained', 0)} XP"
                bot.reply_to(message, formatted, parse_mode='Markdown')
            else:
                bot.reply_to(message, f"❌ Error: {data.get('error', 'Unknown error')}")
        else:
            bot.reply_to(message, "❌ Could not reach trading system. Make sure the server is running.")
            
    except Exception as e:
        bot.reply_to(message, f"❌ Error: {str(e)}")

@bot.message_handler(commands=['consensus'])
def get_consensus(message):
    """Get consensus from all agents for a pair"""
    try:
        text = message.text.replace('/consensus', '').strip()
        pair = text if text else "EURUSD"
        
        bot.send_chat_action(message.chat.id, 'typing')
        
        # Call the consensus API
        response = requests.post(
            f"{API_BASE_URL}/advisor/consensus",
            json={"asset_type": pair},
            timeout=30
        )
        
        if response.status_code == 200:
            data = response.json()
            consensus_text = f"""
📊 *Consensus Report for {pair}*

🤖 *Agent Consensus:*
{data.get('consensus_summary', 'Analyzing...')}

🎯 *Final Recommendation:* {data.get('final_recommendation', 'HOLD')}

💡 *Confidence:* {data.get('confidence', 50)}%
            """
            bot.reply_to(message, consensus_text, parse_mode='Markdown')
        else:
            bot.reply_to(message, "❌ Could not get consensus. Make sure the system is running.")
            
    except Exception as e:
        bot.reply_to(message, f"❌ Error: {str(e)}")

@bot.message_handler(commands=['end'])
def end_session(message):
    """End current agent session"""
    if message.chat.id in user_sessions:
        del user_sessions[message.chat.id]
        bot.reply_to(message, "✅ Session ended. Use /agents to see available agents.")
    else:
        bot.reply_to(message, "No active session. Use /agents to start chatting.")

@bot.message_handler(func=lambda message: True)
def handle_message(message):
    """Handle regular messages (when in session with an agent)"""
    chat_id = message.chat.id
    
    if chat_id in user_sessions:
        agent_name = user_sessions[chat_id]
        question = message.text
        
        bot.send_chat_action(chat_id, 'typing')
        
        try:
            response = requests.post(
                f"{API_BASE_URL}/chat/ask",
                json={"agent_name": agent_name, "question": question},
                timeout=30
            )
            
            if response.status_code == 200:
                data = response.json()
                if data.get('success'):
                    answer = data.get('response')
                    bot.reply_to(message, f"🤖 *{agent_name}*:\n\n{answer}", parse_mode='Markdown')
                else:
                    bot.reply_to(message, f"❌ {data.get('error', 'Unknown error')}")
            else:
                bot.reply_to(message, "❌ System error. Please try again.")
                
        except Exception as e:
            bot.reply_to(message, f"❌ Connection error: {str(e)}")
    else:
        # Not in session - show help
        help_msg = """
💡 *How to use me:*

• /agents - List all agents
• /agent_N - Chat with Agent_N (Intermarket)
• /agent_W - Chat with Agent_W (Consensus)
• /ask [agent] [question] - Ask any agent
• /consensus [pair] - Get trading consensus

Example: `/ask Agent_N What is the correlation between gold and USD?`
        """
        bot.reply_to(message, help_msg, parse_mode='Markdown')

def run_bot():
    """Start the Telegram bot"""
    print("🤖 Telegram Bot Starting...")
    print("📍 Bot Token:", TELEGRAM_BOT_TOKEN[:10] + "...")
    print("✅ Agents available: Agent_N (Intermarket), Agent_W (Consensus)")
    print("🎯 Bot is running. Press Ctrl+C to stop.")
    bot.infinity_polling()

if __name__ == '__main__':
    run_bot()
