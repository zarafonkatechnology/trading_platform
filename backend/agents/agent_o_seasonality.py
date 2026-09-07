"""
Agent_O - Seasonality Expert
Determines monthly bias and seasonal patterns
"""
from price_cache_manager import get_price_for_agent, get_any_price
from price_helper import get_price_with_fallback, get_price_with_details
from datetime import datetime
import calendar
import random
from typing import Dict
from .base_agent import BaseAgent

class SeasonalityExpert(BaseAgent):
    """Agent O - Seasonality Analysis for Macro Context"""
    
    def __init__(self):
        super().__init__("Agent_O", "Seasonality Expert")
        
        # Historical seasonal patterns
        self.monthly_bias = {
            1: {"name": "January", "bias": "bullish", "strength": 65, "saying": "January Effect - New year inflows"},
            2: {"name": "February", "bias": "neutral", "strength": 50, "saying": "Post-January consolidation"},
            3: {"name": "March", "bias": "bullish", "strength": 55, "saying": "Spring rally begins"},
            4: {"name": "April", "bias": "bullish", "strength": 60, "saying": "Tax season liquidity"},
            5: {"name": "May", "bias": "bearish", "strength": 35, "saying": "Sell in May and Go Away"},
            6: {"name": "June", "bias": "bearish", "strength": 40, "saying": "Summer lull begins"},
            7: {"name": "July", "bias": "neutral", "strength": 50, "saying": "Summer volatility"},
            8: {"name": "August", "bias": "bearish", "strength": 45, "saying": "Vacation season - low liquidity"},
            9: {"name": "September", "bias": "bearish", "strength": 30, "saying": "Worst month for markets"},
            10: {"name": "October", "bias": "neutral", "strength": 50, "saying": "Turnaround month"},
            11: {"name": "November", "bias": "bullish", "strength": 70, "saying": "Santa Rally begins"},
            12: {"name": "December", "bias": "bullish", "strength": 75, "saying": "Santa Rally - Year-end rally"}
        }
        
        self.holiday_effects = {
            "Gold": {"months": [1, 2, 8, 9, 12], "bias": "bullish", "reason": "Holiday season demand"},
            "EURUSD": {"months": [3, 4, 9, 10], "bias": "volatile", "reason": "Central bank meetings"}
        }
    
    def analyze(self, signal_data):
        """Analyze seasonal context for trading bias"""
        price = get_price_with_fallback(symbol, self.name)
    
        if price <= 0:
            return {'decision': 'HOLD', 'reason': 'No price available'}
        current_date = datetime.now()
        month = current_date.month
        day = current_date.day
        weekday = current_date.weekday()
        
        # Get monthly bias
        monthly = self.monthly_bias.get(month, {"bias": "neutral", "strength": 50})
        
        # Day of week pattern
        day_patterns = {
            0: {"bias": "neutral", "note": "Monday - Trend start"},
            1: {"bias": "bullish", "note": "Tuesday - Momentum builds"},
            2: {"bias": "bullish", "note": "Wednesday - Strongest day"},
            3: {"bias": "bearish", "note": "Thursday - Profit taking"},
            4: {"bias": "neutral", "note": "Friday - Position squaring"}
        }
        day_bias = day_patterns.get(weekday, {"bias": "neutral"})
        
        # Calculate overall seasonality score
        seasonality_score = monthly["strength"]
        if day_bias["bias"] == "bullish":
            seasonality_score += 5
        elif day_bias["bias"] == "bearish":
            seasonality_score -= 5
        
        # Determine vote based on seasonality
        if seasonality_score > 60:
            vote = "BUY"
            confidence = seasonality_score
            reasoning = f"📅 {monthly['name']}: {monthly['saying']} - {day_bias['note']}"
        elif seasonality_score < 40:
            vote = "SELL"
            confidence = 100 - seasonality_score
            reasoning = f"📅 {monthly['name']}: {monthly['saying']} - Historically bearish"
        else:
            vote = "HOLD"
            confidence = 50
            reasoning = f"📅 {monthly['name']}: Neutral seasonal bias"
        
        return {
            'agent': self.name,
            'type': self.agent_type,
            'vote': vote,
            'confidence': confidence,
            'reasoning': reasoning,
            'seasonality_data': {
                'month': month,
                'month_name': monthly['name'],
                'monthly_bias': monthly['bias'],
                'monthly_strength': monthly['strength'],
                'day_bias': day_bias['bias'],
                'day_note': day_bias['note'],
                'seasonality_score': seasonality_score,
                'holiday_effect': self.holiday_effects.get("EURUSD", {})
            },
            'position_multiplier': 0.5 if monthly['bias'] == 'bearish' else 1.0,
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
     