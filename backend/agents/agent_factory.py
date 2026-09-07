"""
Agent Factory - Creates all agents dynamically from database roles
"""
from price_cache_manager import get_price_for_agent, get_any_price
from price_helper import get_price_with_fallback, get_price_with_details
from .base_agent import BaseAgent

class DynamicAgent(BaseAgent):
    """Generic agent that uses role data from database"""
    def __init__(self, name, role, timeframe, weight):
        super().__init__(name, role)
        self.role = role
        self.timeframe = timeframe
        self.weight = weight
    
    def analyze(self, signal_data):
        price = get_price_with_fallback(symbol, self.name)
    
        if price <= 0:
            return {'decision': 'HOLD', 'reason': 'No price available'}
        # In production, each agent would have custom logic.
        # For now, we implement a simplified version based on role.
        import random
        
        # Some roles have specialized simulators
        if self.role == 'Ichimoku Direction':
            # Agent_K logic
            cloud_position = random.choice(['above', 'inside', 'below'])
            vote = 'BUY' if cloud_position == 'above' else 'SELL' if cloud_position == 'below' else 'HOLD'
            confidence = random.randint(60, 95)
        elif self.role == 'Trend Direction':
            # Agent_A logic
            ma_cross = random.choice(['golden', 'death', 'none'])
            vote = 'BUY' if ma_cross == 'golden' else 'SELL' if ma_cross == 'death' else 'HOLD'
            confidence = random.randint(55, 90)
        elif self.role == 'Pattern Recognition':
            # Agent_F logic
            pattern = random.choice(['triangle', 'flag', 'none'])
            vote = 'BUY' if pattern in ['triangle', 'flag'] else 'HOLD'
            confidence = random.randint(60, 85)
        elif self.role == 'Supply/Demand':
            # Agent_R logic
            zone = random.choice(['support', 'resistance', 'none'])
            vote = 'BUY' if zone == 'support' else 'SELL' if zone == 'resistance' else 'HOLD'
            confidence = random.randint(65, 90)
        # ... add more role-specific logic
        else:
            # Default random for missing roles
            vote = random.choice(['BUY', 'SELL', 'HOLD'])
            confidence = random.randint(50, 90)
        
        return {
            'agent': self.name,
            'role': self.role,
            'timeframe': self.timeframe,
            'vote': vote,
            'confidence': confidence,
            'weight': self.weight,
            'timestamp': datetime.now().isoformat()
        }
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
     
        
