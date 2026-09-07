# C:\trading_platform\forex_engine\brokers\eurcad_broker.py

import logging
import numpy as np
import random
from datetime import datetime
from typing import Dict, List, Optional

try:
    from brokers.base_broker import BaseBroker
except ImportError:
    from base_broker import BaseBroker

logger = logging.getLogger(__name__)

class EURCADBroker(BaseBroker):
    """
    EUR/CAD Broker - Volume Analysis + Oil Correlation.
    Strategy: Volume + oil correlation + confluence scoring.
    """
    
    def __init__(self, config: Dict = None):
        if config is None:
            config = {}
        
        super().__init__(
            pair="EURCAD",
            config=config,
            agent_type="Volume Analysis",
            specialization="Volume + Oil Correlation with Confluence Scoring",
            name="EURCAD_Broker"
        )
        
        # ===== EURCAD-SPECIFIC PARAMETERS =====
        self.entry_threshold = config.get('entry_threshold', 1.8)
        self.exit_threshold = config.get('exit_threshold', 0.3)
        self.sl_pips = config.get('sl_pips', 12)
        self.tp_pips = config.get('tp_pips', 25)
        self.volume_multiplier = 0.8
        self.max_position_size = 3
        self.gear_type = 'CROSS'
        
        # ===== HISTORY =====
        self.close_history = []
        self.high_history = []
        self.low_history = []
        self.volume_history = []
        
        # ===== PATTERN DETECTION =====
        self.pattern_info = None
        self.squeeze_detected = False
        self.volume_spike = False
        self.support_level = 0.0
        self.resistance_level = 0.0
        
        # ===== EXTERNAL DATA =====
        self.oil_price = 0.0
        self.oil_change_pct = 0.0
        self.euro_strength = 0.0
        self.cad_strength = 0.0
        self.volume_ratio = 1.0
        self.volume_surge = False
        
        # ===== CONFLUENCE TRACKING =====
        self.confluence_score = 0.0
        self.indicators = {}
        
        # ===== STATE =====
        self.z_score = 0.0
        self.signal = 'HOLD'
        self.confidence = 50.0
        
        # ===== OTHER =====
        self.name = "EURCAD_Broker"
        self.agent_type = "Volume Analysis"
        self.specialization = "Volume + Oil Correlation with Confluence Scoring"
        
        logger.info(f"✅ EURCAD Broker initialized")
        logger.info(f"   Entry: {self.entry_threshold} | Exit: {self.exit_threshold}")
        logger.info(f"   SL: {self.sl_pips}pips | TP: {self.tp_pips}pips")
    
    def analyze(self, signal_data: Dict) -> Dict:
        """
        EURCAD-specific confluence analysis with Volume, Oil, and Euro correlation.
        Uses base class for Z-score and engine alignment.
        """
        try:
            # ===== STEP 1: Get base analysis from parent =====
            base_result = super().analyze(signal_data)
            
            # ===== STEP 2: Get EURCAD-specific data =====
            current_price = signal_data.get('price', signal_data.get('current_price', 0))
            candles = signal_data.get('candles', [])
            
            if not candles:
                return base_result
            
            closes = [c['close'] for c in candles]
            highs = [c['high'] for c in candles]
            lows = [c['low'] for c in candles]
            
            if len(closes) < 20:
                return base_result
            
            # Update history
            self.close_history.extend(closes)
            self.high_history.extend(highs)
            self.low_history.extend(lows)
            
            # ===== STEP 3: Get external data =====
            self.oil_price = signal_data.get('CrudeOIL', 0)
            self.oil_change_pct = signal_data.get('oil_change_pct', 0)
            self.euro_strength = signal_data.get('euro_strength', 0.0)
            self.cad_strength = signal_data.get('cad_strength', 0.0)
            self.volume_ratio = signal_data.get('volume_ratio', 1.0)
            self.volume_surge = signal_data.get('volume_surge', False)
            
            # ===== STEP 4: Calculate indicators =====
            self.indicators = self._calculate_indicators(closes, highs, lows)
            
            # ===== STEP 5: Count signals =====
            bullish_signals = sum(1 for v in self.indicators.values() if v == 'bullish')
            bearish_signals = sum(1 for v in self.indicators.values() if v == 'bearish')
            total_signals = len(self.indicators)
            
            # ===== STEP 6: Calculate confluence score =====
            if total_signals > 0:
                if bullish_signals > bearish_signals:
                    self.confluence_score = (bullish_signals / total_signals) * 100
                else:
                    self.confluence_score = (bearish_signals / total_signals) * 100
            else:
                self.confluence_score = 0
            
            # ===== STEP 7: Generate EURCAD signal =====
            eurcad_result = self._generate_eurcad_signal(
                current_price, bullish_signals, bearish_signals, total_signals
            )
            
            # ===== STEP 8: Apply volume filter =====
            eurcad_result = self._apply_volume_filter(eurcad_result)
            
            # ===== STEP 9: Apply oil correlation =====
            eurcad_result = self._apply_oil_correlation(eurcad_result)
            
            # ===== STEP 10: Override base if needed =====
            base_signal = base_result.get('vote', 'HOLD')
            base_conf = base_result.get('confidence', 0)
            
            if base_signal == 'HOLD' and eurcad_result['vote'] != 'HOLD' and eurcad_result['confidence'] >= 60:
                base_result['vote'] = eurcad_result['vote']
                base_result['confidence'] = eurcad_result['confidence']
                base_result['reasoning'] = f"{eurcad_result['reasoning']} (EURCAD override)"
                base_result['z_score'] = self.z_score
            elif base_signal != 'HOLD' and eurcad_result['vote'] != 'HOLD':
                if eurcad_result['confidence'] > base_conf + 10:
                    base_result['vote'] = eurcad_result['vote']
                    base_result['confidence'] = eurcad_result['confidence']
                    base_result['reasoning'] = f"{eurcad_result['reasoning']} (stronger than base)"
            
            # ===== STEP 11: Add EURCAD-specific data =====
            base_result['oil_price'] = self.oil_price
            base_result['oil_change_pct'] = self.oil_change_pct
            base_result['euro_strength'] = self.euro_strength
            base_result['cad_strength'] = self.cad_strength
            base_result['volume_ratio'] = self.volume_ratio
            base_result['volume_surge'] = self.volume_surge
            base_result['indicators'] = self.indicators
            base_result['confluence_score'] = self.confluence_score
            base_result['bullish_signals'] = bullish_signals
            base_result['bearish_signals'] = bearish_signals
            base_result['total_signals'] = total_signals
            
            return base_result
            
        except Exception as e:
            logger.error(f"EURCAD Broker error: {e}")
            import traceback
            traceback.print_exc()
            return self._hold_response(f"Error: {str(e)}")
    
    def _generate_eurcad_signal(self, price: float, bullish_signals: int, 
                                bearish_signals: int, total_signals: int) -> Dict:
        """
        Generate EURCAD-specific signal based on confluence.
        """
        # Strong confluence (4+ indicators)
        if bullish_signals >= 4:
            return {
                'vote': 'BUY',
                'confidence': min(95, 60 + self.confluence_score * 0.35),
                'reasoning': f"🎯 STRONG CONFLUENCE: {bullish_signals}/{total_signals} indicators align BULLISH"
            }
        
        if bearish_signals >= 4:
            return {
                'vote': 'SELL',
                'confidence': min(95, 60 + self.confluence_score * 0.35),
                'reasoning': f"🎯 STRONG CONFLUENCE: {bearish_signals}/{total_signals} indicators align BEARISH"
            }
        
        # Moderate confluence (3 indicators)
        if bullish_signals >= 3:
            return {
                'vote': 'BUY',
                'confidence': min(85, 55 + self.confluence_score * 0.3),
                'reasoning': f"✅ MODERATE CONFLUENCE: {bullish_signals}/{total_signals} indicators align BULLISH"
            }
        
        if bearish_signals >= 3:
            return {
                'vote': 'SELL',
                'confidence': min(85, 55 + self.confluence_score * 0.3),
                'reasoning': f"✅ MODERATE CONFLUENCE: {bearish_signals}/{total_signals} indicators align BEARISH"
            }
        
        # Low confluence
        return {
            'vote': 'HOLD',
            'confidence': 40,
            'reasoning': f"⚠️ LOW CONFLUENCE: Only {max(bullish_signals, bearish_signals)}/{total_signals} indicators align"
        }
    
    def _calculate_indicators(self, closes: List[float], highs: List[float], lows: List[float]) -> Dict:
        """
        Calculate multiple indicators for confluence.
        """
        indicators = {}
        
        # ===== 1. FIBONACCI =====
        if len(closes) >= 30:
            swing_high = max(highs[-30:])
            swing_low = min(lows[-30:])
            current_price = closes[-1]
            if swing_high > swing_low:
                retracement = (swing_high - current_price) / (swing_high - swing_low)
            else:
                retracement = 0.5
            
            if retracement > 0.618:
                indicators['fibonacci'] = 'bullish'
            elif retracement < 0.382:
                indicators['fibonacci'] = 'bearish'
            else:
                indicators['fibonacci'] = 'neutral'
        else:
            indicators['fibonacci'] = 'neutral'
        
        # ===== 2. ICHIMOKU CLOUD =====
        if len(closes) >= 52:
            tenkan_high = max(highs[-9:])
            tenkan_low = min(lows[-9:])
            tenkan = (tenkan_high + tenkan_low) / 2
            
            kijun_high = max(highs[-26:])
            kijun_low = min(lows[-26:])
            kijun = (kijun_high + kijun_low) / 2
            
            current_price = closes[-1]
            
            if current_price > tenkan and current_price > kijun:
                indicators['ichimoku_cloud'] = 'bullish'
            elif current_price < tenkan and current_price < kijun:
                indicators['ichimoku_cloud'] = 'bearish'
            else:
                indicators['ichimoku_cloud'] = 'neutral'
        else:
            indicators['ichimoku_cloud'] = 'neutral'
        
        # ===== 3. RSI DIVERGENCE =====
        indicators['rsi_divergence'] = self._calculate_rsi_divergence(closes)
        
        # ===== 4. VOLUME PROFILE =====
        if self.volume_ratio > 1.5 and self.volume_surge:
            if len(closes) >= 2:
                if closes[-1] > closes[-2]:
                    indicators['volume_profile'] = 'bullish'
                elif closes[-1] < closes[-2]:
                    indicators['volume_profile'] = 'bearish'
                else:
                    indicators['volume_profile'] = 'neutral'
            else:
                indicators['volume_profile'] = 'neutral'
        elif self.volume_ratio > 1.2:
            indicators['volume_profile'] = 'bullish' if self.volume_ratio > 1.5 else 'neutral'
        else:
            indicators['volume_profile'] = 'neutral'
        
        # ===== 5. MOVING AVERAGE =====
        if len(closes) >= 50:
            ma_20 = sum(closes[-20:]) / 20
            ma_50 = sum(closes[-50:]) / 50
            current_price = closes[-1]
            
            if current_price > ma_20 > ma_50:
                indicators['moving_average'] = 'bullish'
            elif current_price < ma_20 < ma_50:
                indicators['moving_average'] = 'bearish'
            else:
                indicators['moving_average'] = 'neutral'
        else:
            indicators['moving_average'] = 'neutral'
        
        # ===== 6. MACD =====
        indicators['macd'] = self._calculate_macd(closes)
        
        # ===== 7. OIL CORRELATION =====
        if abs(self.oil_change_pct) > 0.5:
            if self.oil_change_pct > 0:
                indicators['oil_correlation'] = 'bearish'
            else:
                indicators['oil_correlation'] = 'bullish'
        else:
            indicators['oil_correlation'] = 'neutral'
        
        # ===== 8. EURO STRENGTH =====
        if self.euro_strength > 0.3:
            indicators['euro_strength'] = 'bullish'
        elif self.euro_strength < -0.3:
            indicators['euro_strength'] = 'bearish'
        else:
            indicators['euro_strength'] = 'neutral'
        
        # ===== 9. CAD STRENGTH =====
        if self.cad_strength > 0.3:
            indicators['cad_strength'] = 'bearish'
        elif self.cad_strength < -0.3:
            indicators['cad_strength'] = 'bullish'
        else:
            indicators['cad_strength'] = 'neutral'
        
        return indicators
    
    def _calculate_rsi_divergence(self, closes: List[float]) -> str:
        """Calculate RSI divergence properly."""
        if len(closes) < 20:
                 return 'neutral'
        
        # Calculate RSI
        gains, losses = [], []
        for i in range(1, len(closes)):
                 diff = closes[i] - closes[i-1]
                 gains.append(max(diff, 0))
                 losses.append(max(-diff, 0))
        
        if len(gains) < 14:
                 return 'neutral'
        
        avg_gain = sum(gains[-14:]) / 14
        avg_loss = sum(losses[-14:]) / 14
        
        if avg_loss == 0:
                 return 'bullish'
        
        rs = avg_gain / avg_loss
        rsi = 100 - (100 / (1 + rs))
        
        # Need at least 5 bars to check divergence
        if len(closes) < 5:
                 return 'neutral'
        
        # Check for Bearish Divergence: Price makes higher high, RSI makes lower high
        if rsi > 60:
                 price_highs = closes[-5:]
                 rsi_values = []
                 for i in range(len(closes)-5, len(closes)):
                          # Simplified RSI for history
                          g = [max(closes[j] - closes[j-1], 0) for j in range(max(1, i-13), i+1)]
                          l = [max(-(closes[j] - closes[j-1]), 0) for j in range(max(1, i-13), i+1)]
                          if len(g) >= 14 and sum(l) > 0:
                                   r = 100 - (100 / (1 + (sum(g[-14:])/14) / (sum(l[-14:])/14)))
                                   rsi_values.append(r)
                 
                 if len(rsi_values) >= 5:
                          # Price higher high but RSI lower high = bearish divergence
                          if max(closes[-5:-2]) < closes[-1] and max(rsi_values[:-1]) > rsi_values[-1]:
                                   return 'bearish'
        
        # Check for Bullish Divergence: Price makes lower low, RSI makes higher low
        if rsi < 40:
                 if len(closes) >= 5:
                          if min(closes[-5:-2]) > closes[-1]:  # Lower low
                                   # Need RSI history - simplified check
                                   if rsi > 30 and closes[-1] < closes[-2]:  # RSI rising from oversold
                                            return 'bullish'
        
        return 'neutral'
    
    def _calculate_macd(self, closes: List[float]) -> str:
        """Calculate MACD signal."""
        if len(closes) < 26:
            return 'neutral'
        
        fast_ema = sum(closes[-12:]) / 12
        slow_ema = sum(closes[-26:]) / 26
        macd_line = fast_ema - slow_ema
        
        if len(closes) >= 35:
            signal_ema = sum(closes[-9:]) / 9
            macd_histogram = macd_line - (signal_ema - slow_ema)
        else:
            macd_histogram = macd_line
        
        if macd_histogram > 0 and macd_line > 0:
            return 'bullish'
        elif macd_histogram < 0 and macd_line < 0:
            return 'bearish'
        else:
            return 'neutral'
    
    def _apply_volume_filter(self, result: Dict) -> Dict:
        """Apply volume filter to signal."""
        if self.volume_ratio < 0.5:
            result['confidence'] = max(30, result['confidence'] - 20)
            result['reasoning'] += " | LOW VOLUME ALERT - reduce confidence"
            if result['confidence'] < 50:
                result['vote'] = 'HOLD'
                result['reasoning'] = "Low volume overrides signal - WAIT"
        elif self.volume_surge and result['vote'] != 'HOLD':
            result['confidence'] = min(95, result['confidence'] + 10)
            result['reasoning'] += " | Volume surge confirms signal"
        return result
    
    def _apply_oil_correlation(self, result: Dict) -> Dict:
        """Apply oil correlation adjustment."""
        if abs(self.oil_change_pct) > 1.0:
            oil_signal = 'bearish' if self.oil_change_pct > 0 else 'bullish'
            
            if result['vote'] == oil_signal:
                result['confidence'] = min(95, result['confidence'] + 10)
                result['reasoning'] += f" | Oil {self.oil_change_pct:.1f}% confirms signal"
            elif result['vote'] != 'HOLD':
                result['confidence'] = max(40, result['confidence'] - 15)
                result['reasoning'] += f" | Oil {self.oil_change_pct:.1f}% contradicts signal"
                if result['confidence'] < 50:
                    result['vote'] = 'HOLD'
                    result['reasoning'] = "Oil correlation overrides confluence"
        return result
    
    def _hold_response(self, reason: str) -> Dict:
        """Generate HOLD response."""
        return {
            'pair': self.pair,
            'vote': 'HOLD',
            'confidence': 50,
            'reasoning': reason,
            'z_score': self.z_score,
            'position': 0,
            'timestamp': datetime.now().isoformat()
        }
    
    def monte_carlo_forecast(self, current_price: float, volatility: float = 0.005, 
                         n_sims: int = 1000, horizon: int = 20) -> Dict:
        """Monte Carlo forecast using actual Ichimoku cloud levels."""
        # Use stored cloud levels or calculate defaults
        cloud_top = getattr(self, 'cloud_top', current_price * 1.01)
        cloud_bottom = getattr(self, 'cloud_bottom', current_price * 0.99)
        
        outcomes = {'above_cloud': 0, 'inside_cloud': 0, 'below_cloud': 0}
        
        for _ in range(n_sims):
               price = current_price
               for _ in range(horizon):
                     price *= (1 + random.gauss(0, volatility))
               
               if price > cloud_top:
                     outcomes['above_cloud'] += 1
               elif price < cloud_bottom:
                     outcomes['below_cloud'] += 1
               else:
                     outcomes['inside_cloud'] += 1
        
        probs = {k: round(v/n_sims*100, 1) for k, v in outcomes.items()}
        
        if probs['above_cloud'] > 60:
               return {'vote': 'BUY', 'confidence': probs['above_cloud'], 'probabilities': probs}
        elif probs['below_cloud'] > 60:
               return {'vote': 'SELL', 'confidence': probs['below_cloud'], 'probabilities': probs}
        return {'vote': 'HOLD', 'confidence': probs['inside_cloud'], 'probabilities': probs}
    def predict(self, signal_data: Dict, market_features: Dict = None) -> tuple:
        result = self.analyze(signal_data)
        return result['vote'], result['confidence']
    
    def get_status(self) -> Dict:
        return {
            'name': self.name,
            'pair': self.pair,
            'signal': self.signal,
            'confidence': self.confidence,
            'z_score': self.z_score,
            'confluence_score': self.confluence_score,
            'oil_price': self.oil_price,
            'oil_change_pct': self.oil_change_pct,
            'euro_strength': self.euro_strength,
            'cad_strength': self.cad_strength,
            'volume_ratio': self.volume_ratio,
            'indicators': self.indicators,
            'timestamp': datetime.now().isoformat()
        }