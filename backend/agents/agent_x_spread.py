# ============================================================
# backend/agents/agent_x_spread.py - ULTIMATE OPTIMIZED VERSION
# ============================================================
# MULTI-PAIR SPREAD REVERSION SPECIALIST
# Supports: INDICES, FOREX, METALS, ENERGY
# Features: Velocity Filter, Adaptive Threshold, Hurst Exponent
# ============================================================

import math
import logging
from typing import Dict, List, Optional
from collections import deque

logger = logging.getLogger(__name__)


class VelocityFilter:
    """
    Prevents entry when Z-score momentum is still rising.
    This solves the "overshoot" problem.
    """
    
    def __init__(self, window: int = 5):
        self.window = window
        self.z_history = deque(maxlen=window + 1)
        self.velocity_history = deque(maxlen=window)
    
    def update(self, z_score: float) -> Dict:
        """Update filter with new Z-score."""
        self.z_history.append(z_score)
        
        if len(self.z_history) < 3:
            return {
                'velocity': 0.0,
                'momentum': 'STABLE',
                'is_slowing': False,
                'can_enter': False,
                'acceleration': 0.0
            }
        
        # Calculate velocity (first derivative)
        z_list = list(self.z_history)
        velocities = [z_list[i] - z_list[i-1] for i in range(1, len(z_list))]
        current_velocity = velocities[-1]
        self.velocity_history.append(current_velocity)
        
        # Calculate acceleration (second derivative)
        if len(velocities) >= 2:
            acceleration = velocities[-1] - velocities[-2]
        else:
            acceleration = 0.0
        
        # Determine momentum
        if current_velocity > 0.1:
            momentum = 'RISING'
        elif current_velocity < -0.1:
            momentum = 'FALLING'
        else:
            momentum = 'STABLE'
        
        # Check if momentum is slowing (critical for entry)
        is_slowing = False
        if len(velocities) >= 2:
            # Velocity is positive but decreasing → slowing
            if current_velocity > 0 and acceleration < 0:
                is_slowing = True
            # Velocity is negative but increasing → slowing
            if current_velocity < 0 and acceleration > 0:
                is_slowing = True
        
        # Entry allowed when:
        # 1. Momentum is slowing, OR
        # 2. Velocity is near zero (stable)
        can_enter = is_slowing or abs(current_velocity) < 0.05
        
        return {
            'velocity': current_velocity,
            'momentum': momentum,
            'is_slowing': is_slowing,
            'can_enter': can_enter,
            'acceleration': acceleration
        }


class HurstExponent:
    """
    Calculates Hurst exponent to detect market regime.
    H < 0.5: Mean-reverting (good for spread trading)
    H = 0.5: Random walk
    H > 0.5: Trending (bad for spread trading)
    """
    
    def __init__(self, max_lag: int = 50):
        self.max_lag = max_lag
        self.prices = deque(maxlen=max_lag * 2)
        self.current_h = 0.5
        self.regime = 'RANDOM'
    
    def update(self, price: float) -> Dict:
        """Update Hurst exponent with new price."""
        self.prices.append(price)
        
        if len(self.prices) < self.max_lag:
            return {
                'hurst': 0.5,
                'regime': 'RANDOM',
                'threshold_multiplier': 1.0,
                'confidence': 50
            }
        
        # Calculate Hurst using R/S analysis
        prices = list(self.prices)
        lags = range(10, min(self.max_lag, len(prices) // 2))
        rs_values = []
        
        for lag in lags:
            n = len(prices) // lag
            if n < 2:
                continue
            chunks = [prices[i*lag:(i+1)*lag] for i in range(n)]
            means = [sum(chunk) / len(chunk) for chunk in chunks]
            stds = [math.sqrt(sum((x - m) ** 2 for x in chunk) / len(chunk)) 
                    for chunk, m in zip(chunks, means)]
            rs = [(max(chunk) - min(chunk)) / s for chunk, s in zip(chunks, stds) if s > 0]
            if rs:
                rs_values.append(sum(rs) / len(rs))
        
        if rs_values and len(rs_values) > 1:
            avg_rs = sum(rs_values) / len(rs_values)
            self.current_h = math.log(avg_rs) / math.log(len(prices))
        else:
            self.current_h = 0.5
        
        # Clamp H to [0.1, 0.9]
        self.current_h = max(0.1, min(0.9, self.current_h))
        
        # Determine regime
        if self.current_h < 0.45:
            self.regime = 'MEAN_REVERTING'
            threshold_multiplier = 0.7  # Lower threshold (easier to enter)
            confidence = 80
        elif self.current_h < 0.55:
            self.regime = 'RANDOM'
            threshold_multiplier = 1.0  # Normal threshold
            confidence = 60
        else:
            self.regime = 'TRENDING'
            threshold_multiplier = 1.5  # Higher threshold (harder to enter)
            confidence = 70
        
        return {
            'hurst': self.current_h,
            'regime': self.regime,
            'threshold_multiplier': threshold_multiplier,
            'confidence': confidence
        }


class AgentXSpread:
    """
    MULTI-PAIR SPREAD REVERSION SPECIALIST
    Features: Velocity Filter + Adaptive Threshold + Hurst Exponent
    """
    
    def __init__(self, name="Agent_X", timeframe="M15"):
        self.name = name
        self.timeframe = timeframe
        self.agent_type = "Multi-Pair Spread Reversion Specialist"
        
        # ===== PAIR CONFIGURATIONS =====
        self.pairs = {
            'INDICES': {
                'asset1': '#S&P500',
                'asset2': '#NASDAQ100',
                'beta': 1.05,
                'base_entry_threshold': 2.0,
                'exit_threshold': 0.3,
            },
            'FOREX': {
                'asset1': 'EURUSD',
                'asset2': 'GBPUSD',
                'beta': 0.85,
                'base_entry_threshold': 1.8,
                'exit_threshold': 0.3,
            },
            'METALS': {
                'asset1': 'GOLD',
                'asset2': 'SILVER',
                'beta': 0.70,
                'base_entry_threshold': 1.8,
                'exit_threshold': 0.3,
            },
            'ENERGY': {
                'asset1': 'BRENT_OIL',
                'asset2': 'CrudeOIL',
                'beta': 0.80,
                'base_entry_threshold': 1.8,
                'exit_threshold': 0.3,
            },
        }
        
        # ===== SPREAD HISTORY (PER INSTANCE) =====
        self.spread_history = []
        self.max_history = 60
        
        # ===== STATE =====
        self.signal = "HOLD"
        self.confidence = 0
        self.position = 0
        self.z_score = 0.0
        self.z_score_ema = 0.0
        self.alpha = 0.3  # EMA smoothing factor
        self.persistence = 0
        self.current_spread = 0.0
        self.mu = 0.0
        self.sigma = 0.0
        self.samples = 0
        self.last_spx = 0
        self.last_ndx = 0
        
        # ===== VELOCITY FILTER (PER PAIR) =====
        self.velocity_filters = {
            'INDICES': VelocityFilter(),
            'FOREX': VelocityFilter(),
            'METALS': VelocityFilter(),
            'ENERGY': VelocityFilter(),
        }
        
        # ===== HURST EXPONENT (PER PAIR) =====
        self.hurst_calculators = {
            'INDICES': HurstExponent(),
            'FOREX': HurstExponent(),
            'METALS': HurstExponent(),
            'ENERGY': HurstExponent(),
        }
        
        # ===== DAILY STATS =====
        self.trades_today = 0
        self.max_trades_per_day = 5
        self.reversions_today = 0
        self.pair_trades = {'INDICES': 0, 'FOREX': 0, 'METALS': 0, 'ENERGY': 0}
        
        # ===== ADAPTIVE THRESHOLD STATE =====
        self.current_entry_threshold = 2.0
        
        logger.info(f"   ✅ {self.name} (Velocity + Hurst) initialized")
        logger.info(f"      📊 Base Entry Threshold: 2.0")
        logger.info(f"      📊 Exit Threshold: 0.3")
        logger.info(f"      📊 Pairs: INDICES, FOREX, METALS, ENERGY")
        logger.info(f"      📊 Velocity Filter: Active (prevents overshoot)")
        logger.info(f"      📊 Hurst Exponent: Active (adaptive thresholds)")
    
    def get_pair_for_symbol(self, symbol: str) -> str:
        """Determine which pair a symbol belongs to."""
        for pair_name, config in self.pairs.items():
            if symbol == config['asset1'] or symbol == config['asset2']:
                return pair_name
        return None
    
    def calculate_spread(self, price1: float, price2: float, beta: float) -> float:
        """Calculate spread between two assets."""
        if price1 <= 0 or price2 <= 0:
            return 0.0
        return math.log(price1) - beta * math.log(price2)
    
    def calculate_z_score(self, spread_history: List[float]) -> Dict:
        """Calculate Z-score from spread history with precision."""
        if len(spread_history) < 10:
            return {'z_score': 0.0, 'mu': 0.0, 'sigma': 0.0, 'samples': len(spread_history)}
        
        mu = sum(spread_history) / len(spread_history)
        variance = sum((x - mu) ** 2 for x in spread_history) / len(spread_history)
        sigma = math.sqrt(variance) if variance > 0 else 0.0001
        
        if sigma > 0:
            z_score = (spread_history[-1] - mu) / sigma
        else:
            z_score = 0.0
        
        return {'z_score': z_score, 'mu': mu, 'sigma': sigma, 'samples': len(spread_history)}
    
    def get_pair_signal(self, pair_name: str, pair_config: Dict, price1: float, price2: float) -> Dict:
        """Get signal with Velocity Filter + Adaptive Threshold + Hurst."""
        
        entry_threshold = pair_config['base_entry_threshold']
        exit_threshold = pair_config['exit_threshold']
        
        # 1. Calculate spread
        spread = self.calculate_spread(price1, price2, pair_config['beta'])
        if spread == 0:
            return self._hold_response("No valid spread", pair_name)
        
        self.spread_history.append(spread)
        if len(self.spread_history) > self.max_history:
            self.spread_history.pop(0)
        
        # 2. Calculate Z-score
        z_result = self.calculate_z_score(self.spread_history)
        z_score = z_result['z_score']
        mu = z_result['mu']
        sigma = z_result['sigma']
        samples = z_result['samples']
        
        self.z_score = z_score
        self.mu = mu
        self.sigma = sigma
        self.samples = samples
        self.current_spread = spread
        
        # 3. EMA smoothing
        if self.samples == 0:
            self.z_score_ema = z_score
        else:
            self.z_score_ema = (self.alpha * z_score) + ((1 - self.alpha) * self.z_score_ema)
        
        # 4. Persistence
        if abs(self.z_score_ema) >= entry_threshold:
            self.persistence += 1
        else:
            self.persistence = 0
        
        # 5. VELOCITY FILTER (PREVENTS OVERSHOOT)
        velocity_result = self.velocity_filters[pair_name].update(z_score)
        
        # 6. HURST EXPONENT (ADAPTIVE THRESHOLD)
        hurst_result = self.hurst_calculators[pair_name].update(price1)
        
        # 7. ADAPTIVE THRESHOLD
        adaptive_threshold = entry_threshold * hurst_result['threshold_multiplier']
        self.current_entry_threshold = adaptive_threshold
        
        # 8. SIGNAL GENERATION
        signal = 'HOLD'
        confidence = 50
        reasoning = f"{pair_name} normal (Z_EMA={self.z_score_ema:.4f})"
        
        # Check if we can enter (velocity + persistence)
        can_enter = velocity_result['can_enter'] and self.persistence >= 2
        
        if can_enter:
            if self.z_score_ema > adaptive_threshold:
                signal = "SELL"
                confidence = min(95, 75 + (self.z_score_ema - adaptive_threshold) * 20)
                reasoning = f"{pair_name} overextended (Z={z_score:.4f}, Z_EMA={self.z_score_ema:.4f}, Persist={self.persistence})"
                
            elif self.z_score_ema < -adaptive_threshold:
                signal = "BUY"
                confidence = min(95, 75 + (-self.z_score_ema - adaptive_threshold) * 20)
                reasoning = f"{pair_name} compressed (Z={z_score:.4f}, Z_EMA={self.z_score_ema:.4f}, Persist={self.persistence})"
        
        # Exit logic
        if abs(self.z_score_ema) < exit_threshold and self.position != 0:
            signal = "HOLD"
            self.position = 0
            confidence = 50
            reasoning = f"{pair_name} reverted (Z_EMA={self.z_score_ema:.4f})"
        
        # Update position
        if signal in ['BUY', 'SELL']:
            self.position = 1 if signal == 'BUY' else -1
        
        self.signal = signal
        self.confidence = confidence
        
        # ===== LOG WITH VELOCITY + HURST INFO =====
        if samples > 0 and (samples % 5 == 0 or samples <= 3):
            logger.info(f"   📊 Agent_X: {pair_name} | Samples={samples}/30 | "
                       f"Z={z_score:.4f} | EMA={self.z_score_ema:.4f} | "
                       f"Persist={self.persistence} | "
                       f"Vel={velocity_result['velocity']:.3f} | "
                       f"H={hurst_result['hurst']:.2f} | "
                       f"Thresh={adaptive_threshold:.2f} | {signal} ({confidence:.0f}%)")
        
        return {
            'pair': pair_name,
            'vote': signal,
            'confidence': confidence,
            'reasoning': reasoning,
            'z_score': round(z_score, 4),
            'z_score_ema': round(self.z_score_ema, 4),
            'persistence': self.persistence,
            'position': self.position,
            'spread': round(spread, 6),
            'mu': round(mu, 6),
            'sigma': round(sigma, 6),
            'samples': samples,
            'asset1': pair_config['asset1'],
            'asset2': pair_config['asset2'],
            'price1': price1,
            'price2': price2,
            'entry_threshold': adaptive_threshold,
            'exit_threshold': exit_threshold,
            'velocity': velocity_result,
            'hurst': hurst_result,
        }
    
    def _hold_response(self, reason: str, pair_name: str) -> Dict:
        """Generate HOLD response."""
        return {
            'pair': pair_name,
            'vote': 'HOLD',
            'confidence': 0,
            'reasoning': reason,
            'z_score': 0.0,
            'z_score_ema': 0.0,
            'persistence': 0,
            'position': 0,
            'spread': 0.0,
            'mu': 0.0,
            'sigma': 0.0,
            'samples': 0,
            'asset1': 'N/A',
            'asset2': 'N/A',
            'price1': 0,
            'price2': 0,
            'entry_threshold': 0,
            'exit_threshold': 0,
            'velocity': {'velocity': 0, 'can_enter': False},
            'hurst': {'hurst': 0.5, 'regime': 'RANDOM'},
        }
    
    def analyze(self, signal_data: Dict) -> Dict:
        """Analyze spread - returns signal for the symbol's pair."""
        symbol = signal_data.get('symbol', '')
        spx_price = signal_data.get('spx_price', 0)
        ndx_price = signal_data.get('ndx_price', 0)
        eurusd_price = signal_data.get('eurusd_price', 0)
        gbpusd_price = signal_data.get('gbpusd_price', 0)
        gold_price = signal_data.get('gold_price', 0)
        silver_price = signal_data.get('silver_price', 0)
        brent_price = signal_data.get('brent_price', 0)
        crude_price = signal_data.get('crude_price', 0)
        
        # ===== GET PRICES FROM BRIDGE IF NEEDED =====
        if spx_price <= 0 or ndx_price <= 0:
            try:
                from price_bridge import price_bridge
                if spx_price <= 0:
                    spx_price = price_bridge.get_price('#S&P500')
                if ndx_price <= 0:
                    ndx_price = price_bridge.get_price('#NASDAQ100')
                if eurusd_price <= 0:
                    eurusd_price = price_bridge.get_price('EURUSD')
                if gbpusd_price <= 0:
                    gbpusd_price = price_bridge.get_price('GBPUSD')
                if gold_price <= 0:
                    gold_price = price_bridge.get_price('GOLD')
                if silver_price <= 0:
                    silver_price = price_bridge.get_price('SILVER')
                if brent_price <= 0:
                    brent_price = price_bridge.get_price('BRENT_OIL')
                if crude_price <= 0:
                    crude_price = price_bridge.get_price('CrudeOIL')
            except:
                pass
        
        self.last_spx = spx_price
        self.last_ndx = ndx_price
        
        # ===== DETERMINE TARGET PAIR =====
        target_pair = self.get_pair_for_symbol(symbol)
        if target_pair is None:
            target_pair = 'INDICES'
        
        # ===== GET PRICES FOR THE PAIR =====
        if target_pair == 'INDICES':
            price1, price2 = spx_price, ndx_price
        elif target_pair == 'FOREX':
            price1, price2 = eurusd_price, gbpusd_price
        elif target_pair == 'METALS':
            price1, price2 = gold_price, silver_price
        elif target_pair == 'ENERGY':
            price1, price2 = brent_price, crude_price
        else:
            price1, price2 = spx_price, ndx_price
        
        # ===== ANALYZE =====
        if price1 > 0 and price2 > 0:
            pair_config = self.pairs[target_pair]
            result = self.get_pair_signal(target_pair, pair_config, price1, price2)
            result['symbol'] = symbol
            result['timeframe'] = self.timeframe
            return result
        
        # ===== NO DATA =====
        return {
            'vote': 'HOLD',
            'confidence': 0,
            'reasoning': 'No price data available',
            'symbol': symbol,
            'timeframe': self.timeframe,
            'z_score': 0.0,
            'z_score_ema': 0.0,
            'persistence': 0,
            'spread': 0.0,
            'samples': 0,
            'asset1': 'N/A',
            'asset2': 'N/A',
            'beta': 0,
            'pair': target_pair
        }
    
    def get_pair_status(self) -> Dict:
        """Get status of all pairs."""
        status = {
            'z_score': self.z_score,
            'z_score_ema': self.z_score_ema,
            'persistence': self.persistence,
            'samples': self.samples,
            'mu': self.mu,
            'sigma': self.sigma,
            'spread': self.current_spread,
            'signal': self.signal,
            'confidence': self.confidence,
            'current_entry_threshold': self.current_entry_threshold,
        }
        
        # Add velocity and hurst for each pair
        for pair_name in self.velocity_filters:
            status[f'{pair_name}_velocity'] = {
                'velocity': self.velocity_filters[pair_name].velocity_history[-1] if self.velocity_filters[pair_name].velocity_history else 0,
                'can_enter': self.velocity_filters[pair_name].z_history and len(self.velocity_filters[pair_name].z_history) > 2
            }
            status[f'{pair_name}_hurst'] = {
                'hurst': self.hurst_calculators[pair_name].current_h,
                'regime': self.hurst_calculators[pair_name].regime,
            }
        
        return status
    
    def reset_daily_trades(self):
        """Reset daily trade counter."""
        self.trades_today = 0
        self.reversions_today = 0
        self.pair_trades = {'INDICES': 0, 'FOREX': 0, 'METALS': 0, 'ENERGY': 0}
        logger.info(f"   🔄 {self.name} daily trade counter reset")