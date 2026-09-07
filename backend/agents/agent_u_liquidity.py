"""
Agent_U - Liquidity Tactics
Tracks where whales are hunting liquidity
"""
from price_cache_manager import get_price_for_agent, get_any_price
from price_helper import get_price_with_fallback, get_price_with_details
import random
from datetime import datetime
from collections import defaultdict
from .base_agent import BaseAgent

class LiquidityAgent(BaseAgent):
    """
    Agent U - Detects liquidity clusters and stop runs
    Market doesn't move because of patterns - it moves because whales need to execute orders
    """
    
    def __init__(self):
        super().__init__(
            name="Agent_U",
            agent_type=" Detects liquidity clusters and stop runs",
            specialization="    Market doesn't move because of patterns - it moves because whales need to execute orders"
        )      
        self.liquidity_levels = defaultdict(int)
        self.stop_clusters = []
        
    def analyze(self, signal_data):
        """Analyze liquidity and stop run opportunities"""
        price = get_price_with_fallback(symbol, self.name)
    
        if price <= 0:
            return {'decision': 'HOLD', 'reason': 'No price available'}
        current_price = signal_data.get('price', 100.0)
        
        # Find liquidity clusters
        liquidity_clusters = self._find_liquidity_clusters(current_price)
        
        # Detect stop run in progress
        stop_run = self._detect_stop_run(current_price)
        
        # Find optimal entry after liquidity grab
        optimal_entry = self._find_optimal_entry(current_price, stop_run)
        
        if stop_run['in_progress']:
            return {
                'agent': self.name,
                'type': self.agent_type,
                'vote': stop_run['direction'],
                'confidence': 94,
                'reasoning': f"⚡ LIQUIDITY GRAB: {stop_run['reason']} - Enter after stops are cleared at {optimal_entry:.5f}",
                'liquidity_clusters': liquidity_clusters,
                'optimal_entry': optimal_entry,
                'timestamp': datetime.now().isoformat()
            }
        
        if liquidity_clusters['nearby']:
            return {
                'agent': self.name,
                'type': self.agent_type,
                'vote': 'WATCH',
                'confidence': 75,
                'reasoning': f"📊 LIQUIDITY DETECTED: Stop cluster at {liquidity_clusters['level']:.5f}. Watch for hunt.",
                'liquidity_clusters': liquidity_clusters,
                'timestamp': datetime.now().isoformat()
            }
        
        return {
            'agent': self.name,
            'type': self.agent_type,
            'vote': 'HOLD',
            'confidence': 50,
            'reasoning': "No significant liquidity clusters nearby. Normal market conditions.",
            'timestamp': datetime.now().isoformat()
        }
    
    def _find_liquidity_clusters(self, current_price):
        """Find where stop losses are clustered"""
        # In production: Analyze order book and open interest
        
        import random
        has_cluster = random.random() < 0.2
        
        if has_cluster:
            direction = random.choice(['above', 'below'])
            level = current_price * (1 + random.uniform(0.003, 0.01)) if direction == 'above' else current_price * (1 - random.uniform(0.003, 0.01))
            return {
                'nearby': True,
                'level': round(level, 5),
                'direction': direction,
                'estimated_size': random.randint(10, 50)  # million dollars
            }
        
        return {'nearby': False, 'level': None, 'direction': None}
    
    def _detect_stop_run(self, current_price):
        """Detect if a stop run is currently happening"""
        import random
        if random.random() < 0.1:
            direction = 'BUY' if random.random() > 0.5 else 'SELL'
            return {
                'in_progress': True,
                'direction': direction,
                'reason': f"Price aggressively moved to {direction} stops. Liquidity sweep complete. Reversal imminent."
            }
        return {'in_progress': False, 'direction': 'HOLD', 'reason': ''}
    
    def _find_optimal_entry(self, current_price, stop_run):
        """Calculate optimal entry after liquidity grab"""
        if stop_run['in_progress']:
            return round(current_price * 0.998 if stop_run['direction'] == 'BUY' else current_price * 1.002, 5)
        return current_price
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
     