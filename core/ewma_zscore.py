# core/ewma_zscore.py
"""
EWMA-based Z-Score with state persistence
Never starts from zero - preserves historical baseline
"""

import json
import os
import math
from typing import Dict, Tuple
from collections import deque
import logging

logger = logging.getLogger(__name__)

class EWMAZScore:
    """
    Exponential Weighted Moving Average Z-Score
    Preserves state between runs - no cold start!
    """
    
    def __init__(self, alpha: float = 0.1, lookback: int = 50):
        self.alpha = alpha  # Smoothing factor (0.05 - 0.2)
        self.lookback = lookback
        self.state_file = 'ewma_state.json'
        self.history_file = 'price_history.json'
        
        # ===== State =====
        self.mean = {}
        self.variance = {}
        self.std = {}
        self.z_score = {}
        self.samples = {}
        self.price_history = {}
        self.initialized = {}  # Track if symbol has been initialized with history
        
        # ===== Load saved state =====
        self._load_state()
    
    def _load_state(self) -> bool:
        """Load saved EWMA state from file"""
        try:
            if os.path.exists(self.state_file):
                with open(self.state_file, 'r') as f:
                    state = json.load(f)
                for symbol, data in state.items():
                    self.mean[symbol] = data.get('mean', 0)
                    self.variance[symbol] = data.get('variance', 0.0001)
                    self.samples[symbol] = data.get('samples', 0)
                    self.std[symbol] = math.sqrt(max(self.variance[symbol], 0.0001))
                    self.initialized[symbol] = True
                    self.z_score[symbol] = 0  # Will be calculated on next update
                logger.info(f'✅ Loaded EWMA state for {len(state)} symbols')
                return True
        except Exception as e:
            logger.warning(f'Failed to load EWMA state: {e}')
        return False
    
    def _save_state(self):
        """Save EWMA state to file - ALWAYS save if we have data"""
        try:
            state = {}
            has_data = False
            for symbol in self.mean:
                # Save even if samples is 0 (just initialized)
                if symbol in self.mean:
                    state[symbol] = {
                        'mean': self.mean[symbol],
                        'variance': self.variance.get(symbol, 0.0001),
                        'samples': self.samples.get(symbol, 0)
                    }
                    has_data = True
            
            if has_data:
                with open(self.state_file, 'w') as f:
                    json.dump(state, f, indent=2)
                logger.debug(f'✅ Saved EWMA state for {len(state)} symbols')
        except Exception as e:
            logger.warning(f'Failed to save EWMA state: {e}')
    
    def _load_price_history(self, symbol: str) -> bool:
        """Load price history from file"""
        try:
            if os.path.exists(self.history_file):
                with open(self.history_file, 'r') as f:
                    data = json.load(f)
                if symbol in data and data[symbol]:
                    self.price_history[symbol] = data[symbol]
                    logger.info(f'✅ Loaded {len(self.price_history[symbol])} prices for {symbol}')
                    return True
        except Exception as e:
            logger.warning(f'Failed to load price history: {e}')
        return False
    
    def _save_price_history(self):
        """Save price history to file"""
        try:
            data = {}
            if os.path.exists(self.history_file):
                with open(self.history_file, 'r') as f:
                    data = json.load(f)
            for symbol, history in self.price_history.items():
                if history and len(history) > 0:
                    data[symbol] = history[-100:]  # Keep last 100
            if data:
                with open(self.history_file, 'w') as f:
                    json.dump(data, f, indent=2)
        except Exception as e:
            logger.warning(f'Failed to save price history: {e}')
    
    def initialize_with_history(self, symbol: str, history: list):
        """Initialize EWMA with historical data"""
        if not history or len(history) < 2:
            return
        
        self.price_history[symbol] = history
        
        # Initialize mean and variance from history
        if len(history) >= 5:
            self.mean[symbol] = sum(history) / len(history)
            variance = sum((x - self.mean[symbol]) ** 2 for x in history) / len(history)
            self.variance[symbol] = variance if variance > 0.0000001 else 0.0001
            self.std[symbol] = math.sqrt(self.variance[symbol])
            self.samples[symbol] = len(history)
            self.initialized[symbol] = True
            
            # Calculate Z-score for the last price
            last_price = history[-1]
            if self.std[symbol] > 0:
                self.z_score[symbol] = (last_price - self.mean[symbol]) / self.std[symbol]
            else:
                self.z_score[symbol] = 0
            
            logger.info(f'✅ Initialized {symbol} with {len(history)} samples')
            self._save_state()
    
    def update(self, symbol: str, price: float):
        """Update EWMA with new price"""
        
        # ===== Handle invalid prices =====
        if price <= 0:
            if symbol not in self.mean:
                self.mean[symbol] = 0
                self.variance[symbol] = 0.0001
                self.std[symbol] = 0.01
                self.samples[symbol] = 0
                self.z_score[symbol] = 0
                self.initialized[symbol] = False
                self._save_state()  # Save even for zero price
            return
        
        # ===== If not initialized, set initial values =====
        if symbol not in self.mean:
            # Try to load price history first
            if self._load_price_history(symbol):
                history = self.price_history[symbol]
                if len(history) >= 5:
                    self.mean[symbol] = sum(history) / len(history)
                    variance = sum((x - self.mean[symbol]) ** 2 for x in history) / len(history)
                    self.variance[symbol] = variance if variance > 0.0000001 else 0.0001
                    self.std[symbol] = math.sqrt(self.variance[symbol])
                    self.samples[symbol] = len(history)
                    self.initialized[symbol] = True
                    logger.info(f'✅ Restored {symbol} from history ({len(history)} samples)')
                else:
                    # Initialize with current price
                    self.mean[symbol] = price
                    self.variance[symbol] = 0.0001
                    self.std[symbol] = 0.01
                    self.samples[symbol] = 0
                    self.z_score[symbol] = 0
                    self.initialized[symbol] = False
                    logger.info(f'🆕 Initialized {symbol} with first price: {price}')
                    self._save_state()  # Save immediately
            else:
                # Initialize with current price
                self.mean[symbol] = price
                self.variance[symbol] = 0.0001
                self.std[symbol] = 0.01
                self.samples[symbol] = 0
                self.z_score[symbol] = 0
                self.initialized[symbol] = False
                logger.info(f'🆕 Initialized {symbol} with first price: {price}')
                self._save_state()  # Save immediately
        
        # ===== Store price history =====
        if symbol not in self.price_history:
            self.price_history[symbol] = []
        self.price_history[symbol].append(price)
        if len(self.price_history[symbol]) > 100:
            self.price_history[symbol] = self.price_history[symbol][-100:]
        
        # ===== EWMA Update (only after initialization with history) =====
        if self.initialized.get(symbol, False):
            self.samples[symbol] += 1
            
            # Update mean
            old_mean = self.mean[symbol]
            self.mean[symbol] = self.alpha * price + (1 - self.alpha) * old_mean
            
            # Update variance
            old_variance = self.variance.get(symbol, 0.0001)
            delta = price - old_mean
            self.variance[symbol] = (1 - self.alpha) * (old_variance + self.alpha * delta * delta)
            
            # Calculate standard deviation
            self.std[symbol] = math.sqrt(max(self.variance[symbol], 0.0000001))
            
            # Calculate Z-score
            if self.std[symbol] > 0:
                self.z_score[symbol] = (price - self.mean[symbol]) / self.std[symbol]
            else:
                self.z_score[symbol] = 0
        else:
            # Not initialized with history yet - just store the price
            # But still update mean slightly for first few prices
            self.samples[symbol] += 1
            if self.samples[symbol] <= 5:
                # Gradually build mean
                old_mean = self.mean[symbol]
                self.mean[symbol] = (old_mean * (self.samples[symbol] - 1) + price) / self.samples[symbol]
        
        # Save state periodically
        if self.samples[symbol] % 5 == 0 or self.samples[symbol] <= 5:
            self._save_state()
            self._save_price_history()
    
    def get_zscore(self, symbol: str) -> Dict:
        """Get current Z-score with all metrics"""
        return {
            'z_score': self.z_score.get(symbol, 0),
            'mean': self.mean.get(symbol, 0),
            'std': self.std.get(symbol, 0.0001),
            'samples': self.samples.get(symbol, 0),
            'variance': self.variance.get(symbol, 0.0001),
            'initialized': self.initialized.get(symbol, False)
        }
    
    def get_all_scores(self) -> Dict:
        """Get all Z-scores"""
        return {symbol: self.z_score.get(symbol, 0) for symbol in self.z_score}