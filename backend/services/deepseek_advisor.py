"""
DeepSeek Trading Advisor - Teaches agents how to make better voting decisions
"""

import os
import json
import requests
import logging
from datetime import datetime
from typing import Dict, List, Optional
from backend.services.market_data_fetcher import market_fetcher
logger = logging.getLogger(__name__)

class DeepSeekTradingAdvisor:
    """DeepSeek AI as a trading advisor for agents"""
    
    def __init__(self):
        self.api_key = os.getenv('DEEPSEEK_API_KEY')
        self.api_url = os.getenv('DEEPSEEK_API_URL', 'https://api.deepseek.com/v1/chat/completions')
        self.enabled = bool(self.api_key and self.api_key != 'your_deepseek_api_key_here')
        
        if self.enabled:
            print("✅ DeepSeek Trading Advisor ready - Agents can get voting advice")
        else:
            print("⚠️ DeepSeek Trading Advisor disabled - using rule-based advice")
    
    def analyze_vote_decision(self, agent_name: str, agent_type: str, 
                               signal_data: Dict, market_features: Dict,
                               agent_vote: str, agent_confidence: float) -> str:
        """
        DeepSeek analyzes whether an agent's vote is correct
        """
        if not self.enabled:
            return self._get_rule_based_advice(agent_name, agent_type, signal_data, agent_vote, agent_confidence)
        
        prompt = f"""
You are a senior trading advisor helping {agent_name}, a {agent_type} specialist.

Current Signal:
- Asset: {signal_data.get('asset_type', 'Unknown')}
- Price: ${signal_data.get('current_price', 0):.2f}
- Confidence: {signal_data.get('confidence_percent', 70)}%

Market Conditions:
- RSI: {market_features.get('rsi_14', 50):.1f}
- Volatility: {market_features.get('volatility', 0.5):.2f}%
- Trend Strength: {market_features.get('trend_strength', 50):.0f}%

Agent's Vote: {agent_vote}
Agent's Confidence: {agent_confidence:.0f}%

Analyze if this vote is correct. Provide:
1. Whether to BUY, SELL, or HOLD
2. Confidence level (0-100%)
3. Reasoning (2-3 sentences)
4. Specific advice for this agent

Keep response short and actionable.
"""
        
        response = self._call_deepseek(prompt)
        
        if response:
            return response
        else:
            return self._get_rule_based_advice(agent_name, agent_type, signal_data, agent_vote, agent_confidence)
    
    
    from backend.services.market_data_fetcher import market_fetcher

    def get_consensus_advice(self, votes: Dict, signal_data: Dict, market_features: Dict) -> str:
      """Get consensus advice with real-time market data"""
    
    # Get real-time prices
      realtime_prices = market_fetcher.get_current_prices()
      current_price = realtime_prices.get(signal_data.get('asset_type', 'XAU/USD'), signal_data.get('current_price', 2350))
    
    # Update signal data with real price
      signal_data['current_price'] = current_price
      signal_data['realtime'] = True
    
      return self._get_rule_based_consensus(votes, signal_data)
        # Add DeepSeek API call for consensus if needed
      return self._get_rule_based_consensus(votes, signal_data)
    
    def teach_voting_strategy(self, agent_name: str, agent_type: str, 
                               past_votes: List[Dict], performance: Dict) -> str:
        """
        DeepSeek teaches an agent how to improve voting based on past performance
        """
        if not self.enabled:
            return self._get_default_voting_lesson(agent_name, agent_type)
        
        # Summarize past performance
        recent_votes = past_votes[-10:] if len(past_votes) > 10 else past_votes
        vote_summary = []
        for v in recent_votes:
            vote_summary.append(f"{v.get('vote', '?')} - {'✅' if v.get('was_correct', False) else '❌'} ({v.get('confidence', 0):.0f}%)")
        
        prompt = f"""
You are a trading mentor teaching {agent_name}, a {agent_type} specialist.

Recent Performance:
{chr(10).join(vote_summary)}

Overall Stats:
- Win Rate: {performance.get('win_rate', 0):.0f}%
- Avg Confidence: {performance.get('avg_confidence', 0):.0f}%
- Total Votes: {performance.get('total_votes', 0)}

Teach {agent_name} how to improve voting decisions. Provide:
1. What they are doing wrong (if anything)
2. What they should change
3. Specific rules to follow
4. Confidence adjustment strategy

Be direct and actionable.
"""
        
        response = self._call_deepseek(prompt)
        
        if response:
            return response
        else:
            return self._get_default_voting_lesson(agent_name, agent_type)
    
    def _get_rule_based_advice(self, agent_name: str, agent_type: str, 
                                signal_data: Dict, agent_vote: str, agent_confidence: float) -> str:
        """Rule-based advice when DeepSeek is unavailable"""
        
        rsi = signal_data.get('rsi', 50)
        price = signal_data.get('current_price', 0)
        
        advice = f"""
📊 *Trading Advice for {agent_name}*

Current Analysis:
• RSI: {rsi:.1f}
• Price: ${price:.2f}
• Your Vote: {agent_vote} ({agent_confidence:.0f}%)

🎯 Recommendation:

"""
        
        if agent_vote == 'BUY':
            if rsi > 70:
                advice += "❌ Your BUY vote is RISKY! RSI is overbought (>70).\n"
                advice += "✅ Better to WAIT for pullback or vote HOLD.\n"
                advice += "💡 Lesson: Don't buy when RSI > 70 without strong trend confirmation."
            elif rsi < 30:
                advice += "✅ Your BUY vote is GOOD! RSI is oversold (<30).\n"
                advice += "💡 Lesson: Oversold conditions often lead to bounces."
            else:
                advice += "🟡 Your BUY vote is NEUTRAL. RSI is in mid-range.\n"
                advice += "💡 Lesson: Wait for additional confirmation (volume, support)."
        
        elif agent_vote == 'SELL':
            if rsi < 30:
                advice += "❌ Your SELL vote is RISKY! RSI is oversold (<30).\n"
                advice += "✅ Better to wait for bounce or vote HOLD.\n"
                advice += "💡 Lesson: Don't sell when RSI < 30 without strong trend confirmation."
            elif rsi > 70:
                advice += "✅ Your SELL vote is GOOD! RSI is overbought (>70).\n"
                advice += "💡 Lesson: Overbought conditions often lead to pullbacks."
            else:
                advice += "🟡 Your SELL vote is NEUTRAL. RSI is in mid-range.\n"
                advice += "💡 Lesson: Wait for additional confirmation (resistance, volume)."
        
        else:  # HOLD
            advice += "🟡 You voted HOLD.\n"
            if rsi < 30 or rsi > 70:
                advice += "💡 Consider: RSI is extreme - this could be a trading opportunity!"
            else:
                advice += "💡 Consider: Market is neutral - holding is reasonable."
        
        advice += f"\n🎯 Confidence Adjustment: {'Decrease' if (agent_vote == 'BUY' and rsi > 70) or (agent_vote == 'SELL' and rsi < 30) else 'Maintain'}"
        
        return advice
    
    def _get_rule_based_consensus(self, votes: Dict, signal_data: Dict) -> str:
        """Rule-based consensus - NOW INSIDE THE CLASS"""
        
        buy = sum(1 for v in votes.values() if v.get('vote') == 'BUY')
        sell = sum(1 for v in votes.values() if v.get('vote') == 'SELL')
        hold = sum(1 for v in votes.values() if v.get('vote') == 'HOLD')
        total = len(votes)
        
        rsi = signal_data.get('rsi', 50)
        price = signal_data.get('current_price', 0)
        
        buy_pct = (buy / total) * 100 if total > 0 else 0
        sell_pct = (sell / total) * 100 if total > 0 else 0
        hold_pct = (hold / total) * 100 if total > 0 else 0
        
        if buy > sell and buy > hold:
            decision = "BUY"
            if rsi < 30:
                confidence = 85
            elif rsi > 70:
                confidence = 55
            else:
                confidence = 70
        elif sell > buy and sell > hold:
            decision = "SELL"
            if rsi > 70:
                confidence = 85
            elif rsi < 30:
                confidence = 55
            else:
                confidence = 70
        else:
            decision = "HOLD"
            confidence = 60
        
        return f"""
📊 *DeepSeek Consensus Advice*

🎯 FINAL DECISION: {decision}
📈 CONFIDENCE: {confidence}%

📋 Vote Breakdown:
🟢 BUY: {buy_pct:.0f}% ({buy} votes)
🔴 SELL: {sell_pct:.0f}% ({sell} votes)
⚪ HOLD: {hold_pct:.0f}% ({hold} votes)

{'─' * 40}

🎯 NEXT STEPS:
• ENTRY: {'BUY' if decision == 'BUY' else 'SELL' if decision == 'SELL' else 'WAIT'}
• STOP LOSS: {'2% below' if decision == 'BUY' else '2% above' if decision == 'SELL' else 'N/A'}
• TAKE PROFIT: {'4% above' if decision == 'BUY' else '4% below' if decision == 'SELL' else 'N/A'}

⚠️ RSI: {rsi:.0f}
💰 Price: ${price:.2f}
"""
    
    def _get_default_voting_lesson(self, agent_name: str, agent_type: str) -> str:
        """Default voting lesson when DeepSeek is unavailable"""
        return f"""
📚 *Voting Lesson for {agent_name} ({agent_type})*

🎯 Key Rules to Follow:
1. Don't buy when RSI > 70 (overbought)
2. Don't sell when RSI < 30 (oversold)
3. Use HOLD when uncertain
4. Match confidence to market conditions

💡 Improvement Strategy:
• Reduce confidence by 20% when voting against RSI signals
• Always check RSI before voting
• When unsure, vote HOLD with 60% confidence

📈 Goal: Achieve >60% win rate
"""
    
    def _call_deepseek(self, prompt: str) -> Optional[str]:
        """Call DeepSeek API"""
        if not self.enabled:
            return None
        
        headers = {
            'Authorization': f'Bearer {self.api_key}',
            'Content-Type': 'application/json'
        }
        
        data = {
            'model': 'deepseek-chat',
            'messages': [
                {
                    'role': 'system',
                    'content': 'You are a professional trading advisor helping AI agents make better voting decisions. Be direct, actionable, and concise.'
                },
                {
                    'role': 'user',
                    'content': prompt
                }
            ],
            'temperature': 0.7,
            'max_tokens': 800
        }
        
        try:
            response = requests.post(self.api_url, headers=headers, json=data, timeout=30)
            
            if response.status_code == 200:
                result = response.json()
                return result['choices'][0]['message']['content']
            else:
                print(f"⚠️ DeepSeek API error: {response.status_code}")
                return None
                
        except Exception as e:
            print(f"⚠️ DeepSeek API call failed: {e}")
            return None

    # ============================================
    # ADD THIS METHOD HERE
    # ============================================
    
    def record_decision_outcome(self, decision: str, confidence: float, actual_outcome: str, pnl: float):
        """Record advisor decision outcome for performance tracking"""
        import psycopg2
        import os
        from dotenv import load_dotenv
        load_dotenv()
        
        was_correct = (decision == actual_outcome)
        
        try:
            conn = psycopg2.connect(
                host=os.getenv('DB_HOST', 'localhost'),
                database=os.getenv('DB_NAME', 'trading_platform'),
                user=os.getenv('DB_USER', 'postgres'),
                password=os.getenv('DB_PASSWORD', 'lama')
            )
            cur = conn.cursor()
            cur.execute("""
                INSERT INTO advisor_performance (advisor_decision, advisor_confidence, actual_outcome, was_correct, actual_pnl)
                VALUES (%s, %s, %s, %s, %s)
            """, (decision, confidence, actual_outcome, was_correct, pnl))
            conn.commit()
            cur.close()
            conn.close()
            
            self.total_predictions += 1
            if was_correct:
                self.correct_predictions += 1
                
            print(f"📊 Advisor decision recorded: {decision} - {'✅ Correct' if was_correct else '❌ Wrong'}")
            
        except Exception as e:
            print(f"Error recording performance: {e}")
# Singleton
_advisor = None

def get_deepseek_advisor():
    global _advisor
    if _advisor is None:
        _advisor = DeepSeekTradingAdvisor()
    return _advisor
