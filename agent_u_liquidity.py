# agent_u_liquidity.py - Liquidity & Stop Hunting Agent

"""
Agent_U - Liquidity & Stop Hunting Specialist
Detects institutional liquidity clusters and stop runs
"""

import random
from typing import Dict, List, Optional


class AgentU_Liquidity:
    """Detects institutional liquidity, stop hunts, and order flow"""
    
    def __init__(self):
        self.name = "Agent_U"
        self.agent_type = "Liquidity Specialist"
        self.key_levels = {}
        self._generate_key_levels()
        
        print(f"   ✅ {self.name} initialized")
    
    def _generate_key_levels(self):
        """Generate key psychological levels for each pair"""
        pairs = ['EURUSD', 'GBPUSD', 'USDJPY', 'AUDUSD', 'USDCAD', 'EURGBP', 'EURJPY', 'NZDUSD', 'USDCHF']
        
        for pair in pairs:
            self.key_levels[pair] = []
            
            # Base prices for each pair
            base_prices = {
                'EURUSD': 1.1000,
                'GBPUSD': 1.3000,
                'USDJPY': 150.00,
                'AUDUSD': 0.6500,
                'USDCAD': 1.3500,
                'EURGBP': 0.8500,
                'EURJPY': 165.00,
                'NZDUSD': 0.6000,
                'USDCHF': 0.9000
            }
            
            base = base_prices.get(pair, 1.0000)
            
            # Major levels (every 100 pips)
            for i in range(-30, 31):
                if 'JPY' in pair:
                    level = base + i * 1.0  # 1.0 = 100 pips for JPY
                else:
                    level = base + i * 0.0100  # 0.0100 = 100 pips for others
                self.key_levels[pair].append(round(level, 5))
    
    def analyze(self, symbol: str, price: float, usd_strength: float = 0, 
                usd_direction: str = 'NEUTRAL') -> Dict:
        """
        Analyze liquidity and stop hunting
        
        Args:
            symbol: Trading symbol (e.g., 'EURUSD')
            price: Current price
            usd_strength: USD strength from Dollar Engine (-100 to +100)
            usd_direction: 'STRONG', 'WEAK', or 'NEUTRAL'
        
        Returns:
            Dict with vote, confidence, and reasoning
        """
        levels = self.key_levels.get(symbol, [])
        
        if not levels:
            return {
                'vote': 'HOLD',
                'confidence': 50,
                'reasoning': 'No key levels available',
                'stop_run': False,
                'nearest_level': 0,
                'distance_pips': 999,
                'aligned': False
            }
        
        # Find nearest level
        nearest = min(levels, key=lambda x: abs(x - price))
        
        # Find levels above and below
        above = [l for l in levels if l > price]
        below = [l for l in levels if l < price]
        nearest_above = min(above) if above else None
        nearest_below = max(below) if below else None
        
        # Calculate distance in pips
        if 'JPY' in symbol:
            distance = abs(price - nearest) * 100  # For JPY pairs
        else:
            distance = abs(price - nearest) / 0.0001  # For other pairs
        
        # Detect stop run
        stop_run = False
        direction = 'HOLD'
        
        if distance < 20:  # Within 20 pips of key level
            stop_run = True
            if price > nearest:
                direction = 'SELL'  # Price above level = sell stop run
            else:
                direction = 'BUY'   # Price below level = buy stop run
        
        # Check alignment with USD
        aligned = False
        if direction == 'BUY' and usd_direction == 'WEAK':
            aligned = True
        elif direction == 'SELL' and usd_direction == 'STRONG':
            aligned = True
        elif usd_direction == 'NEUTRAL':
            aligned = True
        
        # Calculate confidence
        if stop_run:
            confidence = min(90, 70 + (20 - min(distance, 20)) / 20 * 20)
        else:
            confidence = 50
        
        return {
            'vote': direction if stop_run and aligned else 'HOLD',
            'confidence': confidence,
            'reasoning': f"Stop run at {nearest:.5f} ({distance:.1f} pips)" if stop_run else "No stop run detected",
            'stop_run': stop_run,
            'nearest_level': nearest,
            'distance_pips': round(distance, 1),
            'aligned': aligned,
            'above_level': nearest_above,
            'below_level': nearest_below
        }
    
    def get_status(self) -> Dict:
        """Get agent status"""
        return {
            'name': self.name,
            'type': self.agent_type,
            'pairs_tracked': len(self.key_levels),
            'total_levels': sum(len(v) for v in self.key_levels.values())
        }


# Test
if __name__ == "__main__":
    agent = AgentU_Liquidity()
    result = agent.analyze('EURUSD', 1.1025, usd_direction='WEAK')
    print(result)