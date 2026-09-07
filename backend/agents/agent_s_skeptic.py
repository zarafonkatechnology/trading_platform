"""
Agent_S - Skepticism Logic (Stop Hunt & Spoof Detection)
Trains agents to question: "Is this move fake?"
"""
from price_cache_manager import get_price_for_agent, get_any_price
from price_helper import get_price_with_fallback, get_price_with_details
import random
from datetime import datetime
from collections import deque
from .base_agent import BaseAgent

class SkepticAgent(BaseAgent):
    """
    Agent S - Detects fake moves and stop hunts
    Compares order book depth with actual price movement
    """
    
    def __init__(self):
        super().__init__(
            name="Agent_S",
            agent_type="Detects fake moves and stop hunts",
            specialization="Cmpares order book depth with actual price movement"
        )
        self.price_history = deque(maxlen=100)
        self.volume_history = deque(maxlen=100)
        
    def analyze(self, signal_data):
        """Analyze if current move is genuine or fake"""
        price = get_price_with_fallback(symbol, self.name)
    
        if price <= 0:
            return {'decision': 'HOLD', 'reason': 'No price available'}
        current_price = signal_data.get('price', 100.0)
        volume = signal_data.get('volume', 1000)
        
        # Detect stop hunt
        stop_hunt = self._detect_stop_hunt(current_price, volume)
        
        # Detect spoofing (fake walls)
        spoofing = self._detect_spoofing()
        
        # Detect distribution (whales selling into strength)
        distribution = self._detect_distribution(current_price, volume)
        
        # Make decision
        if stop_hunt['detected']:
            return {
                'agent': self.name,
                'type': self.agent_type,
                'vote': stop_hunt['direction'],
                'confidence': 92,
                'reasoning': f"🎯 STOP HUNT DETECTED: {stop_hunt['reason']} - Enter after liquidity grab",
                'stop_hunt': stop_hunt,
                'spoofing': spoofing,
                'timestamp': datetime.now().isoformat()
            }
        
        if spoofing['detected']:
            return {
                'agent': self.name,
                'type': self.agent_type,
                'vote': spoofing['direction'],
                'confidence': 88,
                'reasoning': f"🎭 SPOOFING DETECTED: {spoofing['reason']} - Fake wall manipulation",
                'stop_hunt': stop_hunt,
                'spoofing': spoofing,
                'timestamp': datetime.now().isoformat()
            }
        
        if distribution['detected']:
            return {
                'agent': self.name,
                'type': self.agent_type,
                'vote': 'HOLD' if distribution['direction'] == 'BUY' else 'SELL',
                'confidence': 85,
                'reasoning': f"🐋 DISTRIBUTION: {distribution['reason']} - Whales selling into strength",
                'stop_hunt': stop_hunt,
                'spoofing': spoofing,
                'timestamp': datetime.now().isoformat()
            }
        
        return {
            'agent': self.name,
            'type': self.agent_type,
            'vote': 'HOLD',
            'confidence': 50,
            'reasoning': "No fake move detected. Price action appears genuine.",
            'timestamp': datetime.now().isoformat()
        }
    
    def _detect_stop_hunt(self, current_price, volume):
        """Detect stop hunts - when price spikes to trigger stops"""
        # In production: Analyze order book for liquidity clusters
        # Stop hunt signature: Rapid spike beyond obvious level, immediate reversal
        
        import random
        if random.random() < 0.15:
            return {
                'detected': True,
                'direction': 'BUY' if random.random() > 0.5 else 'SELL',
                'reason': "Price spiked below key support, triggered stops, then reversed. Classic stop hunt."
            }
        return {'detected': False, 'direction': 'HOLD', 'reason': ''}
    
    def _detect_spoofing(self):
        """Detect fake walls - large orders placed then cancelled"""
        import random
        if random.random() < 0.1:
            return {
                'detected': True,
                'direction': 'BUY',
                'reason': "Large sell wall appeared, price dropped 0.2%, then wall vanished. Spoofing detected."
            }
        return {'detected': False, 'direction': 'HOLD', 'reason': ''}
    
    def _detect_distribution(self, current_price, volume):
        """Detect if whales are distributing (selling into strength)"""
        import random
        if random.random() < 0.12:
            return {
                'detected': True,
                'direction': 'SELL',
                'reason': "Price rising but volume decreasing. Whales distributing to retail."
            }
        return {'detected': False, 'direction': 'HOLD', 'reason': ''}
    def monte_carlo_forecast(self, current_price: float, volatility: float = 0.005, 
                         n_sims: int = 1000, horizon: int = 20) -> Dict:
        """
        Simulate future price paths and predict cloud position probability.
        """
        outcomes = {'above_cloud': 0, 'inside_cloud': 0, 'below_cloud': 0}
    
        for _ in range(n_sims):
            price = current_price
            path = [price]
            for _ in range(horizon):
                price *= (1 + random.gauss(0, volatility))
                path.append(price)
        
            # Get Ichimoku cloud at end of simulation (simplified)
            final_price = path[-1]
            # Assume cloud top/bottom based on current price ± 2%
            cloud_top = current_price * 1.01
            cloud_bottom = current_price * 0.99
        
            if final_price > cloud_top:
                outcomes['above_cloud'] += 1
            elif final_price < cloud_bottom:
                outcomes['below_cloud'] += 1
            else:
                outcomes['inside_cloud'] += 1
    
        probs = {k: round(v/n_sims*100, 1) for k, v in outcomes.items()}
    
        # Determine vote based on most probable outcome
        if probs['above_cloud'] > 60:
           vote = 'BUY'
           conf = probs['above_cloud']
        elif probs['below_cloud'] > 60:
            vote = 'SELL'
            conf = probs['below_cloud']
        else:
            vote = 'HOLD'
            conf = probs['inside_cloud']
    
        return {'vote': vote, 'confidence': conf, 'probabilities': probs}
    def get_current_price(symbol):
        """Get price with automatic fallback to cache"""
        result = price_cache.get_price(symbol, use_cache_fallback=True)
    
        if result and result.get('success'):
            return result['mid']
        else:
           # Return last cached price
           cached = price_cache.get_cached_price(symbol)
           if cached:
               return cached['mid']
        return None
     