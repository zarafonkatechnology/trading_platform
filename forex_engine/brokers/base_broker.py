# C:\trading_platform\forex_engine\brokers\base_broker.py

import logging
import numpy as np
from collections import deque
from typing import Dict, Optional
from datetime import datetime

logger = logging.getLogger(__name__)

class BaseBroker:
    """
    Base class for all currency pair brokers.
    Contains shared logic: Z-score, persistence, engine alignment.
    """
    
    def __init__(self, pair: str, config: Dict = None, **kwargs):
        """
        Initialize BaseBroker.
        
        Args:
            pair: Currency pair (e.g., 'EURUSD')
            config: Configuration dictionary
            **kwargs: Additional arguments (agent_type, specialization, etc.)
        """
        self.pair = pair
        self.config = config or {}
        self._preserved_z = None  # ← ADD THIS

        # Store additional attributes from kwargs
        self.agent_type = kwargs.get('agent_type', 'Base Broker')
        self.specialization = kwargs.get('specialization', 'General')
        self.name = kwargs.get('name', f"{pair}_Broker")
        
        # ===== SHARED PARAMETERS =====
        self.beta = config.get('beta', 1.0)
        self.gear_ratio = config.get('gear_ratio', 1.0)
        self.gear_type = config.get('gear_type', 'INVERSE')
        
        # ===== THRESHOLDS =====
        self.entry_threshold = config.get('entry_threshold', 1.2)
        self.exit_threshold = config.get('exit_threshold', 0.3)
        self.emergency_threshold = config.get('emergency_threshold', 3.0)
        
        # ===== RISK MANAGEMENT =====
        self.sl_pips = config.get('sl_pips', 15)
        self.tp_pips = config.get('tp_pips', 30)
        self.volume_multiplier = config.get('volume_multiplier', 1.0)
        self.max_position_size = config.get('max_position_size', 3)
        self.volume = config.get('volume', 0.03)
        self.pip = config.get('pip', 0.0001)
        self.digits = config.get('digits', 5)
        
        # ===== VOLATILITY ADJUSTMENTS =====
        self.volatility_multiplier = config.get('volatility_multiplier', 1.0)
        self.atr_period = config.get('atr_period', 14)
        self.atr_multiplier = config.get('atr_multiplier', 1.5)
        
        # ===== HISTORY =====
        max_history = config.get('max_history', 200)
        self.price_history = deque(maxlen=max_history)
        self.spread_history = deque(maxlen=min(max_history, 60))
        self.volatility_history = deque(maxlen=min(max_history, 50))
        self.close_history = deque(maxlen=max_history)    # ← CRITICAL: For Z-score
        self.high_history = deque(maxlen=max_history)     # ← CRITICAL: For future use
        self.low_history = deque(maxlen=max_history)      # ← CRITICAL: For future use
        
        # ===== STATE =====
        self.z_score = 0.0
        self.z_score_ema = 0.0
        self.persistence = 0
        self.signal = 'HOLD'
        self.confidence = 0.0
        self.position = 0
        self.current_price = 0.0
        self.mu = 0.0
        self.sigma = 0.0
        self.samples = 0
        
        # ===== PERFORMANCE TRACKING =====
        self.performance = {
            'trades': 0,
            'wins': 0,
            'losses': 0,
            'win_rate': 0.0,
            'avg_confidence': 0.0,
            'total_pnl': 0.0,
            'sharpe_ratio': 0.0,
            'max_drawdown': 0.0
        }
        
        # ===== CORRELATION TRACKING =====
        self.correlation_history = deque(maxlen=50)
        self.correlation_threshold = config.get('correlation_threshold', 0.7)
        
        # ===== EXTERNAL DATA CACHE =====
        self.external_data = {}
        
        logger.info(f"   ✅ BaseBroker: {pair} initialized")
        logger.info(f"      Entry: {self.entry_threshold} | Exit: {self.exit_threshold}")
        logger.info(f"      SL: {self.sl_pips}pips | TP: {self.tp_pips}pips")
        self.config = config or {}  # ← FIX: Use empty dict if None

    # ============================================================
    # 1. MAIN ANALYSIS METHOD
    # ============================================================
    
    
    
    def analyze(self, market_data: Dict) -> Dict:
        """Main analysis method - FIXED to preserve Z-score."""
        
        # ===== CRITICAL: PRESERVE Z-SCORE BEFORE ANYTHING =====
        preserved_z = getattr(self, '_preserved_z', None)
        if preserved_z is None:
               preserved_z = getattr(self, 'z_score', 0)
               self._preserved_z = preserved_z
        
        # 1. Get price
        price = market_data.get(self.pair, 0)
        if price <= 0:
               return self._hold_response("No price data")
        
        self.current_price = price
        self.price_history.append(price)
        self.close_history.append(price)
        
        # 2. Use preserved Z-score
        if preserved_z != 0:
               z_score = preserved_z
               mu = getattr(self, 'mu', 0)
               sigma = getattr(self, 'sigma', 0)
               samples = len(self.close_history)
        else:
               # Fallback: calculate from close_history
               if len(self.close_history) >= 10:
                     values = list(self.close_history)
                     mu = sum(values) / len(values)
                     variance = sum((x - mu) ** 2 for x in values) / len(values)
                     sigma = variance ** 0.5 if variance > 0 else 0.0001
                     z_score = (values[-1] - mu) / sigma if sigma > 0 else 0
                     samples = len(values)
               else:
                     z_score = 0
                     mu = 0
                     sigma = 0
                     samples = 0
        
        # Store in self
        self.z_score = z_score
        self.mu = mu
        self.sigma = sigma
        self.samples = samples
        self.z_score_ema = z_score
        
        # 3. Update persistence
        if abs(z_score) >= self.entry_threshold:
               self.persistence += 1
        else:
               self.persistence = 0
        
        # 4. Get engine alignment
        engine_alignment = self._check_engine_alignment(market_data)
        
        # 5. Generate signal
        signal_result = self._generate_signal(
               price, 
               0.01,
               engine_alignment,
               {}
        )
        
        # 6. Return result with Z-score
        return {
               'pair': self.pair,
               'vote': signal_result['signal'],
               'confidence': signal_result['confidence'],
               'reasoning': signal_result['reasoning'],
               'z_score': z_score,
               'z_score_ema': self.z_score_ema,
               'persistence': self.persistence,
               'volatility': 0.01,
               'samples': len(self.close_history),
               'position': self.position,
               'price': price,
               'mu': mu,
               'sigma': sigma,
               'entry_threshold': self.entry_threshold,
               'exit_threshold': self.exit_threshold,
               'sl_pips': self.sl_pips,
               'tp_pips': self.tp_pips,
               'timestamp': datetime.now().isoformat()
        }
        
    # ============================================================
    # 2. RISK MANAGEMENT
    # ============================================================
    
    def calculate_position_size(self, confidence: float, volatility: float, account_balance: float) -> float:
        """
        Calculate position size based on pair-specific risk parameters.
        """
        # Base size from config
        base_size = self.config.get('volume', 0.03) * self.volume_multiplier
        
        # Confidence adjustment
        confidence_factor = confidence / 100.0
        
        # Volatility adjustment (higher volatility = smaller position)
        volatility_factor = 1.0 / (1.0 + volatility * 50)
        
        # Risk per trade (2% of account)
        risk_per_trade = account_balance * 0.02
        
        # Calculate position size
        position_size = base_size * confidence_factor * volatility_factor
        
        # Apply limits
        position_size = max(0.01, min(self.max_position_size, position_size))
        
        return round(position_size, 2)
    
    def calculate_sl_tp(self, price: float, direction: str, volatility: float) -> Dict:
        """
        Calculate Stop Loss and Take Profit based on pair-specific parameters.
        """
        pip = self.config.get('pip', 0.0001)
        digits = self.config.get('digits', 5)
        
        # Adjust SL/TP based on volatility
        volatility_adjustment = 1.0 + (volatility * 100)
        
        # Calculate pips
        sl_pips_adj = self.sl_pips * volatility_adjustment * 0.8
        tp_pips_adj = self.tp_pips * volatility_adjustment * 0.8
        
        # Ensure minimum distances
        min_sl_pips = 10
        min_tp_pips = 20
        
        sl_pips = max(min_sl_pips, sl_pips_adj)
        tp_pips = max(min_tp_pips, tp_pips_adj)
        
        # Calculate SL and TP
        if direction == 'BUY':
            sl = price - (sl_pips * pip)
            tp = price + (tp_pips * pip)
        else:  # SELL
            sl = price + (sl_pips * pip)
            tp = price - (tp_pips * pip)
        
        return {
            'sl': round(sl, digits),
            'tp': round(tp, digits),
            'sl_pips': round(sl_pips, 1),
            'tp_pips': round(tp_pips, 1)
        }
    
    # ============================================================
    # 3. CORRELATION AWARENESS
    # ============================================================
    
    def _check_correlation(self, market_data: Dict) -> Dict:
        """
        Check correlation with other pairs.
        Cross pairs need to consider both underlying currencies.
        """
        if self.gear_type == 'CROSS':
            # For cross pairs, check both underlying currencies
            underlying1 = self.pair[:3]  # e.g., EUR from EURGBP
            underlying2 = self.pair[3:]  # e.g., GBP from EURGBP
            
            # Get their positions against USD
            pair1_price = market_data.get(f'{underlying1}USD', 0)
            pair2_price = market_data.get(f'{underlying2}USD', 0)
            
            if pair1_price > 0 and pair2_price > 0:
                # Calculate relative strength
                rel_strength = pair1_price / pair2_price
                
                # Check if correlation is breaking
                if self.correlation_history:
                    avg_corr = np.mean(list(self.correlation_history)[-20:])
                    current_corr = rel_strength
                    
                    if abs(current_corr - avg_corr) > 0.05:
                        return {
                            'correlation_break': True,
                            'deviation': current_corr - avg_corr,
                            'message': f'Correlation break: {self.pair} deviation {current_corr-avg_corr:.3f}'
                        }
        
        return {'correlation_break': False, 'deviation': 0, 'message': 'Normal correlation'}
    
    # ============================================================
    # 4. EXTERNAL DATA INTEGRATION
    # ============================================================
    
    def _update_external_data(self, market_data: Dict):
        """
        Update external data cache.
        Override in child classes for pair-specific external data.
        """
        # Base implementation - store all data
        for key, value in market_data.items():
            if key not in ['candles', 'prices']:
                self.external_data[key] = value
    
    def get_external_data(self, key: str, default=None):
        """Get external data for this pair."""
        return self.external_data.get(key, default)
    
    # ============================================================
    # 5. ADAPTIVE THRESHOLDS
    # ============================================================
    
    def _calculate_adaptive_threshold(self, volatility: float, market_regime: str) -> float:
        """
        Calculate adaptive entry threshold based on volatility and market regime.
        Ranging pairs need lower thresholds, trending pairs need higher.
        """
        base_threshold = self.entry_threshold
        
        # Adjust for volatility
        if volatility > 0.02:  # High volatility
            volatility_adjustment = 1.2
        elif volatility < 0.005:  # Low volatility
            volatility_adjustment = 0.8
        else:
            volatility_adjustment = 1.0
        
        # Adjust for market regime
        if market_regime == 'RANGING':
            regime_adjustment = 0.8  # Lower threshold for ranging
        elif market_regime == 'TRENDING':
            regime_adjustment = 1.1  # Higher threshold for trending
        else:
            regime_adjustment = 1.0
        
        # Calculate adaptive threshold
        adaptive_threshold = base_threshold * volatility_adjustment * regime_adjustment
        
        # Ensure within bounds
        return max(1.2, min(3.0, adaptive_threshold))
    
    # ============================================================
    # 6. CONFIDENCE SCORING
    # ============================================================
    
    def _calculate_confidence(self, signal: str, z_score: float, volatility: float, 
                            persistence: int, alignment: Dict) -> float:
        """
        Calculate confidence score based on multiple factors.
        Each pair's confidence reflects its predictability.
        """
        # Base confidence from Z-score magnitude
        if signal == 'BUY':
            z_confidence = min(90, 50 + abs(z_score) * 15)
        elif signal == 'SELL':
            z_confidence = min(90, 50 + abs(z_score) * 15)
        else:
            z_confidence = 50
        
        # Persistence boost
        persistence_boost = min(10, persistence * 3)
        
        # Volatility penalty (higher volatility = lower confidence)
        volatility_penalty = max(0, (volatility - 0.005) * 100)
        
        # Engine alignment boost
        alignment_boost = 10 if alignment.get('aligned', False) else 0
        
        # Pair-specific confidence (overridden by child)
        pair_confidence = self._get_pair_confidence_boost()
        
        # Calculate final confidence
        confidence = (
            z_confidence * 0.4 +
            persistence_boost * 0.2 +
            alignment_boost * 0.2 +
            pair_confidence * 0.2
        ) - volatility_penalty
        
        # Ensure bounds
        return max(30, min(95, confidence))
    
    def _get_pair_confidence_boost(self) -> float:
        """
        Override this in child classes for pair-specific confidence boost.
        """
        return 0.0
    
    # ============================================================
    # 7. HELPER METHODS
    # ============================================================
    
    def _calculate_spread(self, market_data: Dict) -> float:
        """
        Calculate spread for this pair.
        If no spread data, use price history to estimate spread.
        """
        # Try to get actual spread from market data
        spread = market_data.get(f'{self.pair}_spread', 0)
        if spread > 0:
            return spread
        
        # Try to calculate from bid/ask
        bid = market_data.get(f'{self.pair}_bid', 0)
        ask = market_data.get(f'{self.pair}_ask', 0)
        if bid > 0 and ask > 0:
            return ask - bid
        
        # Use estimated spread (0.0002 = 2 pips for EURUSD)
        estimated_spread = self.current_price * 0.0002
        
        # If we have price history, calculate spread from price movement
        if len(self.price_history) >= 2:
            # Spread estimate based on recent volatility
            recent = list(self.price_history)[-20:] if len(self.price_history) >= 20 else list(self.price_history)
            if len(recent) >= 2:
                volatility = np.std(recent) if len(recent) > 1 else 0.0001
                # Spread is typically 10-20% of volatility
                estimated_spread = max(estimated_spread, volatility * 0.15)
        
        return estimated_spread
    
    def _calculate_z_score(self) -> Dict:
        """
        Calculate Z-score from close_history (price history).
        This is more reliable than spread_history.
        """
        if len(self.close_history) < 10:
            return {'z_score': self.z_score if hasattr(self, 'z_score') else 0.0, 
                    'mu': 0.0, 'sigma': 0.0, 'samples': len(self.close_history)}
        
        values = list(self.close_history)
        mu = sum(values) / len(values)
        variance = sum((x - mu) ** 2 for x in values) / len(values)
        sigma = variance ** 0.5 if variance > 0 else 0.0001
        
        if sigma > 0:
            z_score = (values[-1] - mu) / sigma
        else:
            z_score = 0.0
        
        return {'z_score': z_score, 'mu': mu, 'sigma': sigma, 'samples': len(values)}
    
    def _calculate_atr(self, market_data: Dict) -> float:
        """Calculate Average True Range."""
        candles = market_data.get('candles', [])
        if not candles or len(candles) < self.atr_period + 1:
            return 0.01
        
        tr_values = []
        for i in range(1, min(len(candles), self.atr_period + 1)):
            high = candles[i]['high']
            low = candles[i]['low']
            prev_close = candles[i-1]['close']
            tr = max(high - low, abs(high - prev_close), abs(low - prev_close))
            tr_values.append(tr)
        
        if tr_values:
            return sum(tr_values) / len(tr_values)
        return 0.01
    
    def _check_engine_alignment(self, market_data: Dict) -> Dict:
        """Check if signal aligns with Dollar Engine prediction."""
        engine_state = market_data.get('engine_state', {})
        engine_direction = engine_state.get('engine_direction', 'NEUTRAL')
        engine_speed = engine_state.get('engine_speed', 0)
        
        if self.gear_type == 'INVERSE':
            # EUR/USD type: SELL when engine says DOWN
            if self.z_score_ema > self.entry_threshold and engine_direction == 'FORWARD':
                return {'aligned': True, 'direction': 'FORWARD', 'confidence_boost': 10}
            elif self.z_score_ema < -self.entry_threshold and engine_direction == 'BACKWARD':
                return {'aligned': True, 'direction': 'BACKWARD', 'confidence_boost': 10}
            elif engine_direction == 'NEUTRAL':
                return {'aligned': True, 'direction': 'NEUTRAL', 'confidence_boost': 0}
            else:
                return {'aligned': False, 'direction': engine_direction, 'confidence_boost': -10}
        
        elif self.gear_type == 'DIRECT':
            # USD/JPY type: BUY when engine says FORWARD
            if self.z_score_ema > self.entry_threshold and engine_direction == 'FORWARD':
                return {'aligned': True, 'direction': 'FORWARD', 'confidence_boost': 10}
            elif self.z_score_ema < -self.entry_threshold and engine_direction == 'BACKWARD':
                return {'aligned': True, 'direction': 'BACKWARD', 'confidence_boost': 10}
            elif engine_direction == 'NEUTRAL':
                return {'aligned': True, 'direction': 'NEUTRAL', 'confidence_boost': 0}
            else:
                return {'aligned': False, 'direction': engine_direction, 'confidence_boost': -10}
        
        return {'aligned': True, 'direction': 'NEUTRAL', 'confidence_boost': 0}
    
    def _apply_pair_specific_logic(self, market_data: Dict) -> Dict:
        """
        Override this in child classes for pair-specific logic.
        """
        return {'bias': 'NEUTRAL', 'confidence_boost': 0, 'reasoning': 'No pair-specific logic'}
    
    def _generate_signal(self, price: float, volatility: float, 
                     alignment: Dict, pair_specific: Dict) -> Dict:
        """Generate final signal."""
        z = self.z_score
        threshold = self.entry_threshold
        
        # ===== DEBUG: Print what's happening =====
        import sys
        print(f"🔍 {self.pair}: z={z:.2f}, threshold={threshold}, persistence={self.persistence}", file=sys.stderr)
        
        # ===== TEMPORARILY REMOVE PERSISTENCE CHECK =====
        # if self.persistence < 2:
        #          print(f"   ⏸️ {self.pair}: BLOCKED by persistence", file=sys.stderr)
        #          return {'signal': 'HOLD', 'confidence': 50, 'reasoning': 'No persistence'}
        
        # Get adaptive threshold
        adaptive_threshold = self.entry_threshold
        
        # Generate signal based on Z-score
        signal = 'HOLD'
        confidence = 50
        reasoning = f'Normal (Z={z:.2f})'
        
        if z > adaptive_threshold:
              if alignment.get('aligned', True):
                      signal = 'SELL'
                      confidence = self._calculate_confidence('SELL', z, volatility, 
                                                                                       self.persistence, alignment)
                      reasoning = f'Overextended (Z={z:.2f})'
                      print(f"   ✅ {self.pair}: SELL signal generated!", file=sys.stderr)
              else:
                      signal = 'HOLD'
                      confidence = 40
                      reasoning = f'Overextended but misaligned (Z={z:.2f})'
        
        elif z < -adaptive_threshold:
              if alignment.get('aligned', True):
                      signal = 'BUY'
                      confidence = self._calculate_confidence('BUY', z, volatility,
                                                                                       self.persistence, alignment)
                      reasoning = f'Compressed (Z={z:.2f})'
                      print(f"   ✅ {self.pair}: BUY signal generated!", file=sys.stderr)
              else:
                      signal = 'HOLD'
                      confidence = 40
                      reasoning = f'Compressed but misaligned (Z={z:.2f})'
        
        print(f"   → {self.pair}: signal={signal}, confidence={confidence}", file=sys.stderr)
        
        return {
              'signal': signal,
              'confidence': min(95, max(30, confidence)),
              'reasoning': reasoning
        }
    def _hold_response(self, reason: str) -> Dict:
        """Generate HOLD response."""
        return {
        'pair': getattr(self, 'pair', 'UNKNOWN'),
        'vote': 'HOLD',
        'confidence': 50,
        'reasoning': reason,
        'z_score': getattr(self, 'z_score', 0),
        'position': 0,
        'timestamp': datetime.now().isoformat()
        }