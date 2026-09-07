# zscore_engine.py - SINGLE Z-SCORE ENGINE (COMPLETE FIXED VERSION)

import math
import time
import logging
from collections import deque
from typing import Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)


class SingleZScoreEngine:
    """
    ✅ SINGLE Z-SCORE ENGINE - One source, one calculation
    Uses prices from forex_dashboard.py only
    
    This fixes the "3 different Z-Score values" problem by:
    1. Using ONLY ONE data source (forex_dashboard.py)
    2. Using ONLY ONE calculation method
    3. Using ONLY ONE price history
    """
    
    def __init__(self, lookback: int = 50, entry_threshold: float = 2.0, 
                 exit_threshold: float = 0.5, warmup_cycles: int = 50):
        """
        Initialize the Z-Score Engine
        
        Args:
            lookback: Number of price points to use for calculation
            entry_threshold: Z-Score threshold to enter a trade (default 2.0)
            exit_threshold: Z-Score threshold to exit a trade (default 0.5)
            warmup_cycles: Number of cycles needed before live trading
        """
        self.lookback = lookback
        self.entry_threshold = entry_threshold
        self.exit_threshold = exit_threshold
        self.warmup_cycles = warmup_cycles
        
        # Price history from dashboard (SINGLE SOURCE)
        self.price_history = {}  # symbol -> deque of prices
        self.mean = {}           # symbol -> mean
        self.std = {}            # symbol -> standard deviation
        self.z_score = {}        # symbol -> current Z-Score
        self.samples = {}        # symbol -> number of samples
        
        # Tracking
        self.cycle_count = 0
        self.is_warmed_up = False
        self.warmup_start_time = None
        
        # Symbol-specific thresholds
        self.thresholds = self._get_default_thresholds()
        
        logger.info(f'✅ Single Z-Score Engine initialized')
        logger.info(f'   Lookback: {lookback} cycles')
        logger.info(f'   Entry Threshold: {entry_threshold}')
        logger.info(f'   Warmup Cycles: {warmup_cycles}')
    
    def _get_default_thresholds(self) -> Dict:
        """Get default thresholds by symbol type"""
        return {
            # Forex Majors
            'EURUSD': {'entry': 2.0, 'exit': 0.5},
            'GBPUSD': {'entry': 2.0, 'exit': 0.5},
            'USDJPY': {'entry': 2.2, 'exit': 0.5},
            'USDCHF': {'entry': 2.0, 'exit': 0.5},
            'AUDUSD': {'entry': 2.0, 'exit': 0.5},
            'USDCAD': {'entry': 2.0, 'exit': 0.5},
            'NZDUSD': {'entry': 2.0, 'exit': 0.5},
            
            # Forex Crosses
            'EURGBP': {'entry': 2.2, 'exit': 0.5},
            'EURJPY': {'entry': 2.2, 'exit': 0.5},
            'EURCAD': {'entry': 2.2, 'exit': 0.5},
            'EURNZD': {'entry': 2.2, 'exit': 0.5},
            'EURCHF': {'entry': 2.2, 'exit': 0.5},
            
            # Indices (more volatile, higher threshold)
            '#NASDAQ100': {'entry': 2.5, 'exit': 0.5},
            '#DJ30': {'entry': 2.5, 'exit': 0.5},
            '#S&P500': {'entry': 2.5, 'exit': 0.5},
            '#RUSS2000': {'entry': 2.5, 'exit': 0.5},
            '#CAC40': {'entry': 2.5, 'exit': 0.5},
            '#DAX40': {'entry': 2.5, 'exit': 0.5},
            '#FTSE100': {'entry': 2.5, 'exit': 0.5},
            '#NIKKEI225': {'entry': 2.5, 'exit': 0.5},

            # ===== NEW INDICES - Stocks/Equities =====
            '#AMAZON': {'entry': 2.7, 'exit': 0.6},
            '#APPLE': {'entry': 2.5, 'exit': 0.5},
            '#SPACEX': {'entry': 3.0, 'exit': 0.7},
            # Add these to the indices section:

            '#MICROSOFT': {'entry': 2.5, 'exit': 0.5},
            '#VISA': {'entry': 2.5, 'exit': 0.5},
            '#MASTERCARD': {'entry': 2.5, 'exit': 0.5},
            
            # Metals
            'GOLD': {'entry': 2.0, 'exit': 0.5},
            'SILVER': {'entry': 2.0, 'exit': 0.5},
            
            # Energy
            'BRENT_OIL': {'entry': 2.0, 'exit': 0.5},
            'CrudeOIL': {'entry': 2.0, 'exit': 0.5},
            
            # Dollar Index
            # '#DOLLAR_IND': {'entry': 2.2, 'exit': 0.5}
        }
    
    def get_thresholds(self, symbol: str) -> Tuple[float, float]:
        """
        Get entry and exit thresholds for a symbol
        
        Returns:
            (entry_threshold, exit_threshold)
        """
        default = {'entry': self.entry_threshold, 'exit': self.exit_threshold}
        thresholds = self.thresholds.get(symbol, default)
        return thresholds.get('entry', self.entry_threshold), thresholds.get('exit', self.exit_threshold)
    
    def update_price(self, symbol: str, price: float):
        """
        Update price history for a symbol
        
        Args:
            symbol: The symbol (e.g., 'EURUSD')
            price: Current price
        """
        if price <= 0:
            return
        
        if symbol not in self.price_history:
            self.price_history[symbol] = deque(maxlen=self.lookback)
        
        self.price_history[symbol].append(price)
        self.samples[symbol] = len(self.price_history[symbol])
    
    def calculate_zscore(self, symbol: str, price: float) -> Dict:
        """
        Calculate Z-Score for a symbol using SINGLE data source
        
        Args:
            symbol: The symbol (e.g., 'EURUSD')
            price: Current price
            
        Returns:
            Dict with z_score, action, confidence, etc.
        """
        # Update price first
        self.update_price(symbol, price)
        
        # Check if we have enough samples
        samples = self.samples.get(symbol, 0)
        
        if samples < self.warmup_cycles:
            return {
                'z_score': 0,
                'action': 'HOLD',
                'confidence': 0,
                'samples': samples,
                'warmup_needed': self.warmup_cycles - samples,
                'reasoning': f'Warming up: {samples}/{self.warmup_cycles}'
            }
        
        # Calculate Z-Score from history
        history = list(self.price_history[symbol])
        
        # Calculate mean
        mean = sum(history) / len(history)
        
        # Calculate standard deviation
        variance = sum((x - mean) ** 2 for x in history) / len(history)
        std = math.sqrt(variance) if variance > 0 else 0.0001
        
        self.mean[symbol] = mean
        self.std[symbol] = std
        
        # Calculate Z-Score
        z_score = (price - mean) / std if std > 0 else 0
        self.z_score[symbol] = z_score
        
        # Get thresholds
        entry_threshold, exit_threshold = self.get_thresholds(symbol)
        
        # Determine action
        if z_score > entry_threshold:
            confidence = min(95, 75 + (z_score - entry_threshold) * 15)
            return {
                'z_score': z_score,
                'action': 'SELL',
                'confidence': confidence,
                'mean': mean,
                'std': std,
                'samples': samples,
                'entry_threshold': entry_threshold,
                'exit_threshold': exit_threshold,
                'reasoning': f'Overbought: Z={z_score:.2f} (entry: {entry_threshold:.2f})'
            }
        elif z_score < -entry_threshold:
            confidence = min(95, 75 + (-z_score - entry_threshold) * 15)
            return {
                'z_score': z_score,
                'action': 'BUY',
                'confidence': confidence,
                'mean': mean,
                'std': std,
                'samples': samples,
                'entry_threshold': entry_threshold,
                'exit_threshold': exit_threshold,
                'reasoning': f'Oversold: Z={z_score:.2f} (entry: {entry_threshold:.2f})'
            }
        else:
            return {
                'z_score': z_score,
                'action': 'HOLD',
                'confidence': max(40, 50 - abs(z_score) * 5),
                'mean': mean,
                'std': std,
                'samples': samples,
                'entry_threshold': entry_threshold,
                'exit_threshold': exit_threshold,
                'reasoning': f'Normal: Z={z_score:.2f}'
            }
    
    def peek_zscore(self, symbol: str, price: float) -> Dict:
        """
        Peek Z-Score without updating history (READ ONLY)
        
        Use this when you want to check Z-Score without adding
        the price to history.
        """
        if self.samples.get(symbol, 0) < self.warmup_cycles:
            return {
                'z_score': 0,
                'action': 'HOLD',
                'confidence': 0,
                'samples': self.samples.get(symbol, 0),
                'reasoning': f'Warming up: {self.samples.get(symbol, 0)}/{self.warmup_cycles}'
            }
        
        history = list(self.price_history[symbol])
        mean = sum(history) / len(history)
        variance = sum((x - mean) ** 2 for x in history) / len(history)
        std = math.sqrt(variance) if variance > 0 else 0.0001
        
        z_score = (price - mean) / std if std > 0 else 0
        entry_threshold, exit_threshold = self.get_thresholds(symbol)
        
        if z_score > entry_threshold:
            return {
                'z_score': z_score,
                'action': 'SELL',
                'confidence': min(95, 75 + (z_score - entry_threshold) * 15),
                'samples': self.samples.get(symbol, 0),
                'entry_threshold': entry_threshold,
                'exit_threshold': exit_threshold,
                'reasoning': f'Overbought: Z={z_score:.2f}'
            }
        elif z_score < -entry_threshold:
            return {
                'z_score': z_score,
                'action': 'BUY',
                'confidence': min(95, 75 + (-z_score - entry_threshold) * 15),
                'samples': self.samples.get(symbol, 0),
                'entry_threshold': entry_threshold,
                'exit_threshold': exit_threshold,
                'reasoning': f'Oversold: Z={z_score:.2f}'
            }
        else:
            return {
                'z_score': z_score,
                'action': 'HOLD',
                'confidence': max(40, 50 - abs(z_score) * 5),
                'samples': self.samples.get(symbol, 0),
                'entry_threshold': entry_threshold,
                'exit_threshold': exit_threshold,
                'reasoning': f'Normal: Z={z_score:.2f}'
            }
    
    def get_warmup_status(self) -> Dict:
        """
        Get warmup status for all symbols
        
        Returns:
            Dict with overall status and per-symbol details
        """
        status = {}
        total_warmup_needed = 0
        total_completed = 0
        
        for symbol, samples in self.samples.items():
            if samples >= self.warmup_cycles:
                status[symbol] = {'status': 'READY', 'samples': samples}
                total_completed += 1
            else:
                status[symbol] = {
                    'status': 'WARMING', 
                    'samples': samples, 
                    'needed': self.warmup_cycles - samples
                }
                total_warmup_needed += 1
        
        return {
            'status': 'COMPLETE' if total_warmup_needed == 0 else 'WARMING',
            'symbols': status,
            'total_symbols': len(self.samples),
            'ready_symbols': total_completed,
            'warming_symbols': total_warmup_needed
        }
    
    def get_status(self, symbol: Optional[str] = None) -> Dict:
        """
        Get engine status for a specific symbol or all symbols
        
        Args:
            symbol: Optional symbol to get status for
        """
        if symbol:
            return {
                'symbol': symbol,
                'samples': self.samples.get(symbol, 0),
                'mean': self.mean.get(symbol, 0),
                'std': self.std.get(symbol, 0),
                'z_score': self.z_score.get(symbol, 0),
                'entry_threshold': self.get_thresholds(symbol)[0],
                'exit_threshold': self.get_thresholds(symbol)[1],
                'warmed_up': self.samples.get(symbol, 0) >= self.warmup_cycles
            }
        else:
            return {
                'total_symbols': len(self.price_history),
                'warmup_cycles': self.warmup_cycles,
                'is_warmed_up': self.is_warmed_up,
                'default_entry': self.entry_threshold,
                'default_exit': self.exit_threshold
            }
    
    def reset_symbol(self, symbol: str):
        """
        Reset Z-Score data for a symbol
        
        Args:
            symbol: The symbol to reset
        """
        if symbol in self.price_history:
            del self.price_history[symbol]
        if symbol in self.mean:
            del self.mean[symbol]
        if symbol in self.std:
            del self.std[symbol]
        if symbol in self.z_score:
            del self.z_score[symbol]
        if symbol in self.samples:
            del self.samples[symbol]
        
        logger.info(f'🔄 Reset Z-Score data for {symbol}')
    
    def reset_all(self):
        """Reset all Z-Score data"""
        self.price_history.clear()
        self.mean.clear()
        self.std.clear()
        self.z_score.clear()
        self.samples.clear()
        self.cycle_count = 0
        self.is_warmed_up = False
        
        logger.info('🔄 Reset ALL Z-Score data')