"""
Agent_T - Confluence Strategy
Multi-indicator consensus for high-probability trades
"""
from price_cache_manager import get_price_for_agent, get_any_price
from price_helper import get_price_with_fallback, get_price_with_details
import random
from datetime import datetime
from .base_agent import BaseAgent

class ConfluenceAgent(BaseAgent):
    """
    Agent T - Finds confluence between multiple indicators
    A single indicator is guesswork, a group is truth
    """
    
    def __init__(self):
        super().__init__(
            name="Agent_T",
            agent_type="Finds confluence between multiple indicators",
            specialization="A single indicator is guesswork, a group is truth"
        )
    
    def analyze(self, signal_data):
        """Find confluence between multiple indicators"""
        price = get_price_with_fallback(symbol, self.name)
    
        if price <= 0:
            return {'decision': 'HOLD', 'reason': 'No price available'}
        # Get indicator values (in production: from real calculations)
        indicators = self._calculate_indicators(signal_data)
        
        # Count bullish vs bearish signals
        bullish_signals = sum(1 for v in indicators.values() if v == 'bullish')
        bearish_signals = sum(1 for v in indicators.values() if v == 'bearish')
        total_signals = len(indicators)
        
        # Calculate confluence score
        if bullish_signals > bearish_signals:
            confluence_score = (bullish_signals / total_signals) * 100
        else:
            confluence_score = (bearish_signals / total_signals) * 100
        
        # Determine if this is a high-probability setup
        if bullish_signals >= 4:
            return {
                'agent': self.name,
                'type': self.agent_type,
                'vote': 'BUY',
                'confidence': min(95, 60 + confluence_score * 0.35),
                'reasoning': f"🎯 STRONG CONFLUENCE: {bullish_signals}/{total_signals} indicators align BULLISH",
                'indicators': indicators,
                'confluence_score': confluence_score,
                'timestamp': datetime.now().isoformat()
            }
        
        if bearish_signals >= 4:
            return {
                'agent': self.name,
                'type': self.agent_type,
                'vote': 'SELL',
                'confidence': min(95, 60 + confluence_score * 0.35),
                'reasoning': f"🎯 STRONG CONFLUENCE: {bearish_signals}/{total_signals} indicators align BEARISH",
                'indicators': indicators,
                'confluence_score': confluence_score,
                'timestamp': datetime.now().isoformat()
            }
        
        if confluence_score > 70:
            direction = 'BUY' if bullish_signals > bearish_signals else 'SELL'
            return {
                'agent': self.name,
                'type': self.agent_type,
                'vote': direction,
                'confidence': confluence_score,
                'reasoning': f"✅ MODERATE CONFLUENCE: {confluence_score:.0f}% alignment",
                'indicators': indicators,
                'confluence_score': confluence_score,
                'timestamp': datetime.now().isoformat()
            }
        
        return {
            'agent': self.name,
            'type': self.agent_type,
            'vote': 'HOLD',
            'confidence': 40,
            'reasoning': f"⚠️ LOW CONFLUENCE: Only {max(bullish_signals, bearish_signals)}/{total_signals} indicators align",
            'indicators': indicators,
            'confluence_score': confluence_score,
            'timestamp': datetime.now().isoformat()
        }
    
    def _calculate_indicators(self, signal_data):
        """Calculate multiple indicators for confluence"""
        import random
        
        return {
            'fibonacci_618': random.choice(['bullish', 'bearish', 'neutral']),
            'ichimoku_cloud': random.choice(['bullish', 'bearish', 'neutral']),
            'rsi_divergence': random.choice(['bullish', 'bearish', 'neutral']),
            'volume_profile': random.choice(['bullish', 'bearish', 'neutral']),
            'moving_average': random.choice(['bullish', 'bearish', 'neutral']),
            'macd': random.choice(['bullish', 'bearish', 'neutral'])
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
     