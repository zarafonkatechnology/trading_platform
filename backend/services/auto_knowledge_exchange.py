"""
Automatic Knowledge Exchange - Agents share insights without manual input
"""

import random
import threading
import time
import logging
from datetime import datetime
from typing import Dict, List

logger = logging.getLogger(__name__)

class AutoKnowledgeExchange:
    """
    Automatically handles knowledge sharing between agents
    """
    
    # Knowledge templates based on agent type
    KNOWLEDGE_TEMPLATES = {
        'Trend Follower': {
            'insights': [
                "I detected a {direction} trend on {asset} with strength {strength}%",
                "Moving average crossover signal on {asset}: {ma_fast} crossed {ma_slow}",
                "Trend momentum is {momentum} on {asset}, {action} recommended"
            ],
            'warnings': [
                "Warning: Trend weakening on {asset}, consider reducing position",
                "Caution: Fake breakout detected on {asset}",
                "Alert: Trend reversal pattern forming on {asset}"
            ]
        },
        'Mean Reversion': {
            'insights': [
                "RSI on {asset} at {rsi} - {'overbought' if rsi > 70 else 'oversold' if rsi < 30 else 'neutral'}",
                "Bollinger bands on {asset}: price at {position}% of band width",
                "Mean reversion opportunity on {asset} at ${price}"
            ],
            'warnings': [
                "Warning: RSI divergence detected on {asset}",
                "Caution: Support level broken on {asset}",
                "Alert: Volatility spike may invalidate reversion"
            ]
        },
        'Momentum': {
            'insights': [
                "Momentum accelerating on {asset} at {rate}% per period",
                "Volume confirms momentum on {asset} with {volume_ratio}x average",
                "Price action shows {strength} momentum on {asset}"
            ],
            'warnings': [
                "Warning: Momentum divergence on {asset}",
                "Caution: Volume decreasing while price rising on {asset}",
                "Alert: Momentum oscillator at extreme on {asset}"
            ]
        },
        'Volatility': {
            'insights': [
                "Volatility on {asset} at {volatility}% - {'HIGH' if volatility > 2 else 'LOW'}",
                "ATR suggests {position_size} position size for {asset}",
                "Volatility regime: {regime} on {asset}"
            ],
            'warnings': [
                "Warning: Extreme volatility on {asset}, reduce position size",
                "Caution: Volatility spike may cause slippage",
                "Alert: Unusual volatility pattern detected"
            ]
        },
        'Microstructure': {
            'insights': [
                "Order flow suggests {sentiment} sentiment on {asset}",
                "Bid-ask spread {spread} on {asset} - {'tight' if spread < 0.001 else 'wide'}",
                "Volume profile shows support at ${support}, resistance at ${resistance}"
            ],
            'warnings': [
                "Warning: Unusual order flow detected on {asset}",
                "Caution: Liquidity drying up on {asset}",
                "Alert: Large sell order detected"
            ]
        },
        'Candlestick Pattern Specialist': {
            'insights': [
               "I detected a {pattern} pattern on {asset} - this is a {type} reversal signal",
                "Candlestick analysis shows {pattern} with {confidence}% reliability",
               "The {pattern} pattern on {asset} suggests {direction} movement"
            ],
            'warnings': [
                "Warning: Doji pattern detected - indecision in market",
                 "Caution: Evening star forming on {asset} - potential reversal",
                 "Alert: Bearish engulfing pattern on {asset} - consider reducing longs"
    ]
    
}
    }
    
    ASSETS = ['XAU/USD', 'XAG/USD', 'BCO/USD', 'S&P500/USD', 'EURUSD', 'GBPUSD', 'USDJPY']
    
    def __init__(self, agent_manager, db_manager, knowledge_exchange_list=None):
        self.agent_manager = agent_manager
        self.db = db_manager
        self.knowledge_exchange_list = knowledge_exchange_list
        self.is_running = False
        self.exchange_thread = None
    
    def start(self, interval_seconds=60):
        """Start automatic knowledge exchange"""
        self.is_running = True
        self.exchange_thread = threading.Thread(target=self._exchange_loop, args=(interval_seconds,), daemon=True)
        self.exchange_thread.start()
        print("🔄 Auto Knowledge Exchange started (every {} seconds)".format(interval_seconds))
    
    def _exchange_loop(self, interval):
        """Main loop for automatic knowledge exchange"""
        while self.is_running:
            try:
                self._run_knowledge_cycle()
                time.sleep(interval)
            except Exception as e:
                print(f"Knowledge exchange error: {e}")
                time.sleep(interval)
    
    def _run_knowledge_cycle(self):
        """Run one cycle of knowledge exchange"""
        agents = self.agent_manager.get_all_agents()
        if len(agents) < 2:
            return
        
        # Randomly select 2-3 agents
        num_exchanging = random.randint(2, min(4, len(agents)))
        exchanging_agents = random.sample(agents, num_exchanging)
        
        # Random asset
        asset = random.choice(self.ASSETS)
        
        # Base price
        base_prices = {
            'XAU/USD': 2350, 'XAG/USD': 28.5, 'BCO/USD': 82, 
            'S&P500/USD': 4750, 'EURUSD': 1.09, 'GBPUSD': 1.26, 'USDJPY': 148
        }
        price = base_prices.get(asset, 100)
        current_price = price * (1 + random.uniform(-0.02, 0.02))
        
        # Market conditions
        conditions = {
            'volatility': round(random.uniform(0.3, 2.5), 1),
            'trend_strength': random.randint(30, 85),
            'rsi': random.randint(25, 75),
            'volume_ratio': round(random.uniform(0.7, 1.8), 1)
        }
        
        # Each agent shares insight
        for agent in exchanging_agents:
            insight = self._generate_insight(agent, asset, current_price, conditions)
            if insight:
                self._record_knowledge_exchange(agent, insight, exchanging_agents)
    
    def _generate_insight(self, agent, asset, price, conditions) -> str:
        """Generate insight based on agent type"""
        agent_type = agent.agent_type
        templates = self.KNOWLEDGE_TEMPLATES.get(agent_type, self.KNOWLEDGE_TEMPLATES['Trend Follower'])
        
        is_warning = random.random() < 0.3
        template_list = templates['warnings'] if is_warning else templates['insights']
        template = random.choice(template_list)
        
        # Fill template
        insight = template
        insight = insight.replace('{asset}', asset)
        insight = insight.replace('{price}', f"{price:.2f}")
        insight = insight.replace('{direction}', random.choice(['strong', 'weak', 'developing']))
        insight = insight.replace('{strength}', str(random.randint(40, 95)))
        insight = insight.replace('{ma_fast}', str(random.randint(5, 20)))
        insight = insight.replace('{ma_slow}', str(random.randint(50, 200)))
        insight = insight.replace('{momentum}', random.choice(['accelerating', 'decelerating']))
        insight = insight.replace('{action}', random.choice(['BUY on dips', 'HOLD', 'take profits']))
        insight = insight.replace('{rsi}', str(conditions['rsi']))
        insight = insight.replace('{position}', str(random.randint(10, 90)))
        insight = insight.replace('{rate}', str(round(random.uniform(0.5, 3.0), 1)))
        insight = insight.replace('{volume_ratio}', str(conditions['volume_ratio']))
        insight = insight.replace('{volatility}', str(conditions['volatility']))
        insight = insight.replace('{position_size}', random.choice(['smaller', 'normal', 'larger']))
        insight = insight.replace('{regime}', random.choice(['calm', 'normal', 'turbulent']))
        insight = insight.replace('{sentiment}', random.choice(['bullish', 'bearish', 'neutral']))
        insight = insight.replace('{spread}', f"{random.uniform(0.0005, 0.002):.4f}")
        insight = insight.replace('{support}', f"{price * 0.99:.2f}")
        insight = insight.replace('{resistance}', f"{price * 1.01:.2f}")
        
        return insight
    
    def _record_knowledge_exchange(self, agent, insight: str, participants: List):
        """Record knowledge exchange - THIS IS THE METHOD THAT WAS MISSING"""
        exchange = {
            'from_agent': agent.name,
            'to_agent': 'ALL AGENTS',
            'topic': f"💡 {agent.agent_type} Insight",
            'content': insight,
            'xp_reward': 5,
            'token_reward': 2,
            'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        }
        
        # Award XP
        agent.xp_points += 5
        agent.token_balance += 2
        agent.knowledge_shared_count += 1
        
        if self.knowledge_exchange_list is not None:
           self.knowledge_exchange_list.insert(0, exchange)
        print(f"📚 [DASHBOARD] Added to list. Total items: {len(self.knowledge_exchange_list)}")
    def stop(self):
        """Stop auto knowledge exchange"""
        self.is_running = False
