"""
Agent_N - Intermarket Analysis
Checks correlations between asset classes
"""

import random
from datetime import datetime
from .base_agent import BaseAgent
from price_cache_manager import get_price_for_agent, get_any_price
from price_helper import get_price_with_fallback, get_price_with_details
class IntermarketMaster(BaseAgent):
    """Agent N - Intermarket Correlation Analysis"""
    
    def __init__(self):
        super().__init__(
            name="Agent_N",
            agent_type="Intermarket Master",
            specialization="Analyzes correlations between asset classes"
        )
        self.correlations = {
            'dxy': -0.85,    # USD negative correlation with EUR
            'bonds_10y': 0.40,   # Bonds vs EUR
            'sp500': -0.20,      # Stocks vs EUR
            'gold': 0.30         # Gold vs EUR
        }
    
    def analyze(self, signal_data):
        """Analyze intermarket context"""
        price = get_price_with_fallback(symbol, self.name)
    
        if price <= 0:
            return {'decision': 'HOLD', 'reason': 'No price available'}
        
        # Fetch current intermarket data (simulated)
        market_data = self._fetch_market_data()
        
        # Calculate composite risk score
        risk_score = self._calculate_risk_score(market_data)
        
        # Determine market regime
        regime = self._determine_regime(market_data, risk_score)
        
        # Generate vote based on intermarket alignment
        if risk_score > 70:
            vote = "BUY"
            confidence = risk_score
            reasoning = f"🌍 Risk-on regime: {regime['description']}"
        elif risk_score < 30:
            vote = "SELL"
            confidence = 100 - risk_score
            reasoning = f"🌍 Risk-off regime: {regime['description']}"
        else:
            vote = "HOLD"
            confidence = 50
            reasoning = f"🌍 Mixed signals: {regime['description']}"
        
        return {
            'agent': self.name,
            'type': self.agent_type,
            'vote': vote,
            'confidence': confidence,
            'reasoning': reasoning,
            'intermarket_data': market_data,
            'risk_score': risk_score,
            'regime': regime,
            'position_multiplier': 0.5 if risk_score < 40 else 1.0,
            'timestamp': datetime.now().isoformat()
        }
    
    def _fetch_market_data(self):
        """Fetch real-time intermarket data"""
        # In production: fetch from API
        # For demo: simulated data
        return {
            'dxy': {
                'price': random.uniform(100, 106),
                'trend': random.choice(['bullish', 'bearish', 'neutral']),
                'strength': random.randint(20, 80)
            },
            'gold': {
                'price': random.uniform(2300, 2500),
                'trend': random.choice(['bullish', 'bearish']),
                'correlation_active': random.choice([True, False])
            },
            'sp500': {
                'price': random.uniform(4500, 5200),
                'trend': random.choice(['bullish', 'bearish', 'neutral']),
                'vix': random.uniform(12, 28)
            },
            'us_bonds_10y': {
                'yield': random.uniform(3.5, 4.8),
                'trend': random.choice(['rising', 'falling']),
                'inversion': random.choice([True, False])
            }
        }
    
    def _calculate_risk_score(self, data):
        """Calculate overall risk appetite score (0-100)"""
        score = 50
        
        # DXY effect (inverse)
        if data['dxy']['trend'] == 'bearish':
            score += 15  # Dollar weak = risk-on
        elif data['dxy']['trend'] == 'bullish':
            score -= 15  # Dollar strong = risk-off
        
        # Gold effect
        if data['gold']['trend'] == 'bullish' and data['gold']['correlation_active']:
            score += 10
        
        # VIX (fear gauge)
        if data['sp500']['vix'] > 25:
            score -= 20
        elif data['sp500']['vix'] < 15:
            score += 15
        
        # Bond yield curve
        if data['us_bonds_10y']['inversion']:
            score -= 10  # Recession warning
        
        return max(0, min(100, score))
    
    def _determine_regime(self, data, risk_score):
        """Determine current market regime"""
        if risk_score > 70:
            return {
                'regime': 'RISK_ON',
                'description': 'Bullish sentiment, weak dollar, strong equities',
                'action': 'Aggressive positioning allowed'
            }
        elif risk_score < 30:
            return {
                'regime': 'RISK_OFF',
                'description': 'Bearish sentiment, strong dollar, fear elevated',
                'action': 'Reduce position sizes'
            }
        else:
            return {
                'regime': 'MIXED',
                'description': 'Conflicting signals across asset classes',
                'action': 'Use smaller positions'
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
     