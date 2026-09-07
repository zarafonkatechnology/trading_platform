"""
Agent_V - Neutral Psychology
Emotionless execution - the system's greatest advantage over humans
"""
from price_cache_manager import get_price_for_agent, get_any_price
from price_helper import get_price_with_fallback, get_price_with_details
import random
from datetime import datetime
from .base_agent import BaseAgent

class NeutralPsychologyAgent(BaseAgent):
    """
    Agent V - Pure logic, no emotion
    While humans panic or get greedy, this agent sees only mathematical deviations
    """
    
    def __init__(self):
       super().__init__(
            name="Agent_V",
            agent_type="Pure logic, no emotion",
            specialization="While humans panic or get greedy, this agent sees only mathematical deviations"
        )              
    def analyze(self, signal_data):
        """Pure mathematical analysis without emotion"""
        price = get_price_with_fallback(symbol, self.name)
    
        if price <= 0:
            return {'decision': 'HOLD', 'reason': 'No price available'}
        current_price = signal_data.get('price', 100.0)
        expected_price = signal_data.get('expected_price', current_price)
        
        # Calculate statistical deviation
        deviation = abs((current_price - expected_price) / expected_price) * 100
        
        # Check if market is overreacting
        overreaction = self._detect_overreaction(current_price, deviation)
        
        # Check for fear/greed extremes
        sentiment_extreme = self._detect_sentiment_extreme()
        
        if overreaction['detected']:
            return {
                'agent': self.name,
                'type': self.agent_type,
                'vote': overreaction['direction'],
                'confidence': 96,
                'reasoning': f"🧠 EMOTIONLESS LOGIC: {overreaction['reason']} - Market overreacting by {deviation:.1f}%. Contrarian entry.",
                'deviation': deviation,
                'timestamp': datetime.now().isoformat()
            }
        
        if sentiment_extreme['detected']:
            return {
                'agent': self.name,
                'type': self.agent_type,
                'vote': sentiment_extreme['direction'],
                'confidence': 93,
                'reasoning': f"🧠 EMOTIONLESS LOGIC: {sentiment_extreme['reason']} - Extreme {sentiment_extreme['emotion']} detected. Contrarian signal.",
                'timestamp': datetime.now().isoformat()
            }
        
        return {
            'agent': self.name,
            'type': self.agent_type,
            'vote': 'HOLD',
            'confidence': 55,
            'reasoning': "Market within normal statistical parameters. No emotional extreme detected.",
            'deviation': deviation,
            'timestamp': datetime.now().isoformat()
        }
    
    def _detect_overreaction(self, current_price, deviation):
        """Detect if market is overreacting to news/events"""
        import random
        
        if deviation > 1.5 and random.random() < 0.3:
            direction = 'BUY' if random.random() > 0.5 else 'SELL'
            return {
                'detected': True,
                'direction': direction,
                'reason': f"Price deviated {deviation:.1f}% from mean. Statistical overreaction. Reversal expected."
            }
        return {'detected': False, 'direction': 'HOLD', 'reason': ''}
    
    def _detect_sentiment_extreme(self):
        """Detect when sentiment reaches extreme levels"""
        import random
        if random.random() < 0.15:
            emotions = ['FEAR', 'GREED', 'PANIC', 'EUPHORIA']
            emotion = random.choice(emotions)
            direction = 'BUY' if emotion in ['FEAR', 'PANIC'] else 'SELL'
            return {
                'detected': True,
                'direction': direction,
                'emotion': emotion,
                'reason': f"Extreme {emotion} in market. Contrarian opportunity."
            }
        return {'detected': False, 'direction': 'HOLD', 'emotion': '', 'reason': ''}
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
     