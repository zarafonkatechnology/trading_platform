# C:\trading_platform\forex_engine\brokers\eurusd_broker.py

import logging
import numpy as np
import random
from datetime import datetime
from typing import Dict, List, Optional

# Use absolute import from the brokers package
try:
    from brokers.base_broker import BaseBroker
except ImportError:
    # Fallback for direct execution
    from base_broker import BaseBroker

logger = logging.getLogger(__name__)
# C:\trading_platform\forex_engine\brokers\usdjpy_broker.py
import logging
import numpy as np
from typing import Dict, List, Optional
from datetime import datetime
import random

logger = logging.getLogger(__name__)

class USDJPYBroker(BaseBroker):
    """
    USD/JPY Broker - Rate-sensitive with yield spread.
    """
    
    def __init__(self, config: Dict = None):
        if config is None:
            config = {}
        
        super().__init__(
            pair="USDJPY",
            config=config
        )
        
        self.entry_threshold = config.get('entry_threshold', 2.2)
        self.exit_threshold = config.get('exit_threshold', 0.35)
        self.sl_pips = config.get('sl_pips', 15)
        self.tp_pips = config.get('tp_pips', 30)
        self.volume_multiplier = 0.9
        self.max_position_size = 4
        self.gear_type = 'DIRECT'
        self.pip = 0.01
        self.digits = 3
        self.close_history = []
        self.high_history = []
        self.low_history = []
        self.volume_history = []
        self.pattern_info = None
        self.squeeze_detected = False
        self.volume_spike = False
        self.support_level = 0.0
        self.resistance_level = 0.0
        self.name = "USDJPY_Broker"
        self.agent_type = "Rate-sensitive with yield spread"
        self.specialization = "Head & Shoulders + Double Top/Bottom"
        self.us_10y_yield = 0.0
        self.jp_10y_yield = 0.0
        self.yield_spread = 0.0
        
        # Fix the f-string syntax error here
        logger.info(f"✅ USDJPY Broker initialized")
        logger.info(f"   Entry: {self.entry_threshold} | Exit: {self.exit_threshold}")
        logger.info(f"   SL: {self.sl_pips}pips | TP: {self.tp_pips}pips")
    
    def _apply_pair_specific_logic(self, market_data: Dict) -> Dict:
        self.us_10y_yield = market_data.get('us_10y_yield', 4.5)
        self.jp_10y_yield = market_data.get('jp_10y_yield', 0.0)
        self.yield_spread = self.us_10y_yield - self.jp_10y_yield
        
        confidence_boost = 0
        bias = 'NEUTRAL'
        reasoning = 'USDJPY: '
        
        if self.yield_spread > 4.0:
            confidence_boost = 15
            bias = 'BUY'
            reasoning += f'Wide yield spread ({self.yield_spread:.2f}%) → USD strength'
        elif self.yield_spread < 3.5:
            confidence_boost = 15
            bias = 'SELL'
            reasoning += f'Narrow yield spread ({self.yield_spread:.2f}%) → USD weakness'
        else:
            reasoning += f'Neutral yield spread ({self.yield_spread:.2f}%)'
        
        rate_change = market_data.get('us_10y_change', 0)
        if abs(rate_change) > 0.05:
            if rate_change > 0:
                reasoning += f', yields rising {rate_change:.2f}% → USD strength'
                if bias == 'NEUTRAL':
                    bias = 'BUY'
                    confidence_boost = 10
            else:
                reasoning += f', yields falling {rate_change:.2f}% → USD weakness'
                if bias == 'NEUTRAL':
                    bias = 'SELL'
                    confidence_boost = 10
        
        return {
            'bias': bias,
            'confidence_boost': confidence_boost,
            'reasoning': reasoning,
            'us_10y_yield': self.us_10y_yield,
            'jp_10y_yield': self.jp_10y_yield,
            'yield_spread': self.yield_spread
        }
    
    def _get_pair_confidence_boost(self) -> float:
        if self.yield_spread > 4.5:
            return 15.0
        elif self.yield_spread < 3.0:
            return 5.0
        return 10.0
    
    # ============================================================
    # KEEP EXISTING METHODS (analyze, _analyze_volume, etc.)
    # Just add the missing attributes above
    # ============================================================
    
    def analyze(self, signal_data: Dict) -> Dict:
        """
        USDJPY-specific analysis with volume and yield spread.
        """
        try:
            current_price = signal_data.get('price', signal_data.get('current_price', 0))
            candles = signal_data.get('candles', [])
            
            if not candles:
                return self._hold_response("No candle data")
            
            closes = [c['close'] for c in candles]
            highs = [c['high'] for c in candles]
            lows = [c['low'] for c in candles]
            
            if len(closes) < 20:
                return self._hold_response(f"Insufficient data ({len(closes)}/20)")
            
            # Update history
            self.close_history.extend(closes)
            self.high_history.extend(highs)
            self.low_history.extend(lows)
            self.current_price = current_price
            self.price_history.append(current_price)
            
            # ===== YIELD SPREAD =====
            self.us_10y_yield = signal_data.get('us_10y_yield', 4.5)
            self.jp_10y_yield = signal_data.get('jp_10y_yield', 0.0)
            self.yield_spread = self.us_10y_yield - self.jp_10y_yield
            
            # ===== VOLUME ANALYSIS =====
            volume_data = self._analyze_volume(signal_data)
            self.volume_spike = volume_data.get('spike', False)
            self.volume_history.append(volume_data.get('current_volume', 0))
            
            # ===== SQUEEZE DETECTION =====
            squeeze_data = self._detect_squeeze()
            self.squeeze_detected = squeeze_data.get('squeeze', False)
            
            # ===== SUPPORT/RESISTANCE =====
            sr_levels = self._find_support_resistance()
            self.support_level = sr_levels.get('support', 0)
            self.resistance_level = sr_levels.get('resistance', 0)
            
            # ===== GENERATE SIGNAL =====
            action, confidence, reasoning = self._generate_signal(
                current_price, 
                volume_data, 
                squeeze_data, 
                sr_levels
            )
            
            self.signal = action
            self.confidence = confidence
            
            # Calculate Z-score
            if len(self.close_history) > 20:
                mu = np.mean(self.close_history[-20:])
                sigma = np.std(self.close_history[-20:])
                self.z_score = (current_price - mu) / sigma if sigma > 0 else 0
            
            return {
                'pair': self.pair,
                'vote': action,
                'confidence': round(min(95, confidence), 1),
                'reasoning': reasoning,
                'z_score': self.z_score,
                'yield_spread': self.yield_spread,
                'squeeze_detected': self.squeeze_detected,
                'volume_spike': self.volume_spike,
                'support': self.support_level,
                'resistance': self.resistance_level,
                'timestamp': datetime.now().isoformat()
            }
             
        except Exception as e:
            logger.error(f"{self.name} prediction error: {e}")
            return self._hold_response(f"Error: {str(e)}")
    
    def _analyze_volume(self, signal_data: Dict) -> Dict:
        """Analyze volume for spikes and patterns."""
        current_volume = signal_data.get('volume', 1000)
        
        # Keep history
        if not hasattr(self, 'volume_history'):
            self.volume_history = []
        self.volume_history.append(current_volume)
        if len(self.volume_history) > 50:
            self.volume_history.pop(0)
        
        if len(self.volume_history) > 10:
            avg_volume = np.mean(self.volume_history[-10:])
            spike = current_volume > avg_volume * 1.5
            return {
                'current_volume': current_volume,
                'avg_volume': avg_volume,
                'spike': spike,
                'ratio': current_volume / avg_volume if avg_volume > 0 else 1.0
            }
        
        return {'current_volume': current_volume, 'avg_volume': 0, 'spike': False, 'ratio': 1.0}
    
    def _detect_squeeze(self) -> Dict:
        """Detect Bollinger Band squeeze."""
        if len(self.close_history) < 20:
            return {'squeeze': False, 'band_width': 0}
        
        prices = self.close_history[-20:]
        sma = np.mean(prices)
        std = np.std(prices)
        
        if std > 0:
            band_width = std / sma * 100
            squeeze = band_width < 0.5  # Less than 0.5% width
            return {'squeeze': squeeze, 'band_width': band_width}
        
        return {'squeeze': False, 'band_width': 0}
    
    def _find_support_resistance(self) -> Dict:
        """Find support and resistance levels."""
        if len(self.close_history) < 30:
            return {'support': 0, 'resistance': 0}
        
        prices = self.close_history[-30:]
        support = min(prices)
        resistance = max(prices)
        
        return {'support': support, 'resistance': resistance}
    
    def _check_exit_conditions(self, current_price: float, entry_price: float) -> Dict:
        """Check if position should be exited."""
        if self.position == 0:
            return {'exit': False, 'reason': 'No position'}
        
        pnl_pct = (current_price - entry_price) / entry_price * 100
        
        if abs(pnl_pct) > 2.0:
            return {'exit': True, 'reason': f'Take profit 2%'}
        elif pnl_pct < -0.5:
            return {'exit': True, 'reason': f'Stop loss 0.5%'}
        
        return {'exit': False, 'reason': 'Hold'}
    
    def _generate_signal(self, current_price: float, volume_data: Dict, 
                         squeeze_data: Dict, sr_levels: Dict) -> tuple:
        """Generate trading signal based on all indicators."""
        action = 'HOLD'
        confidence = 50
        reasons = []
        
        # Yield spread signal
        if self.yield_spread > 4.0:
            yield_signal = 'BUY'
            yield_confidence = 75
        elif self.yield_spread < 3.5:
            yield_signal = 'SELL'
            yield_confidence = 75
        else:
            yield_signal = 'NEUTRAL'
            yield_confidence = 50
        
        # Squeeze breakout
        if squeeze_data.get('squeeze', False):
            if self.z_score > 1.5:
                squeeze_signal = 'SELL'
                squeeze_confidence = 70
            elif self.z_score < -1.5:
                squeeze_signal = 'BUY'
                squeeze_confidence = 70
            else:
                squeeze_signal = 'NEUTRAL'
                squeeze_confidence = 50
        else:
            squeeze_signal = 'NEUTRAL'
            squeeze_confidence = 50
        
        # Volume confirmation
        if volume_data.get('spike', False):
            volume_confirmation = True
            reasons.append('Volume spike confirms')
        else:
            volume_confirmation = False
        
        # Combine signals
        if yield_signal != 'NEUTRAL' and squeeze_signal != 'NEUTRAL':
            if yield_signal == squeeze_signal:
                action = yield_signal
                confidence = max(yield_confidence, squeeze_confidence) + 10
                reasons.append(f'Yield and squeeze align: {action}')
            else:
                action = yield_signal  # Yield takes precedence
                confidence = yield_confidence * 0.7
                reasons.append(f'Yield: {yield_signal}, Squeeze: {squeeze_signal}')
        elif yield_signal != 'NEUTRAL':
            action = yield_signal
            confidence = yield_confidence
            reasons.append(f'Yield spread signal: {action}')
        elif squeeze_signal != 'NEUTRAL':
            action = squeeze_signal
            confidence = squeeze_confidence
            reasons.append(f'Squeeze breakout signal: {action}')
        else:
            action = 'HOLD'
            confidence = 50
            reasons.append('No clear signal')
        
        # Volume filter
        if volume_confirmation and action != 'HOLD':
            confidence = min(95, confidence + 5)
            reasons.append('Volume confirms entry')
        elif volume_data.get('spike', False) and action == 'HOLD':
            confidence = 45
            reasons.append('Volume spike but no signal')
        
        # Support/Resistance check
        if action == 'BUY' and sr_levels.get('resistance', 0) > 0:
            if current_price > sr_levels['resistance'] * 0.99:
                action = 'HOLD'
                confidence = 40
                reasons.append('Too close to resistance')
        
        if action == 'SELL' and sr_levels.get('support', 0) > 0:
            if current_price < sr_levels['support'] * 1.01:
                action = 'HOLD'
                confidence = 40
                reasons.append('Too close to support')
        
        # Exit check
        exit_check = self._check_exit_conditions(current_price, 0)
        if exit_check['exit']:
            action = 'CLOSE'
            confidence = 85
            reasons.append(exit_check['reason'])
        
        return action, min(95, confidence), '; '.join(reasons)
    
    def monte_carlo_forecast(self, current_price: float, volatility: float = 0.005, 
                            n_sims: int = 1000, horizon: int = 20) -> Dict:
        """Monte Carlo forecast for price direction probability."""
        outcomes = {'above': 0, 'inside': 0, 'below': 0}
        
        for _ in range(n_sims):
            price = current_price
            for _ in range(horizon):
                price *= (1 + random.gauss(0, volatility))
            
            cloud_top = current_price * 1.01
            cloud_bottom = current_price * 0.99
            
            if price > cloud_top:
                outcomes['above'] += 1
            elif price < cloud_bottom:
                outcomes['below'] += 1
            else:
                outcomes['inside'] += 1
        
        probabilities = {k: round(v/n_sims*100, 1) for k, v in outcomes.items()}
        
        if probabilities['above'] > 60:
            vote = 'BUY'
            conf = probabilities['above']
        elif probabilities['below'] > 60:
            vote = 'SELL'
            conf = probabilities['below']
        else:
            vote = 'HOLD'
            conf = probabilities['inside']
        
        return {'vote': vote, 'confidence': conf, 'probabilities': probabilities}
    
    def predict(self, signal_data: Dict, market_features: Dict = None) -> tuple:
        """Predict method for compatibility."""
        result = self.analyze(signal_data)
        return result['vote'], result['confidence']
    
    def get_status(self) -> Dict:
        """Get current status."""
        return {
            'name': self.name,
            'pair': self.pair,
            'agent_type': self.agent_type,
            'signal': self.signal,
            'confidence': self.confidence,
            'z_score': self.z_score,
            'yield_spread': self.yield_spread,
            'squeeze_detected': self.squeeze_detected,
            'volume_spike': self.volume_spike,
            'support': self.support_level,
            'resistance': self.resistance_level,
            'timestamp': datetime.now().isoformat()
        }