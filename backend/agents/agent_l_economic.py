"""
Agent_L - Economic Calendar Master
Red Light/Green Light agent - Supreme Authority
"""
from price_cache_manager import get_price_for_agent, get_any_price
from price_helper import get_price_with_fallback, get_price_with_details
from datetime import datetime, timedelta
import random
from .base_agent import BaseAgent

class EconomicCalendarMaster(BaseAgent):
    """Agent L - Economic Calendar with Supreme Authority"""
    
    def __init__(self):
        super().__init__(
            name="Agent_L",
            agent_type="Economic Calendar",
            specialization="Economic Calendar & Rate Decisions"
        )   
        # High impact events that BLOCK trading
        self.high_impact_events = {
            'NFP': {'name': 'Non-Farm Payrolls', 'impact': 'HIGH', 'block_hours': 2},
            'FOMC': {'name': 'Interest Rate Decision', 'impact': 'HIGH', 'block_hours': 3},
            'CPI': {'name': 'Consumer Price Index', 'impact': 'HIGH', 'block_hours': 2},
            'GDP': {'name': 'GDP Release', 'impact': 'HIGH', 'block_hours': 2},
            'ECB': {'name': 'ECB Rate Decision', 'impact': 'HIGH', 'block_hours': 3},
            'BOE': {'name': 'BOE Rate Decision', 'impact': 'HIGH', 'block_hours': 3},
            'NFP_Rev': {'name': 'NFP Revision', 'impact': 'HIGH', 'block_hours': 1},
            'Fed_Chair': {'name': 'Fed Chair Speech', 'impact': 'MEDIUM', 'block_hours': 1}
        }
    
    def analyze(self, signal_data):
        """Check economic calendar and determine if trading is allowed"""
        price = get_price_with_fallback(symbol, self.name)
    
        if price <= 0:
            return {'decision': 'HOLD', 'reason': 'No price available'}
        # Get upcoming events (simulated)
        upcoming_events = self._get_upcoming_events()
        
        # Check if any high-impact event is near
        block_status = self._check_event_block(upcoming_events)
        
        # Supreme Authority: Economic Calendar is the ULTIMATE authority
        if block_status['is_blocked']:
            return {
                'agent': self.name,
                'type': self.agent_type,
                'vote': 'HOLD',
                'confidence': 5,
                'reasoning': f"🔴 RED LIGHT - SUPREME AUTHORITY: {block_status['reason']}",
                'economic_data': upcoming_events,
                'is_blocked': True,
                'block_reason': block_status['reason'],
                'position_multiplier': 0,  # NO TRADING ALLOWED
                'timestamp': datetime.now().isoformat()
            }
        
        # Check for medium impact events (reduce size)
        if block_status['has_medium_impact']:
            return {
                'agent': self.name,
                'type': self.agent_type,
                'vote': 'HOLD',
                'confidence': 30,
                'reasoning': f"🟡 YELLOW LIGHT: {block_status['medium_reason']} - Reduce position size by 50%",
                'economic_data': upcoming_events,
                'is_blocked': False,
                'position_multiplier': 0.5,
                'timestamp': datetime.now().isoformat()
            }
        
        # Green light - normal trading allowed
        return {
            'agent': self.name,
            'type': self.agent_type,
            'vote': 'BUY',  # Neutral vote, doesn't push direction
            'confidence': 90,
            'reasoning': f"🟢 GREEN LIGHT: No high-impact events in next 60 minutes. Normal trading allowed.",
            'economic_data': upcoming_events,
            'is_blocked': False,
            'position_multiplier': 1.0,
            'timestamp': datetime.now().isoformat()
        }
    
    def _get_upcoming_events(self):
        """Get upcoming economic events"""
        # In production: fetch from economic calendar API
        # For demo: simulate events
        current_hour = datetime.now().hour
        
        # Simulate event schedule
        events = []
        
        # Check if NFP Friday (first Friday of month)
        if datetime.now().weekday() == 4 and datetime.now().day <= 7:
            events.append({
                'name': 'Non-Farm Payrolls',
                'impact': 'HIGH',
                'time_minutes': random.randint(5, 55),
                'description': 'Monthly employment report'
            })
        
        # Random high impact events (10% chance)
        if random.random() < 0.1:
            event_names = ['FOMC Statement', 'CPI Release', 'GDP Release']
            events.append({
                'name': random.choice(event_names),
                'impact': 'HIGH',
                'time_minutes': random.randint(10, 50),
                'description': 'High volatility expected'
            })
        
        return events
    
    def _check_event_block(self, events):
        """Check if events are blocking trading"""
        for event in events:
            if event['impact'] == 'HIGH' and event['time_minutes'] < 60:
                return {
                    'is_blocked': True,
                    'reason': f"{event['name']} in {event['time_minutes']} minutes - NO TRADING ALLOWED",
                    'has_medium_impact': False
                }
        
        # Check for medium impact
        for event in events:
            if event['impact'] == 'MEDIUM' and event['time_minutes'] < 45:
                return {
                    'is_blocked': False,
                    'has_medium_impact': True,
                    'medium_reason': f"{event['name']} in {event['time_minutes']} minutes"
                }
        
        return {
            'is_blocked': False,
            'has_medium_impact': False
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
     
        