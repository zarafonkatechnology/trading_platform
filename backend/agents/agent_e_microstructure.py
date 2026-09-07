"""
Agent A: Trend Follower - Hybrid Approach
Adapts to different assets and timeframes
"""

from backend.agents.base_agent import BaseAgent
import logging
from price_cache_manager import get_price_for_agent, get_any_price
from price_helper import get_price_with_fallback, get_price_with_details
logger = logging.getLogger(__name__)

class AgentEMicrostructure(BaseAgent):
    def __init__(self):
        super().__init__("Agent_E", "Microstructure", "Moving Average Crossovers")
    
    def predict(self, signal_data, market_features):
        """
        Trend following logic that adapts to asset and timeframe
        """
        try:
            asset = signal_data.get('asset_type', 'UNKNOWN')
            timeframe = market_features.get('timeframe', 15)
            confidence = signal_data.get('confidence_percent', 70)
            
            # Asset-specific adjustments
            asset_sensitivity = {
                'XAU/USD': 1.2,   # Gold - higher sensitivity
                'XAG/USD': 1.3,   # Silver - very high sensitivity
                'BCO/USD': 1.1,   # Oil - moderate
                'S&P500/USD': 0.9, # S&P 500 - lower sensitivity
                'EURUSD': 0.8,    # Forex - lower sensitivity
            }
            sensitivity = asset_sensitivity.get(asset, 1.0)
            
            # Timeframe-specific thresholds
            if timeframe <= 5:
                trend_threshold = 0.3
            elif timeframe <= 15:
                trend_threshold = 0.5
            elif timeframe <= 60:
                trend_threshold = 0.7
            else:
                trend_threshold = 1.0
            
            # Adjusted confidence
            adjusted_confidence = confidence * sensitivity
            
            # Trend following logic
            if adjusted_confidence > (75 * sensitivity):
                action = 'BUY'
                final_confidence = min(95, adjusted_confidence)
            elif adjusted_confidence < (45 * sensitivity):
                action = 'SELL'
                final_confidence = min(90, 100 - adjusted_confidence)
            else:
                action = 'HOLD'
                final_confidence = 55
            
            logger.debug(f"{self.name} on {asset} ({timeframe}min): {action} with {final_confidence:.0f}%")
            
            return action, final_confidence
            
        except Exception as e:
            logger.error(f"{self.name} prediction error: {e}")
            return 'HOLD', 50
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
     
        
