
"""
COMPLETE TELEGRAM TRADE SIGNAL
Sends full trading details including:
- Timeframe
- Stop Loss
- Take Profit
- Support/Resistance levels
- Volatility
- Agent consensus
"""

import os
import requests
import json
from datetime import datetime
from typing import Dict, List, Optional

class TelegramTradeSignal:
    """Send complete trade signals with all details to Telegram"""
    
    def __init__(self):
        self.token = os.environ.get('TELEGRAM_BOT_TOKEN')
        self.chat_id = os.environ.get('TELEGRAM_CHAT_ID')
        self.enabled = bool(self.token and self.chat_id)
        
        if self.enabled:
            print("✅ Telegram Trade Signal Ready")
    
    def calculate_volatility(self, asset: str, price: float) -> float:
        """Calculate volatility for the asset"""
        # In production, use real ATR calculation
        # For demo, use percentage based on asset type
        if 'OIL' in asset:
            return price * 0.02  # 2% for oil
        elif 'GOLD' in asset:
            return price * 0.01  # 1% for gold
        elif 'SILVER' in asset:
            return price * 0.015  # 1.5% for silver
        else:
            return price * 0.02  # Default 2%
    
    def calculate_support_resistance(self, price: float, asset: str) -> Dict:
        """Calculate support and resistance levels"""
        if 'OIL' in asset:
            return {
                'support_1': round(price * 0.98, 2),
                'support_2': round(price * 0.96, 2),
                'resistance_1': round(price * 1.02, 2),
                'resistance_2': round(price * 1.04, 2)
            }
        elif 'GOLD' in asset:
            return {
                'support_1': round(price * 0.99, 2),
                'support_2': round(price * 0.98, 2),
                'resistance_1': round(price * 1.01, 2),
                'resistance_2': round(price * 1.02, 2)
            }
        else:
            return {
                'support_1': round(price * 0.98, 2),
                'support_2': round(price * 0.97, 2),
                'resistance_1': round(price * 1.02, 2),
                'resistance_2': round(price * 1.03, 2)
            }
    
    def send_trade_signal(self, 
                          signal: str, 
                          confidence: float, 
                          price: float, 
                          asset: str = "OIL",
                          timeframe: int = 15,
                          agent_signals: Dict = None,
                          consensus_score: float = None,
                          additional_data: Dict = None):
        """
        Send complete trade signal to Telegram
        
        Args:
            signal: 'BUY', 'SELL', 'STRONG_BUY', 'STRONG_SELL', 'HOLD'
            confidence: 0-1 confidence score
            price: Current price
            asset: Asset name (OIL, GOLD, SILVER, S&P500)
            timeframe: Trading timeframe in minutes (5, 15, 30, 60)
            agent_signals: Dictionary of individual agent signals
            consensus_score: Overall consensus score
            additional_data: Extra market data
        """
        
        if not self.enabled:
            print("⚠️ Telegram not configured. Set TELEGRAM_BOT_TOKEN and TELEGRAM_CHAT_ID")
            return False
        
        # Calculate trading levels
        volatility = self.calculate_volatility(asset, price)
        sr_levels = self.calculate_support_resistance(price, asset)
        
        # Calculate stop loss and take profit based on signal direction
        if signal in ['BUY', 'STRONG_BUY']:
            stop_loss = round(price - volatility * 1.5, 2)
            take_profit_1 = round(price + volatility * 1.5, 2)
            take_profit_2 = round(price + volatility * 3.0, 2)
            risk_amount = round(price - stop_loss, 2)
            reward_amount = round(take_profit_1 - price, 2)
        elif signal in ['SELL', 'STRONG_SELL']:
            stop_loss = round(price + volatility * 1.5, 2)
            take_profit_1 = round(price - volatility * 1.5, 2)
            take_profit_2 = round(price - volatility * 3.0, 2)
            risk_amount = round(stop_loss - price, 2)
            reward_amount = round(price - take_profit_1, 2)
        else:
            # HOLD signal - no trade execution
            message = self.format_hold_signal(asset, price, confidence, signal)
            return self._send_message(message)
        
        # Calculate risk/reward ratio
        if risk_amount > 0:
            risk_reward = round(reward_amount / risk_amount, 1)
        else:
            risk_reward = 0
        
        # Get agent summary
        agent_summary = self._format_agent_summary(agent_signals)
        
        # Get time
        current_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        
        # Format the complete message
        message = f"""
{'='*50}
🚨 *TRADE SIGNAL - {asset}* 🚨
{'='*50}

📊 *SIGNAL:* {signal}
🎯 *CONFIDENCE:* {confidence*100:.0f}%
💰 *PRICE:* ${price:.2f}
⏰ *TIMEFRAME:* {timeframe} minutes
📅 *TIME:* {current_time}

{'='*50}
📈 *TRADE DETAILS*
{'='*50}
"""
        
        if signal in ['BUY', 'STRONG_BUY']:
            message += f"""
🔵 *ACTION:* BUY {asset}
📊 *POSITION SIZE:* {self._calculate_position_size(confidence)}% of account

🛑 *STOP LOSS:* ${stop_loss:.2f} (Risk: ${risk_amount:.2f})
🎯 *TAKE PROFIT 1:* ${take_profit_1:.2f} (Reward: ${reward_amount:.2f})
🎯 *TAKE PROFIT 2:* ${take_profit_2:.2f}
📈 *RISK/REWARD:* 1:{risk_reward}

🟢 *SUPPORT LEVELS:*
   • S1: ${sr_levels['support_1']:.2f}
   • S2: ${sr_levels['support_2']:.2f}
"""
        elif signal in ['SELL', 'STRONG_SELL']:
            message += f"""
🔴 *ACTION:* SELL {asset}
📊 *POSITION SIZE:* {self._calculate_position_size(confidence)}% of account

🛑 *STOP LOSS:* ${stop_loss:.2f} (Risk: ${risk_amount:.2f})
🎯 *TAKE PROFIT 1:* ${take_profit_1:.2f} (Reward: ${reward_amount:.2f})
🎯 *TAKE PROFIT 2:* ${take_profit_2:.2f}
📉 *RISK/REWARD:* 1:{risk_reward}

🔴 *RESISTANCE LEVELS:*
   • R1: ${sr_levels['resistance_1']:.2f}
   • R2: ${sr_levels['resistance_2']:.2f}
"""
        
        message += f"""
{'='*50}
🤖 *AGENT CONSENSUS*
{'='*50}
{agent_summary}

{'='*50}
📊 *MARKET CONDITIONS*
{'='*50}
• Volatility: {volatility/price*100:.1f}%
• Spread: {self._calculate_spread(asset)} pips
• Session: {self._get_session()}

{'='*50}
⚠️ *RISK MANAGEMENT*
{'='*50}
• Max Risk: 2% per trade
• Daily Loss Limit: 5%
• Use Trailing Stop: YES

{'='*50}
💡 *NEXT STEPS*
{'='*50}
1. Enter {'LONG' if 'BUY' in signal else 'SHORT'} at market
2. Set stop loss at ${stop_loss:.2f}
3. Take partial profits at TP1
4. Trail stop to breakeven after +{reward_amount:.2f}
5. Let runners go to TP2

*Sentinel Auditor - 69-Agent Trading System*
"""
        
        return self._send_message(message)
    
    def _calculate_position_size(self, confidence: float) -> int:
        """Calculate position size based on confidence"""
        if confidence > 0.85:
            return 100  # Full position
        elif confidence > 0.75:
            return 75   # 3/4 position
        elif confidence > 0.65:
            return 50   # Half position
        else:
            return 25   # Quarter position
    
    def _calculate_spread(self, asset: str) -> float:
        """Calculate typical spread for asset"""
        spreads = {
            'OIL': 3,
            'GOLD': 2,
            'SILVER': 2.5,
            'S&P500': 1.5
        }
        return spreads.get(asset, 2)
    
    def _get_session(self) -> str:
        """Get current trading session"""
        hour = datetime.now().hour
        if 9 <= hour < 17:
            return "US Session (Active)"
        elif 1 <= hour < 9:
            return "Asian Session"
        elif 17 <= hour < 1:
            return "European Session"
        return "Off Hours"
    
    def _format_agent_summary(self, agent_signals: Dict) -> str:
        """Format agent signals summary"""
        if not agent_signals:
            return "• No agent data available"
        
        # Count signals by type
        buy_count = sum(1 for s in agent_signals.values() if s in ['BUY', 'STRONG_BUY'])
        sell_count = sum(1 for s in agent_signals.values() if s in ['SELL', 'STRONG_SELL'])
        hold_count = len(agent_signals) - buy_count - sell_count
        
        # Get top 5 agents by confidence
        top_agents = []
        if hasattr(agent_signals, 'items'):
            sorted_agents = sorted(agent_signals.items(), key=lambda x: x[1] if isinstance(x[1], (int, float)) else 0, reverse=True)[:5]
            for agent, sig in sorted_agents:
                top_agents.append(f"   • {agent}: {sig}")
        
        summary = f"""
📊 *VOTE BREAKDOWN:*
   🟢 BUY: {buy_count} agents
   🔴 SELL: {sell_count} agents
   🟡 HOLD: {hold_count} agents

🏆 *TOP AGENTS:*
{chr(10).join(top_agents) if top_agents else '   • No data'}
"""
        return summary
    
    def format_hold_signal(self, asset: str, price: float, confidence: float, signal: str) -> str:
        """Format HOLD signal message"""
        current_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        
        return f"""
{'='*50}
⏸️ *HOLD SIGNAL - {asset}* ⏸️
{'='*50}

📊 *SIGNAL:* {signal}
🎯 *CONFIDENCE:* {confidence*100:.0f}%
💰 *PRICE:* ${price:.2f}
⏰ *TIME:* {current_time}

{'='*50}
💡 *RECOMMENDATION*
{'='*50}
• No action required
• Wait for clearer signal
• Continue monitoring

*Sentinel Auditor - 69-Agent Trading System*
"""
    
    def _send_message(self, message: str) -> bool:
        """Send message to Telegram"""
        if not self.enabled:
            print("📱 Telegram would send:")
            print(message)
            return False
        
        try:
            url = f"https://api.telegram.org/bot{self.token}/sendMessage"
            payload = {
                'chat_id': self.chat_id,
                'text': message,
                'parse_mode': 'Markdown'
            }
            response = requests.post(url, json=payload, timeout=10)
            
            if response.status_code == 200:
                print("✅ Trade signal sent to Telegram")
                return True
            else:
                print(f"❌ Telegram error: {response.status_code}")
                return False
                
        except Exception as e:
            print(f"❌ Telegram error: {e}")
            return False

# ============================================================================
# EXAMPLE USAGE
# ============================================================================

def example_usage():
    """Example of sending a complete trade signal"""
    
    telegram = TelegramTradeSignal()
    
    # Example 1: BUY signal with full details
    telegram.send_trade_signal(
        signal="STRONG_BUY",
        confidence=0.85,
        price=85.50,
        asset="OIL",
        timeframe=15,
        agent_signals={
            'TechnicalMaster': 'BUY',
            'Whale': 'BUY',
            'SupportResistance': 'BUY',
            'RiskMaster': 'HOLD',
            'Sentiment': 'BUY'
        },
        consensus_score=0.82
    )
    
    # Example 2: SELL signal
    telegram.send_trade_signal(
        signal="SELL",
        confidence=0.78,
        price=1950.00,
        asset="GOLD",
        timeframe=5,
        agent_signals={
            'TechnicalMaster': 'SELL',
            'Whale': 'HOLD',
            'SupportResistance': 'SELL',
            'RiskMaster': 'SELL',
            'Sentiment': 'HOLD'
        }
    )

def send_real_signal(signal_data: Dict):
    """Function to call from your trading system"""
    telegram = TelegramTradeSignal()
    
    return telegram.send_trade_signal(
        signal=signal_data.get('signal', 'HOLD'),
        confidence=signal_data.get('confidence', 0.5),
        price=signal_data.get('price', 0),
        asset=signal_data.get('asset', 'OIL'),
        timeframe=signal_data.get('timeframe', 15),
        agent_signals=signal_data.get('agent_signals', {}),
        consensus_score=signal_data.get('consensus_score')
    )

if __name__ == "__main__":
    # Set your Telegram credentials
    # export TELEGRAM_BOT_TOKEN='your_token'
    # export TELEGRAM_CHAT_ID='your_chat_id'
    
    example_usage()
