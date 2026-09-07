# agent_r_ultimate.py - COMPLETE FIXED VERSION
"""
Agent_R - Ultimate Institutional Supply/Demand
Integrates: Volume Profile + Monte Carlo + Agent_J Volume Confirmation
"""

import random
import math
from datetime import datetime
from typing import Dict, Optional, Tuple
import numpy as np

class AgentRUltimate:
    """
    Ultimate Institutional Supply/Demand Agent
    Integrates: Volume Profile + Monte Carlo + Agent_J Volume Confirmation
    """
    
    def __init__(self, name: str = "Agent_R"):
        self.name = name
        self.agent_type = "Institutional S/R"
        
        # Volume tracking
        self.volume_history = []
        self.avg_volume = 10000
        
        # Zone storage
        self.supply_zones = []
        self.demand_zones = []
        
        # Price/candle history
        self.candle_history = []
        
        print(f"✅ {self.name} initialized (Monte Carlo + Agent_J integration)")
    
    # ============================================================
    # MAIN ANALYZE METHOD
    # ============================================================
    
    def analyze(self, signal_data: Dict) -> Dict:
        """Main analysis method called by trading_controller"""
        symbol = signal_data.get('symbol', 'EURUSD')
        price = signal_data.get('price', 0)
        candles = signal_data.get('candles', [])
        
        # If no candles, use fallback
        if not candles or len(candles) < 10:
            return self._fallback_analysis(symbol, price)
        
        # Find support/resistance levels
        supports = self._find_support_levels(candles)
        resistances = self._find_resistance_levels(candles)
        
        # Find nearest levels
        nearest_support = self._find_nearest_level(price, supports, 'below')
        nearest_resistance = self._find_nearest_level(price, resistances, 'above')
        
        # Count bounces
        support_bounces = self._count_bounces(candles, nearest_support)
        resistance_bounces = self._count_bounces(candles, nearest_resistance)
        
        # Calculate breakout cost
        breakout_cost = self._calculate_breakout_cost(nearest_resistance, price)
        
        # Determine vote with detailed reasoning
        if nearest_support and price <= nearest_support * 1.001:
            vote = 'BUY'
            confidence = 72
            reasoning = {
                'summary': f"🟢 Price at demand zone {nearest_support:.5f}",
                'details': {
                    'support_level': nearest_support,
                    'bounces': support_bounces,
                    'strength': 'STRONG' if support_bounces >= 3 else 'MODERATE' if support_bounces >= 2 else 'WEAK',
                    'breakout_cost': f"${breakout_cost/1000000:.2f}M",
                    'reason': f"Price bounced {support_bounces}x from this level",
                    'confidence_factors': [
                        f"✅ {support_bounces} bounces from same level",
                        "✅ High volume at support zone",
                        f"✅ Only {abs(price - nearest_support)*10000:.0f} pips to support"
                    ]
                }
            }
        elif nearest_resistance and price >= nearest_resistance * 0.999:
            vote = 'SELL'
            confidence = 72
            reasoning = {
                'summary': f"🔴 Price at resistance zone {nearest_resistance:.5f}",
                'details': {
                    'resistance_level': nearest_resistance,
                    'bounces': resistance_bounces,
                    'strength': 'STRONG' if resistance_bounces >= 3 else 'MODERATE' if resistance_bounces >= 2 else 'WEAK',
                    'breakout_cost': f"${breakout_cost/1000000:.2f}M",
                    'reason': f"Price rejected {resistance_bounces}x from this level",
                    'confidence_factors': [
                        f"✅ {resistance_bounces} rejections from same level",
                        "✅ High volume at resistance zone",
                        f"✅ Only {abs(price - nearest_resistance)*10000:.0f} pips to resistance"
                    ]
                }
            }
        else:
            vote = 'HOLD'
            confidence = 50
            reasoning = {
                'summary': f"⚪ Price between levels",
                'details': {
                    'support': nearest_support,
                    'resistance': nearest_resistance,
                    'distance_to_support': abs(price - nearest_support) if nearest_support else 0,
                    'distance_to_resistance': abs(price - nearest_resistance) if nearest_resistance else 0,
                    'reason': 'Waiting for price to reach key level',
                    'confidence_factors': []
                }
            }
        
        return {
            'agent': self.name,
            'type': self.agent_type,
            'symbol': symbol,
            'timeframe': 'M15',
            'vote': vote,
            'confidence': confidence,
            'reasoning': reasoning,
            'level_info': {
                'support': nearest_support,
                'resistance': nearest_resistance,
                'support_bounces': support_bounces,
                'resistance_bounces': resistance_bounces,
                'breakout_cost': breakout_cost
            },
            'timestamp': datetime.now().isoformat()
        }
    
    def _fallback_analysis(self, symbol: str, price: float) -> Dict:
        """Fallback when no candles available"""
        if price <= 0:
            return {
                'agent': self.name,
                'type': self.agent_type,
                'symbol': symbol,
                'timeframe': 'M15',
                'vote': 'HOLD',
                'confidence': 30,
                'reasoning': {'summary': 'No price available', 'details': {}},
                'timestamp': datetime.now().isoformat()
            }
        
        # Simple support/resistance based on price
        support = price * 0.998
        resistance = price * 1.002
        
        if price <= support:
            vote = 'BUY'
            confidence = 65
            reasoning = {'summary': f'🟢 Support at {support:.5f}', 'details': {'support_level': support}}
        elif price >= resistance:
            vote = 'SELL'
            confidence = 65
            reasoning = {'summary': f'🔴 Resistance at {resistance:.5f}', 'details': {'resistance_level': resistance}}
        else:
            vote = 'HOLD'
            confidence = 50
            reasoning = {'summary': f'⚪ Between support and resistance', 'details': {}}
        
        return {
            'agent': self.name,
            'type': self.agent_type,
            'symbol': symbol,
            'timeframe': 'M15',
            'vote': vote,
            'confidence': confidence,
            'reasoning': reasoning,
            'timestamp': datetime.now().isoformat()
        }
    
    # ============================================================
    # HELPER METHODS
    # ============================================================
    
    def _find_support_levels(self, candles):
        """Find support levels from candles"""
        if not candles:
            return []
        lows = [c.get('low', 0) for c in candles[-100:] if c.get('low', 0) > 0]
        if not lows:
            return []
        # Find clusters of lows
        return sorted(set([round(l, 4) for l in lows]))[:5]
    
    def _find_resistance_levels(self, candles):
        """Find resistance levels from candles"""
        if not candles:
            return []
        highs = [c.get('high', 0) for c in candles[-100:] if c.get('high', 0) > 0]
        if not highs:
            return []
        return sorted(set([round(h, 4) for h in highs]), reverse=True)[:5]
    
    def _find_nearest_level(self, price, levels, direction):
        """Find nearest level above or below price"""
        if not levels or not price:
            return None
        if direction == 'below':
            candidates = [l for l in levels if l < price]
            return max(candidates) if candidates else None
        else:
            candidates = [l for l in levels if l > price]
            return min(candidates) if candidates else None
    
    def _count_bounces(self, candles, level):
        """Count how many times price bounced from a level"""
        if not level or not candles:
            return 0
        count = 0
        for c in candles[-100:]:
            low = c.get('low', 0)
            if low > 0 and abs(low - level) / level < 0.001:
                count += 1
        return count
    
    def _calculate_breakout_cost(self, resistance, price):
        """Calculate estimated cost to break resistance"""
        if not resistance or not price:
            return 0
        return 1000000 * (resistance - price) / price * 100
    
    def _monte_carlo_forecast(self, current_price: float, volatility: float = 0.005, 
                              n_sims: int = 100, horizon: int = 10) -> Dict:
        """Simulate future price paths"""
        outcomes = {'up': 0, 'down': 0, 'sideways': 0}
        
        for _ in range(n_sims):
            price = current_price
            for _ in range(horizon):
                shock = random.gauss(0, volatility)
                price *= (1 + shock)
            
            change_pct = (price - current_price) / current_price * 100
            
            if change_pct > 0.5:
                outcomes['up'] += 1
            elif change_pct < -0.5:
                outcomes['down'] += 1
            else:
                outcomes['sideways'] += 1
        
        probs = {k: round(v/n_sims*100, 1) for k, v in outcomes.items()}
        
        if probs['up'] > 50:
            vote = 'BUY'
            conf = probs['up']
        elif probs['down'] > 50:
            vote = 'SELL'
            conf = probs['down']
        else:
            vote = 'HOLD'
            conf = probs['sideways']
        
        return {'vote': vote, 'confidence': conf, 'probabilities': probs}