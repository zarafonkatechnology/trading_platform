# agents2/forex_agent_x.py - Fixed Version

import math
import logging
from collections import deque
from typing import Dict, List, Optional

logger = logging.getLogger(__name__)


class ForexAgentX:
    """
    Enhanced Agent_X for Forex - Spread Reversion Specialist
    Now includes gear-based mechanics and multi-pair correlation
    """
    
    def __init__(self, name="Forex_X", timeframe="M15"):  # ← FIXED: Default timeframe
        self.name = name
        self.timeframe = timeframe  # ← FIXED: Assign timeframe
        self.agent_type = "Forex Spread Reversion Specialist"
        
        # === GEAR CONFIGURATION ===
        self.gear_config = {
            'EURUSD': {'beta': 1.10, 'gear_ratio': 1.2, 'type': 'INVERSE', 'entry_threshold': 2.0},
            'GBPUSD': {'beta': 1.05, 'gear_ratio': 1.1, 'type': 'INVERSE', 'entry_threshold': 2.0},
            'USDJPY': {'beta': 0.85, 'gear_ratio': 0.8, 'type': 'DIRECT', 'entry_threshold': 2.0},
            'AUDUSD': {'beta': 0.90, 'gear_ratio': 0.9, 'type': 'INVERSE', 'entry_threshold': 2.0},
            'USDCAD': {'beta': 0.80, 'gear_ratio': 0.7, 'type': 'DIRECT', 'entry_threshold': 2.0},
            'USDCHF': {'beta': 0.75, 'gear_ratio': 0.7, 'type': 'DIRECT', 'entry_threshold': 2.0},
            'EURGBP': {'beta': 0.95, 'gear_ratio': 0.5, 'type': 'CROSS', 'entry_threshold': 2.5},
            'EURJPY': {'beta': 0.98, 'gear_ratio': 0.6, 'type': 'CROSS', 'entry_threshold': 2.5},
        }
        self.testing_mode = True  # ← ADD THIS
        
        # === SPREAD HISTORY PER PAIR ===
        self.histories = {pair: deque(maxlen=60) for pair in self.gear_config.keys()}
        self.z_scores = {pair: 0.0 for pair in self.gear_config.keys()}
        self.emas = {pair: 0.0 for pair in self.gear_config.keys()}
        self.persistence = {pair: 0 for pair in self.gear_config.keys()}
        
        # === ENGINE STATE (from Dollar Engine) ===
        self.engine_speed = 0.0
        self.engine_direction = 'NEUTRAL'
        self.engine_health = 100.0
        self.reversal_probability = 0.0
        
        # === AGENT STATE ===
        self.signal = "HOLD"
        self.confidence = 0.0
        self.position = 0
        self.current_pair = "EURUSD"
        self.alpha = 0.3  # EMA smoothing
        
        # === COMMUNICATION BUFFER ===
        self.communication_buffer = []
        
        # === PERFORMANCE ===
        self.performance = {
            'trades': 0,
            'wins': 0,
            'losses': 0,
            'win_rate': 0.0,
            'avg_return': 0.0,
            'max_drawdown': 0.0,
            'sharpe_ratio': 0.0,
        }
        
        logger.info(f"   ✅ {self.name} (Forex Enhanced) initialized")
        logger.info(f"      📊 Pairs: {len(self.gear_config)} currency pairs")
        logger.info(f"      📊 Gear types: INVERSE, DIRECT, CROSS")
    
    def analyze(self, market_data: Dict) -> Dict:
        """Main analysis method - enhanced for forex with gear mechanics"""
        results = {}
        
        # Update engine state if available
        if 'engine_state' in market_data:
            self.engine_speed = market_data['engine_state'].get('engine_speed', 0.0)
            self.engine_direction = market_data['engine_state'].get('engine_direction', 'NEUTRAL')
            self.engine_health = market_data['engine_state'].get('engine_health', 100.0)
            self.reversal_probability = market_data['engine_state'].get('reversal_probability', 0.0)
        
        # Process each pair
        for pair, config in self.gear_config.items():
            # Get prices
            price1 = market_data.get(config.get('asset1', pair[:3]), 0)
            price2 = market_data.get(config.get('asset2', pair[3:]), 0)
            
            if price1 > 0 and price2 > 0:
                result = self._analyze_pair(pair, config, price1, price2)
                results[pair] = result
        
        # Generate master signal
        master_signal = self._generate_master_signal(results)
        
        return {
            'agent': self.name,
            'signal': master_signal.get('action', 'HOLD'),
            'confidence': master_signal.get('confidence', 50),
            'reasoning': master_signal.get('reason', 'No signal'),
            'pair_signals': results,
            'engine_state': {
                'speed': self.engine_speed,
                'direction': self.engine_direction,
                'health': self.engine_health,
                'reversal_probability': self.reversal_probability,
            },
            'performance': self.performance,
            'timestamp': self._get_timestamp()
        }
    
    def _analyze_pair(self, pair: str, config: Dict, price1: float, price2: float) -> Dict:
        """Analyze a single currency pair with gear mechanics"""
        # Calculate spread
        spread = self._calculate_spread(price1, price2, config['beta'])
        if spread == 0:
            return {'action': 'HOLD', 'confidence': 0, 'reason': 'No data'}
        
        # Update history
        self.histories[pair].append(spread)
        
        # Calculate Z-score
        z_result = self._calculate_z_score(list(self.histories[pair]))
        z_score = z_result['z_score']
        mu = z_result['mu']
        sigma = z_result['sigma']
        samples = z_result['samples']
        
        # Update EMA
        if samples == 1:
            self.emas[pair] = z_score
        else:
            self.emas[pair] = (self.alpha * z_score) + ((1 - self.alpha) * self.emas[pair])
        
        # Update persistence
        entry_threshold = config.get('entry_threshold', 2.0)
        if abs(self.emas[pair]) >= entry_threshold:
            self.persistence[pair] += 1
        else:
            self.persistence[pair] = 0
        
        # Store Z-score
        self.z_scores[pair] = z_score
        
        # Generate signal with gear alignment
        signal = self._generate_gear_signal(pair, z_score, config)
        
        return {
            'pair': pair,
            'action': signal['action'],
            'confidence': signal['confidence'],
            'reason': signal['reason'],
            'z_score': z_score,
            'z_score_ema': self.emas[pair],
            'persistence': self.persistence[pair],
            'samples': samples,
            'mu': mu,
            'sigma': sigma,
            'spread': spread,
            'gear_type': config['type'],
            'gear_ratio': config['gear_ratio'],
            'timestamp': self._get_timestamp()
        }
    
    def _generate_gear_signal(self, pair: str, z_score: float, config: Dict) -> Dict:
        """Generate signal with gear alignment checking"""
        entry_threshold = config.get('entry_threshold', 2.0)
        exit_threshold = 0.3
        gear_type = config['type']
        
        # Check engine alignment
        engine_aligned = self._check_engine_alignment(gear_type, z_score)
        
        signal = 'HOLD'
        confidence = 50
        reason = f'{pair} normal (Z={z_score:.3f})'
        min_persistence = 1 if self.testing_mode else 2
        # Entry logic with persistence
        if self.persistence[pair] >= min_persistence:
            if self.emas[pair] > entry_threshold:
                if engine_aligned:
                    signal = 'SELL'
                    confidence = min(90, 75 + (self.emas[pair] - entry_threshold) * 15)
                    reason = f'{pair} overextended + Engine {self.engine_direction} (Z={z_score:.3f})'
                else:
                    signal = 'HOLD'
                    confidence = 40
                    reason = f'{pair} overextended but Engine misaligned'
            
            elif self.emas[pair] < -entry_threshold:
                if engine_aligned:
                    signal = 'BUY'
                    confidence = min(90, 75 + (-self.emas[pair] - entry_threshold) * 15)
                    reason = f'{pair} compressed + Engine {self.engine_direction} (Z={z_score:.3f})'
                else:
                    signal = 'HOLD'
                    confidence = 40
                    reason = f'{pair} compressed but Engine misaligned'
        
        # Exit logic
        if abs(z_score) < exit_threshold and self.position != 0:
            signal = 'CLOSE'
            confidence = 70
            reason = f'{pair} reverted to mean (Z={z_score:.3f})'
        
        # Engine reversal exit
        if self.reversal_probability > 70 and self.position != 0:
            signal = 'CLOSE'
            confidence = 80
            reason = f'Engine reversal detected (Prob: {self.reversal_probability:.0f}%)'
        
        return {
            'action': signal,
            'confidence': confidence,
            'reason': reason
        }
    
    def _check_engine_alignment(self, gear_type: str, z_score: float) -> bool:
        """Check if gear signal aligns with engine direction"""
        if self.engine_speed == 0:
            return True
        
        if gear_type == 'INVERSE':
            if z_score > 0 and self.engine_direction == 'FORWARD':
                return True
            if z_score < 0 and self.engine_direction == 'BACKWARD':
                return True
        elif gear_type == 'DIRECT':
            if z_score > 0 and self.engine_direction == 'FORWARD':
                return True
            if z_score < 0 and self.engine_direction == 'BACKWARD':
                return True
        
        return False
    
    def _generate_master_signal(self, pair_results: Dict) -> Dict:
        """Generate master signal from all pair signals"""
        buys = 0
        sells = 0
        holds = 0
        total_confidence = 0
        
        for pair, result in pair_results.items():
            if result['action'] == 'BUY':
                buys += 1
                total_confidence += result['confidence']
            elif result['action'] == 'SELL':
                sells += 1
                total_confidence += result['confidence']
            elif result['action'] == 'CLOSE':
                sells += 1
            else:
                holds += 1
        
        if buys > sells and buys > holds:
            action = 'BUY'
            confidence = min(90, total_confidence / max(1, buys) * 0.8)
            reason = f'Majority BUY ({buys}/{buys+sells+holds})'
        elif sells > buys and sells > holds:
            action = 'SELL'
            confidence = min(90, total_confidence / max(1, sells) * 0.8)
            reason = f'Majority SELL ({sells}/{buys+sells+holds})'
        else:
            action = 'HOLD'
            confidence = 50
            reason = f'Mixed signals (B:{buys} S:{sells} H:{holds})'
        
        return {
            'action': action,
            'confidence': confidence,
            'reason': reason,
            'buy_count': buys,
            'sell_count': sells,
            'hold_count': holds
        }
    
    def _calculate_spread(self, price1: float, price2: float, beta: float) -> float:
        """Calculate spread between two currencies."""
        if price1 <= 0 or price2 <= 0:
            return 0.0
        return math.log(price1) - beta * math.log(price2)
    
    def _calculate_z_score(self, spread_history: List[float]) -> Dict:
        """Calculate Z-score from spread history."""
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
    
    def _get_timestamp(self) -> str:
        """Get current timestamp."""
        from datetime import datetime
        return datetime.now().isoformat()