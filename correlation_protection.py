# ============================================================
# correlation_protection.py - FIXED VERSION
# ============================================================

import numpy as np
from collections import deque  # ← ADD THIS IMPORT
from typing import Dict, List, Optional
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class CorrelationProtection:
    """
    Advanced correlation monitoring and kill switch.
    
    Tracks multiple correlation metrics and triggers protection
    when any metric violates thresholds.
    """
    
    def __init__(self):
        self.correlation_history = []
        self.rolling_correlation = 0.85
        self.correlation_threshold = 0.7
        
        # Advanced metrics
        self.rolling_beta = 1.05
        self.beta_threshold_low = 0.5
        self.beta_threshold_high = 2.0
        
        self.rolling_spread = deque(maxlen=100)  # ← NOW WORKS
        self.spread_volatility = 0
        
        self.kill_switch_active = False
        self.kill_reason = ""
        
        logger.info("✅ CorrelationProtection initialized")
        
    def update_correlation(self, spx_returns: np.ndarray, ndx_returns: np.ndarray):
        """Update rolling correlation and beta."""
        if len(spx_returns) < 20:
            return
        
        # Correlation
        self.rolling_correlation = np.corrcoef(spx_returns[-20:], ndx_returns[-20:])[0, 1]
        self.correlation_history.append(self.rolling_correlation)
        
        # Beta
        cov = np.cov(spx_returns[-20:], ndx_returns[-20:])[0, 1]
        var = np.var(ndx_returns[-20:])
        if var > 0:
            self.rolling_beta = cov / var
        
        # Spread volatility
        spreads = spx_returns[-20:] - self.rolling_beta * ndx_returns[-20:]
        self.spread_volatility = np.std(spreads)
        
        self._check_kill_switch()
    
    def _check_kill_switch(self):
        """Check if any protection rule is violated."""
        reasons = []
        
        # Rule 1: Correlation breakdown
        if self.rolling_correlation < self.correlation_threshold:
            reasons.append(f"Correlation dropped to {self.rolling_correlation:.3f}")
        
        # Rule 2: Beta instability
        if self.rolling_beta < self.beta_threshold_low or self.rolling_beta > self.beta_threshold_high:
            reasons.append(f"Beta unstable: {self.rolling_beta:.3f}")
        
        # Rule 3: Spread volatility spike
        if self.spread_volatility > 0.005:  # 0.5% volatility
            reasons.append(f"Spread volatility spike: {self.spread_volatility:.4f}")
        
        # Rule 4: Rapid correlation change
        if len(self.correlation_history) > 10:
            delta = abs(self.rolling_correlation - np.mean(self.correlation_history[-10:-1]))
            if delta > 0.3:
                reasons.append(f"Rapid correlation change: {delta:.3f}")
        
        # Activate kill switch if any rule violated
        if reasons:
            self.kill_switch_active = True
            self.kill_reason = " | ".join(reasons)
            logger.warning(f"🔴 KILL SWITCH ACTIVE: {self.kill_reason}")
        else:
            self.kill_switch_active = False
            self.kill_reason = ""
    
    def is_trade_safe(self) -> Dict:
        """
        Check if it's safe to trade based on all correlation metrics.
        """
        return {
            'safe': not self.kill_switch_active,
            'kill_switch': self.kill_switch_active,
            'reason': self.kill_reason,
            'correlation': round(self.rolling_correlation, 4),
            'beta': round(self.rolling_beta, 4),
            'spread_volatility': round(self.spread_volatility, 4)
        }
    
    def get_status(self) -> Dict:
        """Get current protection status."""
        return {
            'kill_switch_active': self.kill_switch_active,
            'correlation': round(self.rolling_correlation, 4),
            'beta': round(self.rolling_beta, 4),
            'spread_volatility': round(self.spread_volatility, 4),
            'reasons': self.kill_reason if self.kill_switch_active else 'All systems normal'
        }