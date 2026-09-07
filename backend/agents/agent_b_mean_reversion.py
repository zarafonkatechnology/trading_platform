"""
Agent B: RSI/MACD Divergence Specialist
Confirms pattern validation with oscillator divergence
"""
from price_cache_manager import get_price_for_agent, get_any_price
from price_helper import get_price_with_fallback, get_price_with_details
from backend.agents.base_agent import BaseAgent
import logging

logger = logging.getLogger(__name__)

class AgentBMeanReversion(BaseAgent):
    def __init__(self):
        super().__init__(
            name="Agent_B",
            agent_type="Divergence Specialist",
            specialization="RSI/MACD Divergence Confirmation"
        )
    
    def detect_rsi_divergence(self, prices, rsi_values):
        """
        Detect RSI divergence
        Bullish: Price lower low, RSI higher low
        Bearish: Price higher high, RSI lower high
        """
        if len(prices) < 20 or len(rsi_values) < 20:
            return None
        
        # Find recent peaks and troughs
        price_peaks = []
        price_troughs = []
        rsi_peaks = []
        rsi_troughs = []
        
        for i in range(2, len(prices) - 2):
            # Price peaks
            if prices[i] > prices[i-1] and prices[i] > prices[i+1]:
                price_peaks.append((i, prices[i]))
                rsi_peaks.append((i, rsi_values[i]))
            
            # Price troughs
            if prices[i] < prices[i-1] and prices[i] < prices[i+1]:
                price_troughs.append((i, prices[i]))
                rsi_troughs.append((i, rsi_values[i]))
        
        # Bearish divergence (for Head & Shoulders / Double Top)
        if len(price_peaks) >= 2 and len(rsi_peaks) >= 2:
            last_peak = price_peaks[-1]
            prev_peak = price_peaks[-2]
            last_rsi = rsi_peaks[-1]
            prev_rsi = rsi_peaks[-2]
            
            if last_peak[1] > prev_peak[1] and last_rsi[1] < prev_rsi[1]:
                return {
                    'type': 'bearish',
                    'strength': 0.9,
                    'message': 'Bearish divergence: Price higher high, RSI lower high'
                }
        
        # Bullish divergence (for Double Bottom)
        if len(price_troughs) >= 2 and len(rsi_troughs) >= 2:
            last_trough = price_troughs[-1]
            prev_trough = price_troughs[-2]
            last_rsi = rsi_troughs[-1]
            prev_rsi = rsi_troughs[-2]
            
            if last_trough[1] < prev_trough[1] and last_rsi[1] > prev_rsi[1]:
                return {
                    'type': 'bullish',
                    'strength': 0.9,
                    'message': 'Bullish divergence: Price lower low, RSI higher low'
                }
        
        return None
    
    def detect_macd_divergence(self, prices, macd_histogram):
        """
        Detect MACD divergence
        For Double Top: MACD lower at second peak
        """
        if len(prices) < 20 or len(macd_histogram) < 20:
            return None
        
        # Find price peaks
        price_peaks = []
        macd_at_peaks = []
        
        for i in range(2, len(prices) - 2):
            if prices[i] > prices[i-1] and prices[i] > prices[i+1]:
                price_peaks.append((i, prices[i]))
                macd_at_peaks.append((i, macd_histogram[i]))
        
        if len(price_peaks) >= 2:
            last_peak = price_peaks[-1]
            prev_peak = price_peaks[-2]
            last_macd = macd_at_peaks[-1]
            prev_macd = macd_at_peaks[-2]
            
            # Bearish divergence: price higher, MACD lower
            if last_peak[1] > prev_peak[1] and last_macd[1] < prev_macd[1]:
                return {
                    'type': 'bearish',
                    'strength': 0.85,
                    'message': 'MACD bearish divergence: Price higher, MACD lower'
                }
        
        return None
    
    def predict(self, signal_data, market_features):
        """
        Confirm pattern with divergence
        """
        try:
            asset = signal_data.get('asset_type', 'UNKNOWN')
            candles = market_features.get('candles', [])
            
            if len(candles) < 30:
                return 'HOLD', 50
            
            closes = [c['close'] for c in candles]
            rsi_values = market_features.get('rsi_history', [50] * len(closes))
            macd_histogram = market_features.get('macd_histogram', [0] * len(closes))
            
            # Detect divergences
            rsi_divergence = self.detect_rsi_divergence(closes, rsi_values)
            macd_divergence = self.detect_macd_divergence(closes, macd_histogram)
            
            pattern_info = market_features.get('pattern_info', {})
            pattern_type = pattern_info.get('type', '')
            
            # ============================================
            # CONFIRM PATTERN WITH DIVERGENCE
            # ============================================
            
            action = 'HOLD'
            confidence = 50
            
            # Head & Shoulders / Double Top (Bearish) + Bearish Divergence
            if pattern_type == 'bearish' and rsi_divergence and rsi_divergence['type'] == 'bearish':
                action = 'SELL'
                confidence = 85
                logger.info(f"{self.name}: ✅ Bearish divergence CONFIRMS {pattern_info.get('pattern', 'pattern')}")
            
            elif pattern_type == 'bearish' and macd_divergence and macd_divergence['type'] == 'bearish':
                action = 'SELL'
                confidence = 80
                logger.info(f"{self.name}: ✅ MACD divergence CONFIRMS {pattern_info.get('pattern', 'pattern')}")
            
            # Double Bottom (Bullish) + Bullish Divergence
            elif pattern_type == 'bullish' and rsi_divergence and rsi_divergence['type'] == 'bullish':
                action = 'BUY'
                confidence = 85
                logger.info(f"{self.name}: ✅ Bullish divergence CONFIRMS double bottom")
            
            # No divergence - pattern not confirmed
            elif pattern_type == 'bearish':
                action = 'HOLD'
                confidence = 40
                logger.info(f"{self.name}: ⚠️ Bearish pattern but NO divergence - Weight reduced")
            
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
     
        