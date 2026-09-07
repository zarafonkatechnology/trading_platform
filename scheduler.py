#!/usr/bin/env python3
"""
Complete Trading System - Runs Every 2 Minutes
Integrates: OANDA API, Database, Strategy Framework, Telegram Bot
"""

import sqlite3
import re
import json
import time
from unittest.mock import sentinel
import schedule
import logging
import threading
import os
import requests
from datetime import datetime
from typing import Dict, Optional, List
from dataclasses import dataclass
from enum import Enum
from dotenv import load_dotenv
from backend.core import supervisor
from supervisor_simple import SimpleSupervisor
from mt4_price_provider import get_mt4_prices
from gatekeeper_agent import GatekeeperCore, GatekeeperIntegration
from telegram_bot import TelegramBot  # Assuming it's in telegram_bot.py
# Initialize
gatekeeper = GatekeeperCore()
gatekeeper_integration = GatekeeperIntegration(gatekeeper, sentinel, supervisor)

telegram_bot = TelegramBot()




load_dotenv()

# ============================================
# OANDA PRICE FETCHING
# ============================================

def get_mt4_prices_data():
     mt4 = get_mt4_prices()
    if mt4.test_connection():
        return True
    else:
        print("⚠️ MT4 not connected, using simulated prices")
        return False

    # Assets to track
    instruments = [
        'GOLD', 'SILVER', 'BRENT_OIL', 'CrudeOIL',
        'S&P500', 'NASDAQ100', 'EURUSD', 'GBPUSD', 'USD_JPY'
    ]
    
    try:
        # url = f"https://api-fxpractice.oanda.com/v3/accounts/{OANDA_ACCOUNT_ID}/pricing"
        headers = {'Authorization': f'Bearer {OANDA_API_KEY}'}
        params = {'instruments': ','.join(instruments)}
        
        response = requests.get(url, headers=headers, params=params, timeout=10)
        
        if response.status_code == 200:
            data = response.json()
            prices = {}
            
            for price_data in data.get('prices', []):
                instrument = price_data['instrument']
                bids = price_data.get('bids', [])
                asks = price_data.get('asks', [])
                
                if bids and asks:
                    bid = float(bids[0]['price'])
                    ask = float(asks[0]['price'])
                    mid = (bid + ask) / 2
                    
                    # Convert instrument name to display format
                    display_name = instrument.replace('_', '/')
                    prices[display_name] = round(mid, 2) if mid > 10 else round(mid, 4)
                else:
                    prices[instrument.replace('_', '/')] = 0
            
            print(f"✅ Fetched {len(prices)} live prices from MT4")
            return prices
        else:
            print(f"⚠️ MT4 connection error: {e}, using simulated prices")

            return get_simulated_prices()
            
    except Exception as e:
        print(f"⚠️ MT4 connection error: {e}, using simulated prices")

        return get_simulated_prices()

def get_simulated_prices():
    """Fallback simulated prices when MT4 is not available"""
    print("📊 Using simulated prices (MT4 not connected)")
    return {
        'XAU/USD': 2385.50,
        'XAG/USD': 28.45,
        'BCO/USD': 89.75,
        'WTICO/USD': 85.30,
        'S&P500/USD': 5200.50,
        'NAS100/USD': 18250.30,
        'EURUSD': 1.0725,
        'GBPUSD': 1.2530,
        'USDJPY': 154.80,
    }

# ============================================
# TELEGRAM BOT - YOUR COMPLETE WORKING VERSION
# ============================================
prices = get_mt4_prices_data()
print("📡 Source: MT4 Real-Time API")
class TelegramBot:
    CONF_MIN = 0.75   # below this → no message sent
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
            print(f"   Signal filter rules:")
            print(f"     confidence < {self.CONF_MIN*100:.0f}%             → ⏭️  NO SEND")
            print(f"     {self.CONF_MIN*100:.0f}% ≤ confidence < {self.CONF_STRONG*100:.0f}%  → 🟡 WEAK BUY / WEAK SELL")
            print(f"     {self.CONF_STRONG*100:.0f}% ≤ confidence ≤ 100%   → 💪 STRONG BUY / STRONG SELL")

    def should_send(self, asset: str) -> bool:
        now = time.time()
        last = self.last_send.get(asset, 0)
        if now - last >= 30:
            self.last_send[asset] = now
            return True
        return False

    def get_signal_tier(self, signal: str, confidence: float):
        is_buy = 'BUY' in signal
        is_sell = 'SELL' in signal

        if not is_buy and not is_sell:
            return None, None

        if confidence < self.CONF_MIN:
            return None, None

        direction = 'BUY' if is_buy else 'SELL'

        if confidence < self.CONF_STRONG:
            label = f'WEAK {direction}'
            emoji = '🟡🚀' if is_buy else '🟡🔴'
        else:
            label = f'STRONG {direction}'
            emoji = '🚀🚀' if is_buy else '🔴🔴'

        return label, emoji

    def _get_asset_emoji(self, asset: str) -> str:
        emojis = {
            'OIL': '🛢️',
            'GOLD': '💰',
            'SILVER': '🥈',
            'BCO/USD': '🛢️',
            'WTICO/USD': '🛢️',
            'EURUSD': '💶',
            'GBPUSD': '💷',
            'USD_JPY': '🇺🇸🇯🇵',
            'S&P500/USD': '📈',
            'NAS100': '📈',
            'US500': '🇺🇸',
            'SUI20': '🇨🇭'
        }
        return emojis.get(asset, '📊')

    def _format_price(self, asset: str, price: float) -> str:
        if 'EUR' in asset or 'GBP' in asset:
            return f"{price:.5f}"
        elif 'JPY' in asset:
            return f"{price:.3f}"
        elif 'GOLD' in asset or 'SILVER' in asset or 'OIL' in asset:
            return f"${price:.2f}"
        else:
            return f"{price:,.2f}"

    def format_message(self, asset: str, market_data: Dict, agent_results: Dict,
                       ensemble: Dict, scalping_results: Dict, tier_label: str, tier_emoji: str) -> str:

        price = market_data['price']
        conf = ensemble['confidence']
        status = market_data['status']
        symbol = market_data['symbol']

        asset_emoji = self._get_asset_emoji(asset)
        
        # Display name mapping
        display_names = {
            'GOLD': 'GOLD',
            'SILVER': 'SILVER',
            'BRENT_OIL': 'BRENT_OIL',
            'CrudeOIL': 'CrudeOIL',
            '#S&P500': '#S&P500',
            '#EURUSD': 'EURUSD',
            '#GBPUSD': 'GBPUSD',
            '#USDJPY': 'USDJPY'
        }
        display_name = display_names.get(asset, asset)

        filled = int(conf * 10)
        conf_bar = '█' * filled + '░' * (10 - filled)

        if conf < self.CONF_STRONG:
            tier_note = "⚠️ *WEAK SIGNAL* — trade smaller / use caution"
        else:
            tier_note = "💪 *STRONG SIGNAL* — high-confidence setup"

        # Agent results
        agent_lines = []
        for agent, res in list(agent_results.items())[:6]:
            agent_lines.append(f"{agent[:10]}={res['vote']}({res['confidence']:.0f}%)")
        
        formatted_agents = []
        for i in range(0, len(agent_lines), 2):
            if i+1 < len(agent_lines):
                formatted_agents.append(f"   {agent_lines[i]} | {agent_lines[i+1]}")
            else:
                formatted_agents.append(f"   {agent_lines[i]}")

        price_display = self._format_price(asset, price)
        if price_display and not price_display.startswith('$') and 'EUR' not in asset and 'GBP' not in asset:
            if 'GOLD' in asset or 'SILVER' in asset or 'OIL' in asset:
                price_display = f"${price_display}"

        message = f"""
{asset_emoji} *{display_name}* — *{tier_label}* {tier_emoji}

💵 *Price:* {price_display} ({symbol})
📊 *Confidence:* {conf*100:.0f}% {conf_bar}
📡 *Data Source:* {status}

{tier_note}

🤖 *Agent Votes:*
{chr(10).join(formatted_agents)}

📈 *Ensemble:* 🟢BUY:{ensemble['buy_pct']:.0f}% 🔴SELL:{ensemble['sell_pct']:.0f}% ⚪HOLD:{ensemble['hold_pct']:.0f}%
⏰ *Time:* {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
"""
        return message

    def send(self, asset: str, market_data: Dict, agent_results: Dict,
             ensemble: Dict, scalping_results: Dict = None) -> bool:

        if not self.enabled:
            return False

        if not self.should_send(asset):
            return False

        signal = ensemble['signal']
        confidence = ensemble['confidence']

        tier_label, tier_emoji = self.get_signal_tier(signal, confidence)

        if tier_label is None:
            if 'BUY' not in signal and 'SELL' not in signal:
                reason = "signal=HOLD"
            else:
                reason = f"conf={confidence*100:.0f}% < {self.CONF_MIN*100:.0f}%"
            print(f"   ⏭️  {asset}: No Telegram sent ({reason})")
            return False

        message = self.format_message(asset, market_data, agent_results,
                                      ensemble, scalping_results or {},
                                      tier_label, tier_emoji)
        try:
            url = f"https://api.telegram.org/bot{self.token}/sendMessage"
            r = requests.post(url, json={
                'chat_id': self.chat_id,
                'text': message,
                'parse_mode': 'Markdown',
                'disable_web_page_preview': True
            }, timeout=10)

            if r.status_code == 200:
                print(f"   ✅ Telegram SENT: {asset} [{tier_label}] conf={confidence*100:.0f}%")
                self.alert_history.append({'timestamp': datetime.now(), 'asset': asset, 'signal': tier_label})
                return True
            else:
                print(f"   ❌ Telegram error {r.status_code} for {asset}: {r.text[:80]}")
                return False
        except Exception as e:
            print(f"   ❌ Telegram failed for {asset}: {e}")
            return False

    def send_summary(self, prices: Dict):
        if not self.enabled:
            return

        message = "📊 *MARKET SNAPSHOT*\n\n"
        for asset, data in prices.items():
            price = data.get('price', 0)
            price_display = self._format_price(asset, price)
            emoji = self._get_asset_emoji(asset)
            message += f"{emoji} {asset}: {price_display}\n"
        
        try:
            url = f"https://api.telegram.org/bot{self.token}/sendMessage"
            requests.post(url, json={'chat_id': self.chat_id, 'text': message, 'parse_mode': 'Markdown'}, timeout=10)
        except:
            pass
def save_signal_to_db(asset, price, confidence, signal_strength, decision, votes):
    """Save trading signal to database for Platform 2"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    # Insert into signals table
    cursor.execute('''
        INSERT INTO signals (
            asset_type, current_price, confidence_percent, signal_strength,
            data_source, analysis_volatility, stoploss, takeprofit,
            support_level, resistance_level, timeframe_minutes,
            signal_timestamp, status
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    ''', (
        asset, price, confidence * 100, signal_strength,
        'MT4_LIVE', 0.5, price * 0.98, price * 1.04,
        price * 0.99, price * 1.01, 15,
        datetime.now().isoformat(), 'PROCESSED'
    ))
    
    signal_id = cursor.lastrowid
    
    # Insert agent votes
    for agent_name, vote_data in votes.items():
        cursor.execute('''
            INSERT INTO agent_votes (signal_id, agent_name, vote, confidence)
            VALUES (?, ?, ?, ?)
        ''', (signal_id, agent_name, vote_data['vote'], vote_data['confidence']))
    
    # Insert group votes
    buy = sum(1 for v in votes.values() if v['vote'] == 'BUY')
    sell = sum(1 for v in votes.values() if v['vote'] == 'SELL')
    hold = sum(1 for v in votes.values() if v['vote'] == 'HOLD')
    total = len(votes)
    
    cursor.execute('''
        INSERT INTO group_votes (
            signal_id, buy_votes, sell_votes, hold_votes,
            buy_percent, sell_percent, hold_percent,
            final_decision, decision_confidence
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
    ''', (
        signal_id, buy, sell, hold,
        (buy/total*100) if total > 0 else 0,
        (sell/total*100) if total > 0 else 0,
        (hold/total*100) if total > 0 else 0,
        decision, confidence
    ))
    
    conn.commit()
    conn.close()
    print(f"   💾 Saved signal #{signal_id} to database")

# ============================================
# OANDA REAL-TIME API
# ============================================

class OandaRealTime:
    def __init__(self):
        # self.api_key = os.getenv('OANDA_API_KEY')
        # self.account_id = os.getenv('OANDA_ACCOUNT_ID')
        # self.base_url = 'https://api-fxpractice.oanda.com'
        self.headers = {
            'Authorization': f'Bearer {self.api_key}',
            'Content-Type': 'application/json'
        }
        self.connected = False
        
    def test_connection(self):
        if not self.api_key or not self.account_id:
            print("⚠️ MT4 not connected - check EA is running")
            return False
        
        try:
            url = f"{self.base_url}/v3/accounts/{self.account_id}/summary"
            response = requests.get(url, headers=self.headers, timeout=10)
            if response.status_code == 200:
                self.connected = True
                return True
            else:
                print("✅ MT4 connected - Real-time data available")
                return False
        except Exception as e:
            print(f"⚠️ MT4 connection failed: {e}")
            return False
    
    def get_live_price(self, instrument: str) -> Optional[float]:
        if not self.connected:
            return None
        
        try:
            url = f"{self.base_url}/v3/accounts/{self.account_id}/pricing"
            params = {'instruments': instrument}
            response = requests.get(url, headers=self.headers, params=params, timeout=10)
            
            if response.status_code == 200:
                data = response.json()
                for price_data in data.get('prices', []):
                    bids = price_data.get('bids', [])
                    asks = price_data.get('asks', [])
                    if bids and asks:
                        bid = float(bids[0].get('price', 0))
                        ask = float(asks[0].get('price', 0))
                        return (bid + ask) / 2
            return None
        except Exception as e:
            print(f"Error fetching {instrument}: {e}")
            return None
    
    def get_all_prices(self) -> Dict:
        instruments = [
            'GOLD',    # Gold
            'SILVER',    # Silver
            'BRENT_OIL',    # Brent Oil
            'S&P500', # S&P 500
            'EURUSD',    # Euro
            'GBPUSD',    # British Pound
        ]
        
        prices = {}
        for instrument in instruments:
            price = self.get_live_price(instrument)
            if price:
                display_name = instrument.replace('_', '/')
                prices[display_name] = price
        
        return prices


# ============================================
# DATABASE SETUP
# ============================================

DB_PATH = 'trading_system.db'

def init_database():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS signals (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            asset_type TEXT,
            current_price REAL,
            confidence_percent REAL,
            signal_strength TEXT,
            data_source TEXT,
            analysis_volatility REAL,
            stoploss REAL,
            takeprofit REAL,
            support_level REAL,
            resistance_level REAL,
            timeframe_minutes INTEGER,
            signal_timestamp TIMESTAMP,
            status TEXT DEFAULT 'PENDING',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS agent_votes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            signal_id INTEGER,
            agent_name TEXT,
            vote TEXT,
            confidence REAL,
            timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS group_votes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            signal_id INTEGER,
            buy_votes INTEGER,
            sell_votes INTEGER,
            hold_votes INTEGER,
            buy_percent REAL,
            sell_percent REAL,
            hold_percent REAL,
            final_decision TEXT,
            decision_confidence REAL,
            timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    conn.commit()
    conn.close()
    print("✅ Database initialized")


# ============================================
# TRADING AGENT
# ============================================

class TradingAgent:
    def __init__(self, name: str, agent_type: str):
        self.name = name
        self.type = agent_type
        self.xp = 0
        self.tokens = 1000
        self.accuracy = 0
        self.total_votes = 0
        self.correct_votes = 0
    
    def vote(self, signal: Dict) -> Dict:
        import random
        
        confidence = signal.get('confidence_percent', 70) / 100
        
        if self.type == 'trend':
            if confidence > 0.75:
                vote = 'BUY'
                conf = 75 + random.randint(0, 15)
            elif confidence < 0.50:
                vote = 'SELL'
                conf = 60 + random.randint(0, 10)
            else:
                vote = 'HOLD'
                conf = 50
        elif self.type == 'reversion':
            if confidence > 0.80:
                vote = 'SELL'
                conf = 70 + random.randint(0, 15)
            elif confidence < 0.60:
                vote = 'BUY'
                conf = 65 + random.randint(0, 10)
            else:
                vote = 'HOLD'
                conf = 50
        elif self.type == 'momentum':
            if confidence > 0.70:
                vote = 'BUY'
                conf = 65 + random.randint(0, 20)
            else:
                vote = 'HOLD'
                conf = 55
        else:
            vote = random.choice(['BUY', 'SELL', 'HOLD'])
            conf = 50 + random.randint(0, 30)
        
        self.total_votes += 1
        return {'vote': vote, 'confidence': conf}


class SignalProcessor:
    def __init__(self):
        self.agents = [
            TradingAgent('Technical', 'trend'),
            TradingAgent('Momentum', 'momentum'),
            TradingAgent('Reversion', 'reversion'),
            TradingAgent('Volume', 'volume'),
            TradingAgent('Sentiment', 'sentiment')
        ]
    
    def process_signal(self, signal_data: Dict) -> Dict:
        votes = {}
        for agent in self.agents:
            votes[agent.name] = agent.vote(signal_data)
        
        buy = sum(1 for v in votes.values() if v['vote'] == 'BUY')
        sell = sum(1 for v in votes.values() if v['vote'] == 'SELL')
        hold = sum(1 for v in votes.values() if v['vote'] == 'HOLD')
        total = len(votes)
        
        buy_pct = round(buy / total * 100, 1)
        sell_pct = round(sell / total * 100, 1)
        hold_pct = round(hold / total * 100, 1)
        
        weighted_buy = sum(v['confidence'] for v in votes.values() if v['vote'] == 'BUY')
        weighted_sell = sum(v['confidence'] for v in votes.values() if v['vote'] == 'SELL')
        
        if weighted_buy > weighted_sell and buy >= 2:
            decision = 'BUY'
            confidence = min(weighted_buy / total / 100, 0.95)
        elif weighted_sell > weighted_buy and sell >= 2:
            decision = 'SELL'
            confidence = min(weighted_sell / total / 100, 0.95)
        else:
            decision = 'HOLD'
            confidence = hold_pct / 100
        
        return {
            'signal': signal_data,
            'votes': votes,
            'decision': decision,
            'confidence': confidence,
            'buy_pct': buy_pct,
            'sell_pct': sell_pct,
            'hold_pct': hold_pct,
            'buy_count': buy,
            'sell_count': sell,
            'hold_count': hold
        }


# ============================================
# MAIN TRADING CYCLE
# ============================================p
def run_trading_cycle():
    """Execute one complete trading cycle"""
    
    print(f"\n{'='*60}")
    print(f"📊 TRADING CYCLE STARTED at {datetime.now()}")
    print(f"{'='*60}")
    
    # Get prices
    prices = get_mt4_prices_data()
    
    if not prices:
        print("❌ No prices available")
        return
    
    print(f"\n💰 Current Prices:")
    for asset, price in prices.items():
        print(f"   {asset}: ${price:.2f}" if price > 10 else f"   {asset}: {price:.4f}")
    
    # Initialize Telegram bot
    telegram_bot = TelegramBot()
    
    # Process each asset
    results = []
    
    for asset, price in prices.items():
        print(f"\n{'─'*40}")
        print(f"📊 Analyzing {asset}")
        print(f"{'─'*40}")
        
        # Simulate agent votes (replace with your actual agent voting)
        # This is where you would call your actual agent manager
        votes = simulate_agent_votes(asset, price)
        
        # Calculate vote distribution
        buy = sum(1 for v in votes.values() if v['vote'] == 'BUY')
        sell = sum(1 for v in votes.values() if v['vote'] == 'SELL')
        hold = sum(1 for v in votes.values() if v['vote'] == 'HOLD')
        total = len(votes)
        
        buy_pct = (buy / total * 100) if total > 0 else 0
        sell_pct = (sell / total * 100) if total > 0 else 0
        hold_pct = (hold / total * 100) if total > 0 else 0
        
        # Determine decision
        if buy > sell and buy > hold:
            decision = 'BUY'
            confidence = buy_pct / 100
        elif sell > buy and sell > hold:
            decision = 'SELL'
            confidence = sell_pct / 100
        else:
            decision = 'HOLD'
            confidence = hold_pct / 100
        
        print(f"   Votes: BUY={buy}, SELL={sell}, HOLD={hold}")
        print(f"   Decision: {decision} ({confidence*100:.1f}%)")
        
        # Send to Telegram if confidence is high enough
        if confidence >= 0.75:  # 75% confidence threshold
            market_data = {
            'price': price,
            'symbol': asset,
            'status': 'LIVE',
            'volatility': calculate_volatility(asset),  # Add this function
            'stoploss': price * 0.98,  # 2% stop loss
            'takeprofit': price * 1.04,  # 4% take profit
            'support': price * 0.99,  # 1% support
            'resistance': price * 1.01,  # 1% resistance
            'timeframe': 15  # minutes
}
            
            ensemble = {
             'signal': decision,
             'confidence': confidence,
             'buy_pct': buy_pct,
             'sell_pct': sell_pct,
             'hold_pct': hold_pct,
             'buy_count': buy,
             'sell_count': sell,
             'hold_count': hold
}
            
            telegram_bot.send(asset, market_data, votes, ensemble)
        
        results.append({
            'asset': asset,
            'decision': decision,
            'confidence': confidence,
            'buy': buy, 'sell': sell, 'hold': hold
        })
    
    # Send summary
    send_trading_summary(results, telegram_bot)
    
    print(f"\n{'='*60}")
    print(f"✅ CYCLE COMPLETED at {datetime.now()}")
    print(f"{'='*60}\n")
def calculate_volatility(asset):
    """Calculate volatility for asset"""
    # You can implement actual volatility calculation
    # For now, return a reasonable value
    volatility_map = {
        'GOLD': 0.8,
        'SILVER': 1.2,
        'BRENTOI': 1.5,
        'S&P500/USD': 0.6,
        'EURUSD': 0.4,
        'GBPUSD': 0.5,
        'USDJPY': 0.5
    }
    return volatility_map.get(asset, 0.8)
def simulate_agent_votes(asset, price):
    """Simulate agent votes (replace with your actual agent manager)"""
    import random
    
    # This is a placeholder - replace with your actual agent voting logic
    agents = ['Agent_A', 'Agent_B', 'Agent_C', 'Agent_D', 'Agent_E', 'Agent_F']
    votes = {}
    
    for agent in agents:
        # Simulate different voting patterns based on agent type
        if agent == 'Agent_A':  # Trend Follower
            vote = 'BUY' if random.random() > 0.4 else 'SELL'
            conf = random.randint(65, 90)
        elif agent == 'Agent_B':  # Mean Reversion
            vote = 'SELL' if random.random() > 0.5 else 'BUY'
            conf = random.randint(60, 85)
        elif agent == 'Agent_C':  # Momentum
            vote = 'BUY' if random.random() > 0.45 else 'HOLD'
            conf = random.randint(70, 95)
        else:
            vote = random.choice(['BUY', 'SELL', 'HOLD'])
            conf = random.randint(50, 80)
        
        votes[agent] = {'vote': vote, 'confidence': conf}
    
    return votes

def send_trading_summary(results, telegram_bot):
    """Send trading summary to Telegram"""
    if not results:
        return
    
    buy_count = sum(1 for r in results if r['decision'] == 'BUY')
    sell_count = sum(1 for r in results if r['decision'] == 'SELL')
    hold_count = sum(1 for r in results if r['decision'] == 'HOLD')
    
    summary = f"""
📊 *TRADING CYCLE SUMMARY*
⏱️ {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
{'─' * 30}

📈 *Decisions:*
🟢 BUY:  {buy_count}
🔴 SELL: {sell_count}
⚪ HOLD: {hold_count}

📋 *Details:*
"""
    for r in results[:5]:
        emoji = '🟢' if r['decision'] == 'BUY' else '🔴' if r['decision'] == 'SELL' else '⚪'
        summary += f"{emoji} {r['asset']}: {r['decision']} ({r['confidence']*100:.0f}%)\n"
    
    summary += f"\n{'─' * 30}\n"
    summary += f"_Next cycle in 2 minutes_"
    
    telegram_bot.send_message(summary)

# Add send_message method to TelegramBot if not exists
def send_message(self, text):
    """Send plain text message to Telegram"""
    if not self.enabled:
        return False
    
    try:
        url = f"https://api.telegram.org/bot{self.token}/sendMessage"
        response = requests.post(url, json={
            'chat_id': self.chat_id,
            'text': text,
            'parse_mode': 'Markdown'
        }, timeout=10)
        return response.status_code == 200
    except Exception as e:
        print(f"Error sending message: {e}")
        return False

# Add the method to TelegramBot class if it doesn't exist
TelegramBot.send_message = send_message
# ============================================
# SCHEDULER
# ============================================

def main():
    logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(message)s')
    
    print("\n" + "=" * 60)
    print("🚀 TRADING SYSTEM STARTING")
    print("=" * 60)
    print("📡 Source: MT4 Real-Time API")
    print("⏱️  Interval: Every 2 minutes")
    print("📱 Telegram: Enabled")
    print("=" * 60 + "\n")
    
    
    # Run once immediately
    run_trading_cycle()
    
    # Schedule every 2 minutes
    schedule.every(2).minutes.do(run_trading_cycle)
    
    try:
        while True:
            schedule.run_pending()
            time.sleep(20)
    except KeyboardInterrupt:
        print("\n🛑 Scheduler stopped by user")

if __name__ == '__main__':
    main()
