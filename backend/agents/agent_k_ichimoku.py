"""
Agent_K - Ichimoku Expert with Zero-Error Logic
Determines trend validity and cloud breakout quality
"""
from price_cache_manager import get_price_for_agent, get_any_price
from price_helper import get_price_with_fallback, get_price_with_details
import random
from datetime import datetime
import numpy as np
# from .base_agent import BaseAgent
# NEW (try direct import)
import sys
sys.path.insert(0, 'C:/trading_platform')
from backend.agents.base_agent import BaseAgent
from typing import Dict
class IchimokuExpert(BaseAgent):
    """Agent K - Ichimoku Cloud Analysis with Breakout Confirmation"""
    
    def __init__(self):
        super().__init__(
            name="Agent_K",
            agent_type="Ichimoku Cloud",
            specialization="Ichimoku Cloud & Kumo Breakouts"
        )    
        # Ichimoku components
        self.tenkan_period = 9   # Conversion line
        self.kijun_period = 26   # Base line
        self.senkou_b_period = 52 # Leading span B
    def analyze(self, signal_data):
        price = get_price_with_fallback(symbol, self.name)
    
        if price <= 0:
            return {'decision': 'HOLD', 'reason': 'No price available'}
        """Analyze Ichimoku Cloud signals with volume confirmation rules"""
        pair = signal_data.get('pair', 'EURUSD')
        current_price = signal_data.get('price', 1.0950)
        
        # Calculate Ichimoku components
        ichimoku = self._calculate_ichimoku(pair, current_price)
        
        # Get volume data (from signal or Volume Master)
        volume_data = signal_data.get('volume_data', {})
        volume_ratio = volume_data.get('volume_ratio', 0.8)  # 0.8 = below average, 1.2 = above average
        volume_surge = volume_data.get('volume_surge', False)
        
        # Apply Zero-Error Rules
        result = self._apply_ichimoku_rules(ichimoku, volume_ratio, volume_surge, current_price)
        
        return {
            'agent': self.name,
            'type': self.agent_type,
            'vote': result['vote'],
            'confidence': result['confidence'],
            'reasoning': result['reasoning'],
            'ichimoku_data': ichimoku,
            'volume_condition': {
                'ratio': volume_ratio,
                'surge': volume_surge,
                'status': 'high' if volume_ratio > 1.1 else 'low' if volume_ratio < 0.9 else 'normal'
            },
            'rule_applied': result['rule'],
            'timestamp': datetime.now().isoformat()
        }
    
    def _calculate_ichimoku(self, pair, current_price):
        """Calculate Ichimoku Cloud components"""
        # In production: calculate from real price data
        # For demo: generate realistic values
        
        # Price position relative to cloud
        cloud_top = current_price * (1 + random.uniform(-0.005, 0.005))
        cloud_bottom = current_price * (1 + random.uniform(-0.005, 0.005))
        
        if cloud_top < cloud_bottom:
            cloud_top, cloud_bottom = cloud_bottom, cloud_top
        
        if current_price > cloud_top:
            price_vs_cloud = "above"  # Bullish
        elif current_price < cloud_bottom:
            price_vs_cloud = "below"  # Bearish
        else:
            price_vs_cloud = "inside"  # Hesitation/Wait
        
        # Cloud color (future cloud)
        cloud_color = random.choice(['green', 'red'])
        
        # TK Cross (Tenkan/Kijun)
        tenkan = current_price * (1 + random.uniform(-0.002, 0.002))
        kijun = current_price * (1 + random.uniform(-0.002, 0.002))
        
        if tenkan > kijun:
            tk_cross = "bullish"  # Golden cross
        elif tenkan < kijun:
            tk_cross = "bearish"  # Death cross
        else:
            tk_cross = "neutral"
        
        # Chikou Span (lagging line)
        chikou_position = random.choice(['above', 'below', 'crossing'])
        
        # Cloud direction
        cloud_direction = random.choice(['rising', 'falling', 'flat'])
        
        return {
            'price_vs_cloud': price_vs_cloud,
            'cloud_top': round(cloud_top, 5),
            'cloud_bottom': round(cloud_bottom, 5),
            'cloud_color': cloud_color,
            'cloud_direction': cloud_direction,
            'tk_cross': tk_cross,
            'tenkan': round(tenkan, 5),
            'kijun': round(kijun, 5),
            'chikou_position': chikou_position,
            'current_price': current_price
        }
    
    def _apply_ichimoku_rules(self, ichimoku, volume_ratio, volume_surge, current_price):
        """Apply Zero-Error Rules for Ichimoku + Volume"""
        
        # Rule A: Breakout Confirmation Rule
        if ichimoku['price_vs_cloud'] == "above":
            if volume_ratio > 1.1 or volume_surge:
                # VALID BREAKOUT: Price above cloud with high volume
                return {
                    'vote': 'BUY',
                    'confidence': min(95, 70 + (volume_ratio - 1) * 50),
                    'reasoning': f"✅ VALID BREAKOUT: Price above Kumo peak ({ichimoku['cloud_top']:.5f}) with high volume (ratio: {volume_ratio:.1f}x). Strong buy signal.",
                    'rule': 'A - Breakout Confirmation (VALID)'
                }
            else:
                # TRAP: Price above cloud but low volume
                return {
                    'vote': 'HOLD',
                    'confidence': 30,
                    'reasoning': f"⚠️ FALSE BREAKOUT: Price above cloud but volume is low (ratio: {volume_ratio:.1f}x). This is likely a SCAM. Wait for volume confirmation.",
                    'rule': 'A - Breakout Confirmation (TRAP - NO TRADE)'
                }
        
        # Rule B: Kumo Curve Logic (Cloud Direction Change)
        if ichimoku['cloud_direction'] == "rising" and ichimoku['price_vs_cloud'] == "below":
            if volume_surge:
                # REVERSAL WARNING: Cloud turning bullish with volume surge
                return {
                    'vote': 'WATCH',
                    'confidence': 55,
                    'reasoning': f"🔄 POTENTIAL REVERSAL: Cloud turning bullish while price below. Volume surge detected - whales may be accumulating. Watch for breakout.",
                    'rule': 'B - Kumo Curve (WARNING - Monitor)'
                }
            else:
                # CLOUD CURVE WITHOUT VOLUME - Just a warning
                return {
                    'vote': 'HOLD',
                    'confidence': 40,
                    'reasoning': f"⚠️ CLOUD CURVE SIGNAL: Cloud direction changing but volume normal. Treat as warning, not signal. Wait for volume confirmation.",
                    'rule': 'B - Kumo Curve (WARNING ONLY)'
                }
        
        # Rule C: Tenkan-Kijun Cross with Volume Veto
        if ichimoku['tk_cross'] == "bullish":
            if volume_ratio > 1.0:
                # GOLDEN CROSS WITH VOLUME CONFIRMATION
                return {
                    'vote': 'BUY',
                    'confidence': 85,
                    'reasoning': f"✅ GOLDEN CROSS CONFIRMED: Tenkan crossed above Kijun with volume confirmation (ratio: {volume_ratio:.1f}x). High probability trade.",
                    'rule': 'C - TK Cross (CONFIRMED - Trade)'
                }
            else:
                # GOLDEN CROSS BUT VOLUME SAYS NO - VETO!
                return {
                    'vote': 'HOLD',
                    'confidence': 25,
                    'reasoning': f"❌ VOLUME VETO: Golden cross detected but volume indicates distribution (ratio: {volume_ratio:.1f}x). Trade BLOCKED by Volume Master.",
                    'rule': 'C - TK Cross (VETOED - No Trade)'
                }
        
        # Hesitation State - Price Inside Cloud
        if ichimoku['price_vs_cloud'] == "inside":
            return {
                'vote': 'HOLD',
                'confidence': 50,
                'reasoning': f"⏸️ HESITATION: Price is inside the Kumo cloud ({ichimoku['cloud_bottom']:.5f} - {ichimoku['cloud_top']:.5f}). Market undecided. Wait for clear breakout with volume.",
                'rule': 'Base Rule - Inside Cloud (HOLD)'
            }
        
        # Bearish Signals
        if ichimoku['price_vs_cloud'] == "below":
            if volume_ratio > 1.1:
                return {
                    'vote': 'SELL',
                    'confidence': 85,
                    'reasoning': f"✅ VALID BREAKDOWN: Price below Kumo with high selling volume (ratio: {volume_ratio:.1f}x). Strong sell signal.",
                    'rule': 'A - Breakdown Confirmation (VALID)'
                }
            else:
                return {
                    'vote': 'HOLD',
                    'confidence': 35,
                    'reasoning': f"⚠️ FALSE BREAKDOWN: Price below cloud but low volume. Possible bear trap. Wait for confirmation.",
                    'rule': 'A - Breakdown (TRAP - No Trade)'
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
     
        