# ============================================================
# adaptive_threshold.py - Forward Gradient Calibration
# ============================================================
# Automatically calibrates Z-score thresholds
# ============================================================

import numpy as np
from typing import Dict, List, Optional
from datetime import datetime
import logging

logger = logging.getLogger(__name__)


class AdaptiveThresholdCalibrator:
    """
    Forward Gradient Calibration.
    
    Automatically adjusts Z-score threshold based on:
    1. Recent performance
    2. Current volatility
    3. Market regime
    """
    
    def __init__(self, window_size: int = 100):
        self.window_size = window_size
        self.performance_history = []
        self.z_history = []
        
        self.current_threshold = 2.5
        self.threshold_range = (1.5, 4.0)
        self.calibration_frequency = 20  # Calibrate every 20 trades
        
        self.calibration_count = 0
        self.last_calibration = datetime.now()
        
        logger.info("✅ AdaptiveThresholdCalibrator initialized")
        logger.info(f"   Current Threshold: {self.current_threshold:.2f}")
        logger.info(f"   Window Size: {window_size}")
    
    def add_trade_result(self, trade: Dict):
        """Add a trade result for calibration."""
        self.performance_history.append({
            'pnl': trade.get('pnl', 0),
            'z_score': trade.get('z_score', 0),
            'timestamp': trade.get('timestamp', datetime.now())
        })
        
        self.z_history.append(trade.get('z_score', 0))
        
        # Keep history limited
        if len(self.performance_history) > self.window_size * 2:
            self.performance_history = self.performance_history[-self.window_size * 2:]
            self.z_history = self.z_history[-self.window_size * 2:]
        
        # Calibrate periodically
        if len(self.performance_history) % self.calibration_frequency == 0:
            self.calibrate()
    
    def calibrate(self) -> float:
        """
        Perform forward gradient calibration.
        Returns the new threshold.
        """
        if len(self.performance_history) < self.window_size:
            return self.current_threshold
        
        recent_trades = self.performance_history[-self.window_size:]
        self.calibration_count += 1
        
        # ===== 1. TEST CANDIDATE THRESHOLDS =====
        candidate_thresholds = np.arange(
            self.threshold_range[0],
            self.threshold_range[1] + 0.1,
            0.1
        )
        
        results = []
        for threshold in candidate_thresholds:
            simulated_pnls = self._simulate_trades(recent_trades, threshold)
            sharpe = self._calculate_sharpe(simulated_pnls)
            results.append({
                'threshold': threshold,
                'sharpe': sharpe,
                'win_rate': self._calculate_win_rate(simulated_pnls)
            })
        
        # ===== 2. FIND BEST THRESHOLD =====
        best = max(results, key=lambda x: x['sharpe'])
        new_threshold = best['threshold']
        
        # ===== 3. VOLATILITY ADJUSTMENT =====
        volatility = self._calculate_current_volatility()
        volatility_adjustment = volatility * 10  # Higher volatility = higher threshold
        
        # ===== 4. REGIME ADJUSTMENT =====
        regime_adjustment = self._get_regime_adjustment()
        
        # ===== 5. COMBINE =====
        adjusted_threshold = new_threshold + volatility_adjustment + regime_adjustment
        adjusted_threshold = max(self.threshold_range[0], min(self.threshold_range[1], adjusted_threshold))
        
        # ===== 6. LOG =====
        if abs(adjusted_threshold - self.current_threshold) > 0.2:
            logger.info(f"📊 Threshold Calibrated: {self.current_threshold:.2f} → {adjusted_threshold:.2f}")
            logger.info(f"   Sharpe: {best['sharpe']:.3f} | Win Rate: {best['win_rate']:.1f}%")
            logger.info(f"   Volatility Adjustment: {volatility_adjustment:.2f}")
            logger.info(f"   Regime Adjustment: {regime_adjustment:.2f}")
        
        self.current_threshold = adjusted_threshold
        self.last_calibration = datetime.now()
        
        return self.current_threshold
    
    def _simulate_trades(self, trades: List[Dict], threshold: float) -> List[float]:
        """Simulate trade outcomes with given threshold."""
        simulated_pnls = []
        
        for trade in trades:
            z_score = trade.get('z_score', 0)
            pnl = trade.get('pnl', 0)
            
            # If Z-score would have triggered
            if abs(z_score) > threshold:
                simulated_pnls.append(pnl)
            else:
                simulated_pnls.append(0)  # Skip trade
        
        return simulated_pnls
    
    def _calculate_sharpe(self, returns: List[float]) -> float:
        """Calculate Sharpe ratio."""
        if not returns or len(returns) < 5:
            return -1000
        
        # Remove zeros (skipped trades)
        active_returns = [r for r in returns if r != 0]
        
        if len(active_returns) < 5:
            return -1000
        
        mean_return = np.mean(active_returns)
        std_return = np.std(active_returns) + 0.0001
        
        return mean_return / std_return * np.sqrt(252)
    
    def _calculate_win_rate(self, returns: List[float]) -> float:
        """Calculate win rate from returns."""
        active_returns = [r for r in returns if r != 0]
        
        if not active_returns:
            return 0
        
        wins = sum(1 for r in active_returns if r > 0)
        return (wins / len(active_returns)) * 100
    
    def _calculate_current_volatility(self) -> float:
        """Calculate current volatility from Z-scores."""
        if len(self.z_history) < 20:
            return 0
        
        return np.std(self.z_history[-20:])
    
    def _get_regime_adjustment(self) -> float:
        """Get adjustment based on market regime."""
        try:
            from institutional.market_regime import MarketRegimeClassifier
            # This would use the current regime
            # For now, return 0
        except:
            pass
        
        return 0
    
    def get_status(self) -> Dict:
        """Get current status."""
        return {
            'current_threshold': self.current_threshold,
            'calibration_count': self.calibration_count,
            'history_length': len(self.performance_history),
            'last_calibration': self.last_calibration.isoformat()
        }