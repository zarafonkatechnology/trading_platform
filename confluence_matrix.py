"""
Confluence Matrix - Zero Error Trading Logic
Combines Ichimoku and Volume Master signals with strict rules
"""

from datetime import datetime
from enum import Enum

class TradeSignal(Enum):
    STRONG_BUY = "STRONG_BUY"
    BUY = "BUY"
    WATCH = "WATCH"
    HOLD = "HOLD"
    SELL = "SELL"
    STRONG_SELL = "STRONG_SELL"
    BLOCKED = "BLOCKED"

class ConfluenceMatrix:
    """
    Zero-Error Confluence Matrix for Ichimoku + Volume
    """
    
    def __init__(self):
        self.rule_triggered = None
        self.confidence_score = 0
        
    def evaluate(self, ichimoku_signal, volume_signal):
        """
        Evaluate both signals using the Confluence Matrix
        
        Matrix Rules:
        ┌─────────────────────────────────────────────────────────┐
        │ Scenario          │ Ichimoku │ Volume    │ Outcome      │
        ├─────────────────────────────────────────────────────────┤
        │ Strong Breakout   │ Above    │ High Buy  │ STRONG_BUY   │
        │ Trap              │ Above    │ Low/Sell  │ BLOCKED      │
        │ Reversal          │ Below    │ Buy Surge │ WATCH_BOTTOM │
        │ Distribution      │ Bullish  │ Sell Vol  │ BLOCKED      │
        │ Hesitation        │ Inside   │ Any       │ HOLD         │
        │ Golden Cross      │ Bull TK  │ Low Vol   │ BLOCKED      │
        │ Golden Cross      │ Bull TK  │ High Vol  │ BUY          │
        └─────────────────────────────────────────────────────────┘
        """
        
        ichimoku = ichimoku_signal.get('ichimoku_data', {})
        volume = volume_signal.get('volume_data', {})
        
        price_vs_cloud = ichimoku.get('price_vs_cloud', 'inside')
        volume_ratio = volume.get('volume_ratio', 1.0)
        volume_surge = volume.get('volume_surge', False)
        volume_pressure = volume.get('pressure', 'neutral')
        tk_cross = ichimoku.get('tk_cross', 'neutral')
        
        # SCENARIO 1: Price Above Cloud (Breakout)
        if price_vs_cloud == "above":
            if volume_surge and volume_pressure == 'buying':
                self.rule_triggered = "Strong Breakout Confirmed"
                self.confidence_score = 92
                return {
                    'signal': TradeSignal.STRONG_BUY,
                    'action': 'BUY',
                    'confidence': 92,
                    'reasoning': "✅ STRONG BREAKOUT: Price above Kumo with high buying volume. High probability trade.",
                    'risk_level': 'LOW',
                    'suggested_position': 2.0  # 2% of capital
                }
            elif volume_ratio < 0.8 or volume_pressure == 'selling':
                self.rule_triggered = "Fake Breakout - TRAP"
                self.confidence_score = 15
                return {
                    'signal': TradeSignal.BLOCKED,
                    'action': 'HOLD',
                    'confidence': 15,
                    'reasoning': "⚠️ TRAP DETECTED: Price above cloud but volume is low/selling. This is a SCAM. DO NOT TRADE.",
                    'risk_level': 'HIGH',
                    'suggested_position': 0
                }
        
        # SCENARIO 2: Price Below Cloud (Breakdown)
        if price_vs_cloud == "below":
            if volume_surge and volume_pressure == 'selling':
                self.rule_triggered = "Strong Breakdown Confirmed"
                self.confidence_score = 90
                return {
                    'signal': TradeSignal.STRONG_SELL,
                    'action': 'SELL',
                    'confidence': 90,
                    'reasoning': "✅ STRONG BREAKDOWN: Price below Kumo with high selling volume. Strong sell signal.",
                    'risk_level': 'LOW',
                    'suggested_position': -2.0
                }
            elif volume_surge and volume_pressure == 'buying':
                self.rule_triggered = "Reversal Watch - Bottom Detection"
                self.confidence_score = 60
                return {
                    'signal': TradeSignal.WATCH,
                    'action': 'WATCH',
                    'confidence': 60,
                    'reasoning': "🔄 REVERSAL WATCH: Price below cloud but massive buy surge detected. Watch for bottom. Don't sell.",
                    'risk_level': 'MEDIUM',
                    'suggested_position': 0
                }
        
        # SCENARIO 3: Golden Cross with Volume Veto
        if tk_cross == 'bullish':
            if volume_surge and volume_pressure == 'buying':
                self.rule_triggered = "Golden Cross Confirmed"
                self.confidence_score = 85
                return {
                    'signal': TradeSignal.BUY,
                    'action': 'BUY',
                    'confidence': 85,
                    'reasoning': "✅ GOLDEN CROSS: Tenkan above Kijun with volume confirmation. Buy signal.",
                    'risk_level': 'LOW',
                    'suggested_position': 1.5
                }
            elif volume_ratio < 0.9:
                self.rule_triggered = "Golden Cross VETOED"
                self.confidence_score = 20
                return {
                    'signal': TradeSignal.BLOCKED,
                    'action': 'HOLD',
                    'confidence': 20,
                    'reasoning': "⛔ VOLUME VETO: Golden cross detected but volume is low. Trade BLOCKED - likely distribution.",
                    'risk_level': 'HIGH',
                    'suggested_position': 0
                }
        
        # SCENARIO 4: Hesitation - Inside Cloud
        if price_vs_cloud == "inside":
            self.rule_triggered = "Hesitation - Inside Cloud"
            self.confidence_score = 40
            return {
                'signal': TradeSignal.HOLD,
                'action': 'HOLD',
                'confidence': 40,
                'reasoning': "⏸️ HESITATION: Price inside Kumo cloud. Market undecided. Wait for clear breakout with volume.",
                'risk_level': 'MEDIUM',
                'suggested_position': 0
            }
        
        # SCENARIO 5: Cloud Curve Warning
        cloud_direction = ichimoku.get('cloud_direction', 'flat')
        if cloud_direction == 'rising' and not volume_surge:
            self.rule_triggered = "Cloud Curve - Warning Only"
            self.confidence_score = 45
            return {
                'signal': TradeSignal.WATCH,
                'action': 'WATCH',
                'confidence': 45,
                'reasoning': "⚠️ CLOUD CURVE: Cloud turning bullish but volume normal. Treat as warning, not signal.",
                'risk_level': 'MEDIUM',
                'suggested_position': 0
            }
        
        # Default - No clear signal
        return {
            'signal': TradeSignal.HOLD,
            'action': 'HOLD',
            'confidence': 50,
            'reasoning': "Mixed signals. No clear confluence. Wait for better setup.",
            'risk_level': 'MEDIUM',
            'suggested_position': 0
        }
    
    def get_trade_decision_matrix(self):
        """Return the decision matrix for documentation"""
        return {
            'matrix': [
                {'ichimoku': 'Above Cloud', 'volume': 'High Buy', 'outcome': 'STRONG_BUY (92%)'},
                {'ichimoku': 'Above Cloud', 'volume': 'Low/Sell', 'outcome': 'BLOCKED - TRAP'},
                {'ichimoku': 'Below Cloud', 'volume': 'High Sell', 'outcome': 'STRONG_SELL (90%)'},
                {'ichimoku': 'Below Cloud', 'volume': 'Buy Surge', 'outcome': 'WATCH - Bottom'},
                {'ichimoku': 'Inside Cloud', 'volume': 'Any', 'outcome': 'HOLD'},
                {'ichimoku': 'Golden Cross', 'volume': 'High', 'outcome': 'BUY (85%)'},
                {'ichimoku': 'Golden Cross', 'volume': 'Low', 'outcome': 'BLOCKED - VETO'},
                {'ichimoku': 'Cloud Curve', 'volume': 'Normal', 'outcome': 'WARNING Only'}
            ]
        }


# Global instance
confluence = ConfluenceMatrix()
