#!/usr/bin/env python3
"""
Telegram Bot for Trading System
"""

import os
import time
import requests
from datetime import datetime
from typing import Dict, Optional
from dotenv import load_dotenv

load_dotenv()

class TelegramBot:
    """Telegram bot for sending trading signals and market updates"""
    
    # Confidence thresholds
    CONF_MIN = 0.40      # below this → no message sent
    CONF_STRONG = 0.85   # at/above → STRONG tier

    def __init__(self):
        self.token = os.environ.get('TELEGRAM_BOT_TOKEN', '').strip()
        self.chat_id = os.environ.get('TELEGRAM_CHAT_ID', '').strip()
        self.enabled = bool(self.token and self.chat_id)
        self.last_send: Dict[str, float] = {}
        self.signal_history = []
        self.alert_history = []

        print(f"\n📱 Telegram: {'ENABLED' if self.enabled else 'DISABLED'}")
        if self.enabled:
            print(f"   Token: {self.token[:10]}...")
            print(f"   Chat ID: {self.chat_id}")
            print(f"   Signal filter rules:")
            print(f"     confidence < {self.CONF_MIN*100:.0f}%             → ⏭️  NO SEND")
            print(f"     {self.CONF_MIN*100:.0f}% ≤ confidence < {self.CONF_STRONG*100:.0f}%  → 🟡 WEAK BUY / WEAK SELL")
            print(f"     {self.CONF_STRONG*100:.0f}% ≤ confidence ≤ 100%   → 💪 STRONG BUY / STRONG SELL")

    def should_send(self, asset: str) -> bool:
        """Rate limit: only send every 30 seconds per asset"""
        now = time.time()
        last = self.last_send.get(asset, 0)
        if now - last >= 30:
            self.last_send[asset] = now
            return True
        return False

    def get_signal_tier(self, signal: str, confidence: float):
        """Determine signal strength tier"""
        is_buy = 'BUY' in signal.upper()
        is_sell = 'SELL' in signal.upper()

        if not is_buy and not is_sell:
            return None, None

        if confidence < self.CONF_MIN:
            return None, None

        direction = 'BUY' if is_buy else 'SELL'

        if confidence < self.CONF_STRONG:
            label = f'WEAK {direction}'
            emoji = '🟡' if is_buy else '🟡'
        else:
            label = f'STRONG {direction}'
            emoji = '💪' if is_buy else '💪'

        return label, emoji

    def _get_asset_emoji(self, asset: str) -> str:
        """Get emoji for asset"""
        emojis = {
            'GOLD': '💰', 'XAU/USD': '💰',
            'SILVER': '🥈', 'XAG/USD': '🥈',
            'OIL': '🛢️', 'BCO/USD': '🛢️', 'WTICO/USD': '🛢️',
            'SP500': '📊', 'S&P500/USD': '📊',
            'NASDAQ': '📈', 'NAS100/USD': '📈',
            'EURUSD': '💶', 'EURUSD': '💶',
            'GBPUSD': '💷',
            'USDJPY': '💴',
            'BTC': '₿', 'BTC/USD': '₿'
        }
        return emojis.get(asset, '📊')

    def _format_price(self, asset: str, price: float) -> str:
        """Format price based on asset type"""
        if 'EUR' in asset or 'GBP' in asset:
            return f"{price:.5f}"
        elif 'JPY' in asset:
            return f"{price:.3f}"
        elif 'GOLD' in asset or 'SILVER' in asset or 'OIL' in asset:
            return f"${price:.2f}"
        else:
            return f"{price:,.2f}"

def format_message(self, asset: str, market_data: Dict, agent_results: Dict,
                   ensemble: Dict, tier_label: str, tier_emoji: str) -> str:
    """Format the Telegram message with complete trading data"""

    # Get market data
    price = market_data.get('price', 0)
    conf = ensemble.get('confidence', 0)
    status = market_data.get('status', 'LIVE')
    symbol = market_data.get('symbol', asset)
    volatility = market_data.get('volatility', 0.8)
    stoploss = market_data.get('stoploss', price * 0.98)
    takeprofit = market_data.get('takeprofit', price * 1.04)
    support = market_data.get('support', price * 0.99)
    resistance = market_data.get('resistance', price * 1.01)
    timeframe = market_data.get('timeframe', 15)

    asset_emoji = self._get_asset_emoji(asset)

    display_names = {
        'XAU/USD': 'GOLD', 'XAG/USD': 'SILVER',
        'BCO/USD': 'BRENT OIL', 'WTICO/USD': 'WTI OIL',
        'S&P500/USD': 'S&P 500',
        'EURUSD': 'EURUSD', 'GBPUSD': 'GBPUSD', 'USDJPY': 'USDJPY'
    }
    display_name = display_names.get(asset, asset)

    # Create confidence bar
    filled = int(conf * 10)
    conf_bar = '█' * filled + '░' * (10 - filled)

    # Signal strength note
    if conf < self.CONF_STRONG:
        tier_note = "⚠️ *WEAK SIGNAL* — trade smaller / use caution"
    else:
        tier_note = "💪 *STRONG SIGNAL* — high-confidence setup"

    # Format agent votes
    agent_lines = []
    for agent, res in list(agent_results.items())[:6]:
        vote = res.get('vote', 'HOLD')
        vote_conf = res.get('confidence', 50)
        vote_emoji = '🟢' if vote == 'BUY' else '🔴' if vote == 'SELL' else '⚪'
        agent_lines.append(f"{vote_emoji} {agent}: {vote} ({vote_conf:.0f}%)")

    formatted_agents = '\n'.join(agent_lines) if agent_lines else '   No votes available'

    # Price formatting
    if 'EUR' in asset or 'GBP' in asset:
        price_display = f"{price:.5f}"
        sl_display = f"{stoploss:.5f}"
        tp_display = f"{takeprofit:.5f}"
        sup_display = f"{support:.5f}"
        res_display = f"{resistance:.5f}"
    elif 'JPY' in asset:
        price_display = f"{price:.3f}"
        sl_display = f"{stoploss:.3f}"
        tp_display = f"{takeprofit:.3f}"
        sup_display = f"{support:.3f}"
        res_display = f"{resistance:.3f}"
    else:
        price_display = f"${price:.2f}"
        sl_display = f"${stoploss:.2f}"
        tp_display = f"${takeprofit:.2f}"
        sup_display = f"${support:.2f}"
        res_display = f"${resistance:.2f}"

    # Calculate risk/reward ratio
    risk_reward = "N/A"
    if stoploss > 0 and takeprofit > price:
        risk = price - stoploss
        reward = takeprofit - price
        if risk > 0:
            risk_reward = f"1:{reward/risk:.1f}"

    # Build complete message with MARKET DATA and RISK MANAGEMENT sections
    message = f"""
{'═' * 45}
{asset_emoji} *{display_name}* — *{tier_label}* {tier_emoji}
{'═' * 45}

📊 *MARKET DATA*
├ 💵 *Price:* {price_display} ({symbol})
├ 📈 *Confidence:* {conf*100:.0f}% {conf_bar}
├ 📡 *Source:* {status}
├ ⏱️ *Timeframe:* {timeframe} minutes
├ 📉 *Volatility:* {volatility:.2f}%
└ 🎯 *Risk/Reward:* {risk_reward}

{tier_note}

🛡️ *RISK MANAGEMENT*
├ 🛑 *Stop Loss:* {sl_display}
├ 🎯 *Take Profit:* {tp_display}
├ 🔼 *Resistance:* {res_display}
└ 🔽 *Support:* {sup_display}

🤖 *AGENT VOTES* ({len(agent_results)} agents)
{formatted_agents}

📈 *ENSEMBLE RESULTS*
├ 🟢 BUY:  {ensemble.get('buy_pct', 0):.0f}% ({ensemble.get('buy_count', 0)} votes)
├ 🔴 SELL: {ensemble.get('sell_pct', 0):.0f}% ({ensemble.get('sell_count', 0)} votes)
└ ⚪ HOLD: {ensemble.get('hold_pct', 0):.0f}% ({ensemble.get('hold_count', 0)} votes)

{'─' * 45}
⏰ {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
{'═' * 45}
"""
    return message
def send_test_message(self):
        """Send a test message to verify bot is working"""
        if not self.enabled:
            print("❌ Telegram bot not configured")
            return False
        
        message = """
✅ *Telegram Bot Test*

Your trading system bot is working correctly!

📊 *Status:*
- Bot Connected: ✅
- Chat ID Configured: ✅
- Ready to receive signals

📈 *Commands:*
- Send trading signals
- Receive market updates
- Get agent voting results

_This is an automated test message._
"""
        try:
            url = f"https://api.telegram.org/bot{self.token}/sendMessage"
            response = requests.post(url, json={
                'chat_id': self.chat_id,
                'text': message,
                'parse_mode': 'Markdown'
            }, timeout=10)
            
            if response.status_code == 200:
                print("✅ Test message sent! Check your Telegram.")
                return True
            else:
                print(f"❌ Failed: {response.status_code}")
                return False
        except Exception as e:
            print(f"❌ Error: {e}")
            return False


# Create a global instance
telegram_bot = TelegramBot()

# Test if configured
if telegram_bot.enabled:
    print("✅ Telegram bot ready!")
else:
    print("⚠️ Telegram bot not configured. Set TELEGRAM_BOT_TOKEN and TELEGRAM_CHAT_ID in .env")
