"""
Agent A: Trend Follower - Adaptive Moving Average with Zero Error Filter
- Multi-Timeframe Confirmation (9, 21, 50 period MAs)
- Volatility Zone (ATR filter)
- Kaufman Efficiency Ratio (adaptive speed)
"""

from backend.agents.base_agent import BaseAgent
import logging
import numpy as np
from price_cache_manager import get_price_for_agent, get_any_price
from price_helper import get_price_with_fallback, get_price_with_details

import re
logger = logging.getLogger(__name__)

class AgentATrend(BaseAgent):
    def __init__(self):
        super().__init__(
            name="Agent_A",
            agent_type="Trend Follower",
            specialization="Adaptive Moving Average with Zero Error Filter"
        )
    
    def calculate_kaufman_efficiency_ratio(self, prices, period=10):
        """
        Kaufman Efficiency Ratio (ER)
        Measures market efficiency: 1 = strong trend, 0 = random noise
        ER = |Price Change| / Sum of Absolute Price Changes
        """
        if len(prices) < period:
            return 0.5
        
        recent_prices = prices[-period:]
        
        # Total price change (direction)
        total_change = abs(recent_prices[-1] - recent_prices[0])
        
        # Sum of absolute price changes (volatility)
        sum_abs_change = sum(abs(recent_prices[i] - recent_prices[i-1]) 
                            for i in range(1, len(recent_prices)))
        
        if sum_abs_change == 0:
            return 0.5
        
        efficiency_ratio = total_change / sum_abs_change
        return round(efficiency_ratio, 4)
    
    def calculate_adaptive_period(self, efficiency_ratio):
        """
        Smart Speed: Adjust period based on market efficiency
        High efficiency (strong trend) → Fast MA (5-20 period)
        Low efficiency (noise) → Slow MA (50-200 period)
        """
        # ER range: 0 (noise) to 1 (strong trend)
        # Fastest period: 5, Slowest period: 200
        fastest = 5
        slowest = 200
        
        # Linear interpolation
        adaptive_period = slowest - (efficiency_ratio * (slowest - fastest))
        
        # Round to nearest integer and ensure within bounds
        period = int(round(adaptive_period))
        return max(fastest, min(slowest, period))
    
    def calculate_moving_averages(self, prices, periods):
        """Calculate multiple moving averages"""
        mas = {}
        for name, period in periods.items():
            if len(prices) >= period:
                mas[name] = sum(prices[-period:]) / period
            else:
                mas[name] = prices[-1] if prices else 0
        return mas
    
    def calculate_atr(self, highs, lows, closes, period=14):
        """Calculate Average True Range for volatility zone"""
        if len(closes) < period + 1:
            return 0
        
        tr_values = []
        for i in range(1, len(closes)):
            hl = highs[i] - lows[i]
            hc = abs(highs[i] - closes[i-1])
            lc = abs(lows[i] - closes[i-1])
            tr = max(hl, hc, lc)
            tr_values.append(tr)
        
        return np.mean(tr_values[-period:]) if tr_values else 0
    
    def predict(self, signal_data, market_features):
        """
        Adaptive Moving Average with Zero Error Filter:
        1. Multi-Timeframe Confirmation (9, 21, 50)
        2. Volatility Zone (ATR filter)
        3. Kaufman Efficiency Ratio (adaptive speed)
        """
        try:
            asset = signal_data.get('asset_type', 'UNKNOWN')
            current_price = signal_data.get('current_price', 0)
            
            # Get candlestick data
            candles = market_features.get('candles', [])
            if not candles:
                return 'HOLD', 50
            
            closes = [c['close'] for c in candles]
            highs = [c['high'] for c in candles]
            lows = [c['low'] for c in candles]
            
            if len(closes) < 50:
                return 'HOLD', 50
            
            # ============================================
            # STEP 1: Kaufman Efficiency Ratio
            # ============================================
            efficiency_ratio = self.calculate_kaufman_efficiency_ratio(closes, period=20)
            adaptive_period = self.calculate_adaptive_period(efficiency_ratio)
            
            # ============================================
            # STEP 2: Multi-Timeframe Moving Averages
            # ============================================
            ma_periods = {
                'fast': adaptive_period,
                'medium': 21,
                'slow': 50
            }
            mas = self.calculate_moving_averages(closes, ma_periods)
            
            # Check alignment (all MAs in same direction)
            ma_fast = mas.get('fast', current_price)
            ma_medium = mas.get('medium', current_price)
            ma_slow = mas.get('slow', current_price)
            
            # Determine trend direction
            bullish_alignment = ma_fast > ma_medium > ma_slow
            bearish_alignment = ma_fast < ma_medium < ma_slow
            
            # ============================================
            # STEP 3: Volatility Zone (ATR Filter)
            # ============================================
            atr = self.calculate_atr(highs, lows, closes, period=14)
            atr_zone = atr * 1.5  # 1.5x ATR zone
            
            # Check if price is outside ATR zone
            price_above_zone = current_price > ma_slow + atr_zone
            price_below_zone = current_price < ma_slow - atr_zone
            
            # Need 2 consecutive candles outside zone for confirmation
            consecutive_outside = market_features.get('consecutive_outside', 0)
            
            # ============================================
            # STEP 4: Zero Error Filter
            # ============================================
            
            action = 'HOLD'
            confidence = 50
            reasons = []
            
            # Check market efficiency
            if efficiency_ratio > 0.6:
                # HIGH EFFICIENCY - Strong trend, use fast MA
                adaptive_status = f"Fast mode (ER={efficiency_ratio:.2f}, period={adaptive_period})"
                
                if bullish_alignment and price_above_zone:
                    consecutive_outside += 1
                    if consecutive_outside >= 2:
                        action = 'BUY'
                        confidence = 85
                        reasons = [
                            f"Strong uptrend (ER={efficiency_ratio:.2f})",
                            f"Multi-MA alignment: {ma_fast:.0f} > {ma_medium:.0f} > {ma_slow:.0f}",
                            f"Price above ATR zone for {consecutive_outside} candles"
                        ]
                    else:
                        action = 'HOLD'
                        confidence = 60
                        reasons = [f"Waiting for 2nd candle confirmation ({consecutive_outside}/2)"]
                
                elif bearish_alignment and price_below_zone:
                    consecutive_outside += 1
                    if consecutive_outside >= 2:
                        action = 'SELL'
                        confidence = 85
                        reasons = [
                            f"Strong downtrend (ER={efficiency_ratio:.2f})",
                            f"Multi-MA alignment: {ma_fast:.0f} < {ma_medium:.0f} < {ma_slow:.0f}",
                            f"Price below ATR zone for {consecutive_outside} candles"
                        ]
                    else:
                        action = 'HOLD'
                        confidence = 60
                        reasons = [f"Waiting for 2nd candle confirmation ({consecutive_outside}/2)"]
                else:
                    consecutive_outside = 0
                    action = 'HOLD'
                    confidence = 55
                    reasons = ["MAs aligned but price within ATR zone - NOISE FILTERED"]
            
            elif efficiency_ratio < 0.3:
                # LOW EFFICIENCY - Ranging/Noisy market, use slow MA
                adaptive_status = f"Slow mode (ER={efficiency_ratio:.2f}, period={adaptive_period})"
                action = 'HOLD'
                confidence = 55
                reasons = [f"Low efficiency market (ER={efficiency_ratio:.2f}) - HOLD position"]
            
            else:
                # MEDIUM EFFICIENCY - Normal market
                adaptive_status = f"Normal mode (ER={efficiency_ratio:.2f}, period={adaptive_period})"
                
                if bullish_alignment and current_price > ma_slow:
                    action = 'BUY'
                    confidence = 70
                    reasons = ["Moderate uptrend with MA confirmation"]
                elif bearish_alignment and current_price < ma_slow:
                    action = 'SELL'
                    confidence = 70
                    reasons = ["Moderate downtrend with MA confirmation"]
                else:
                    action = 'HOLD'
                    confidence = 55
                    reasons = ["MAs overlapping - NOISE, holding position"]
            
            # Store consecutive_outside for next iteration
            market_features['consecutive_outside'] = consecutive_outside
            
            # Log decision
            logger.info(f"{self.name}: {action} on {asset} - {adaptive_status}")
            logger.info(f"   Reasons: {', '.join(reasons)}")
            logger.info(f"   MAs: Fast={ma_fast:.0f}, Medium={ma_medium:.0f}, Slow={ma_slow:.0f}")
            logger.info(f"   ATR Zone: ±${atr_zone:.2f}, Price: ${current_price:.2f}")
            
            return action, min(95, confidence)
             
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
    def respond_to_query(self, user_query: str) -> str:
        """Respond to user queries about any instrument price"""
        query_lower = user_query.lower()
        
        # Pattern to detect price queries
        price_patterns = [
            r'(?:what is|price of|current price|how much is|value of)\s+(\w+)',
            r'(\w+)\s+(?:price|value|trading at|worth)',
            r'what\'s\s+(\w+)\s+(?:price|at|worth)',
        ]
        
        extracted_symbol = None
        
        for pattern in price_patterns:
            match = re.search(pattern, query_lower)
            if match:
                extracted_symbol = match.group(1)
                break
        
        # Also check for direct symbol mentions
        symbols_to_check = ['gold', 'silver', 'nasdaq', 'nasdaq100', 's&p', 'dow', 
                           'oil', 'brent', 'eurusd', 'gbpusd', 'usdjpy']
        
        for symbol in symbols_to_check:
            if symbol in query_lower:
                extracted_symbol = symbol
                break
        
        if extracted_symbol:
            # Get price response
            return get_price_for_agent(self.name, extracted_symbol)
        else:
            return f"{self.name}: I can help you with prices! Just ask me like 'What is the price of gold?' or 'How much is silver?'"
    
    def analyze_signal(self, signal_data=None):
        """Analyze trend using real prices"""
        price = get_price_with_fallback(symbol, self.name)
    
        if price <= 0:
            return {'decision': 'HOLD', 'reason': 'No price available'}
        # Get price for analysis
        gold_price = get_any_price('gold')
        
        if gold_price:
            current_price = gold_price['mid']
            return {
                'agent': self.name,
                'vote': 'HOLD',
                'confidence': 70,
                'reasoning': f"Current {gold_price.get('display_name', 'Gold')} price: ${current_price:.2f} (from {gold_price.get('source', 'CACHE')})",
                'current_price': current_price
            }
        
        return {
            'agent': self.name,
            'vote': 'HOLD',
            'confidence': 50,
            'reasoning': "Waiting for price data..."
        }
