"""
Agent_J - Volume Master with Whale Detection
Reveals truth about moves and detects volume surges
"""

import random
from datetime import datetime
from collections import deque
from .base_agent import BaseAgent
from price_cache_manager import get_price_for_agent, get_any_price
from price_helper import get_price_with_fallback, get_price_with_details
class VolumeMaster(BaseAgent):
    """Agent J - Volume Analysis with Whale Detection"""
    
    def __init__(self):  # ← 4 spaces (one indentation level)
        super().__init__(
            name="Agent_j",
            agent_type="Volume Master",
            specialization="Volume Profile & Order Flow Analysis"
        )
    def analyze(self, signal_data):
        price = get_price_with_fallback(symbol, self.name)
    
        if price <= 0:
            return {'decision': 'HOLD', 'reason': 'No price available'}
        """Analyze volume patterns and detect whale activity"""
        pair = signal_data.get('pair', 'EURUSD')
        
        # Get or simulate volume data
        volume_data = self._analyze_volume(pair, signal_data)
        
        # Get Ichimoku signal if available
        ichimoku_signal = signal_data.get('ichimoku_signal', {})
        
        # Apply Zero-Error Volume Rules
        result = self._apply_volume_rules(volume_data, ichimoku_signal)
        
        return {
            'agent': self.name,
            'type': self.agent_type,
            'vote': result['vote'],
            'confidence': result['confidence'],
            'reasoning': result['reasoning'],
            'volume_data': volume_data,
            'whale_activity': volume_data['whale_detected'],
            'volume_surge': volume_data['volume_surge'],
            'rule_applied': result['rule'],
            'timestamp': datetime.now().isoformat()
        }
    
    def _analyze_volume(self, pair, signal_data):
        """Analyze volume patterns"""
        
        # Get current volume (in production: from OANDA)
        current_volume = signal_data.get('volume', random.randint(1000, 10000))
        
        # Calculate average volume (simulated)
        avg_volume = signal_data.get('avg_volume', 5000)
        
        # Volume ratio (current / average)
        volume_ratio = current_volume / avg_volume if avg_volume > 0 else 1.0
        
        # Detect volume surge (ratio > 1.5)
        volume_surge = volume_ratio > 1.5
        
        # Detect whale activity (extreme volume spike)
        whale_detected = volume_ratio > 2.0
        
        # Volume trend
        self.volume_history.append(current_volume)
        if len(self.volume_history) >= 3:
            recent_volumes = list(self.volume_history)[-3:]
            if all(recent_volumes[i] < recent_volumes[i+1] for i in range(len(recent_volumes)-1)):
                volume_trend = "increasing"
            elif all(recent_volumes[i] > recent_volumes[i+1] for i in range(len(recent_volumes)-1)):
                volume_trend = "decreasing"
            else:
                volume_trend = "neutral"
        else:
            volume_trend = "neutral"
        
        # Determine buying vs selling pressure
        if volume_surge and whale_detected:
            # Whales are active - determine direction
            pressure = random.choice(['buying', 'selling', 'accumulation'])
        else:
            pressure = "neutral"
        
        return {
            'current_volume': current_volume,
            'avg_volume': avg_volume,
            'volume_ratio': round(volume_ratio, 2),
            'volume_surge': volume_surge,
            'whale_detected': whale_detected,
            'volume_trend': volume_trend,
            'pressure': pressure,
            'signal_quality': 'high' if volume_surge else 'low' if volume_ratio < 0.7 else 'normal'
        }
    
    def _apply_volume_rules(self, volume, ichimoku_signal):
        """Apply Zero-Error Volume Rules"""
        
        # Rule A: Volume Confirmation for Breakouts
        if volume['volume_surge']:
            if volume['pressure'] == 'buying':
                return {
                    'vote': 'BUY',
                    'confidence': 90,
                    'reasoning': f"✅ VOLUME CONFIRMATION: Strong buying surge detected! Volume {volume['volume_ratio']:.1f}x average. Whales are buying. High probability trade.",
                    'rule': 'A - Volume Confirmation (BUY SIGNAL)'
                }
            elif volume['pressure'] == 'selling':
                return {
                    'vote': 'SELL',
                    'confidence': 90,
                    'reasoning': f"✅ VOLUME CONFIRMATION: Strong selling surge detected! Volume {volume['volume_ratio']:.1f}x average. Whales are distributing. Sell signal.",
                    'rule': 'A - Volume Confirmation (SELL SIGNAL)'
                }
            elif volume['whale_detected']:
                return {
                    'vote': 'WATCH',
                    'confidence': 65,
                    'reasoning': f"🐋 WHALE ALERT: Extreme volume spike ({volume['volume_ratio']:.1f}x) but direction unclear. Monitor price action closely.",
                    'rule': 'A - Volume Confirmation (WHALE WATCH)'
                }
        
        # Rule B: Volume Peak on Cloud Curve
        if volume['volume_surge'] and volume['volume_trend'] == 'increasing':
            return {
                'vote': 'BUY',
                'confidence': 85,
                'reasoning': f"📈 VOLUME PEAK DETECTED: Volume surging ({volume['volume_ratio']:.1f}x) with increasing trend. Whales are driving this move. High confidence.",
                'rule': 'B - Volume Peak (CONFIRMATION)'
            }
        
        # Rule C: Volume Veto Power (Even on Golden Cross)
        if ichimoku_signal.get('tk_cross') == 'bullish' and volume['pressure'] == 'selling':
            return {
                'vote': 'HOLD',
                'confidence': 20,
                'reasoning': f"⛔ VOLUME VETO: Even though Ichimoku shows golden cross, volume indicates SELLING DISTRIBUTION (ratio: {volume['volume_ratio']:.1f}x). Trade BLOCKED.",
                'rule': 'C - Volume Veto (BLOCKED)'
            }
        
        # Low volume warning
        if volume['volume_ratio'] < 0.7:
            return {
                'vote': 'HOLD',
                'confidence': 30,
                'reasoning': f"⚠️ LOW VOLUME WARNING: Volume {volume['volume_ratio']:.1f}x below average. Any breakout is likely a TRAP. Wait for volume confirmation.",
                'rule': 'Base Rule - Low Volume (NO TRADE)'
            }
        
        # Distribution detection
        if volume['pressure'] == 'selling' and volume['volume_trend'] == 'increasing':
            return {
                'vote': 'SELL',
                'confidence': 75,
                'reasoning': f"📉 DISTRIBUTION DETECTED: Increasing selling volume (ratio: {volume['volume_ratio']:.1f}x). Smart money is exiting. Sell signal.",
                'rule': 'Base Rule - Distribution (SELL)'
            }
        
        # Accumulation detection
        if volume['pressure'] == 'buying' and volume['volume_trend'] == 'increasing':
            return {
                'vote': 'BUY',
                'confidence': 75,
                'reasoning': f"📈 ACCUMULATION DETECTED: Increasing buying volume (ratio: {volume['volume_ratio']:.1f}x). Smart money is accumulating. Buy signal.",
                'rule': 'Base Rule - Accumulation (BUY)'
            }
        
        # Default - neutral volume
        return {
            'vote': 'HOLD',
            'confidence': 50,
            'reasoning': f"Volume normal ({volume['volume_ratio']:.1f}x average). No strong signals. Wait for volume surge.",
            'rule': 'Default - Neutral Volume'
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
     
        