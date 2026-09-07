# ============================================================
# market_regime.py - System Classifier
# ============================================================
# Determines market state BEFORE any trade decision
# ============================================================

import numpy as np
from typing import Dict, List, Optional
from datetime import datetime
import logging

logger = logging.getLogger(__name__)


class MarketRegimeClassifier:
    """
    System Classifier - Determines current market state.
    
    Regimes:
        - RANGING: Mean-reversion works best
        - TRENDING_UP: Trend-following works best
        - TRENDING_DOWN: Trend-following works best
        - VOLATILE: Reduce position size
        - LIQUIDITY_VACUUM: Stop trading
    """
    
    def __init__(self):
        self.regime_names = {
            'RANGING': 0,
            'TRENDING_UP': 1,
            'TRENDING_DOWN': 2,
            'VOLATILE': 3,
            'LIQUIDITY_VACUUM': 4
        }
        
        self.current_regime = 'RANGING'
        self.regime_history = []
        self.confidence = 0.5
        
        # Rolling windows
        self.price_window = []
        self.volatility_window = []
        self.liquidity_window = []
        
        logger.info("✅ MarketRegimeClassifier initialized")
    
    def classify(self, prices: List[float], spreads: List[float] = None, volumes: List[float] = None) -> Dict:
        """
        Classify current market regime.
        
        Returns:
            regime: str
            confidence: float (0-100)
            metrics: dict
        """
        if len(prices) < 50:
            return {'regime': 'RANGING', 'confidence': 50, 'metrics': {}}
        
        # Update windows
        self.price_window = prices[-100:] if len(prices) > 100 else prices
        
        # ===== 1. CALCULATE METRICS =====
        # Trend Strength (ADX-like)
        trend_strength = self._calculate_trend_strength(self.price_window)
        
        # Volatility (ATR)
        volatility = self._calculate_volatility(self.price_window)
        
        # Mean Reversion Score (Hurst Exponent)
        mean_reversion_score = self._calculate_mean_reversion(self.price_window)
        
        # Liquidity Score
        liquidity_score = self._calculate_liquidity(spreads, volumes)
        
        # ===== 2. CLASSIFY =====
        # Trending Market (Strong trend)
        if trend_strength > 0.7:
            if self.price_window[-1] > self.price_window[0]:
                regime = 'TRENDING_UP'
            else:
                regime = 'TRENDING_DOWN'
            confidence = min(95, 70 + trend_strength * 25)
            
        # Volatile Market
        elif volatility > 0.05:
            regime = 'VOLATILE'
            confidence = min(95, 70 + (volatility - 0.03) * 500)
            
        # Liquidity Vacuum
        elif liquidity_score < 0.3:
            regime = 'LIQUIDITY_VACUUM'
            confidence = min(95, 70 + (1 - liquidity_score) * 50)
            
        # Ranging Market (Mean Reversion)
        elif mean_reversion_score > 0.6:
            regime = 'RANGING'
            confidence = min(95, 70 + mean_reversion_score * 30)
            
        else:
            regime = 'RANGING'
            confidence = 50
        
        # ===== 3. UPDATE HISTORY =====
        self.current_regime = regime
        self.confidence = confidence
        
        self.regime_history.append({
            'timestamp': datetime.now(),
            'regime': regime,
            'confidence': confidence
        })
        
        if len(self.regime_history) > 1000:
            self.regime_history.pop(0)
        
        # ===== 4. LOG =====
        logger.info(f"📊 Regime: {regime} ({confidence:.0f}%)")
        logger.info(f"   Trend: {trend_strength:.3f} | Vol: {volatility:.3f} | MeanRev: {mean_reversion_score:.3f}")
        
        return {
            'regime': regime,
            'confidence': round(confidence, 1),
            'trend_strength': round(trend_strength, 3),
            'volatility': round(volatility, 4),
            'mean_reversion_score': round(mean_reversion_score, 3),
            'liquidity_score': round(liquidity_score, 3),
            'regime_code': self.regime_names[regime]
        }
    
    def _calculate_trend_strength(self, prices: List[float]) -> float:
        """Calculate trend strength (0-1)."""
        if len(prices) < 20:
            return 0.5
        
        try:
            x = np.arange(len(prices))
            y = np.array(prices)
            
            # Linear regression
            slope, intercept = np.polyfit(x, y, 1)
            
            # R-squared
            y_pred = slope * x + intercept
            ss_total = np.sum((y - np.mean(y)) ** 2)
            ss_res = np.sum((y - y_pred) ** 2)
            r_squared = 1 - (ss_res / ss_total) if ss_total > 0 else 0
            
            # Normalize slope
            normalized_slope = abs(slope) / (np.mean(y) + 1e-8) * 100
            
            return min(1, r_squared * normalized_slope * 0.5)
            
        except Exception as e:
            logger.debug(f"Trend strength error: {e}")
            return 0.5
    
    def _calculate_volatility(self, prices: List[float]) -> float:
        """Calculate annualized volatility."""
        if len(prices) < 20:
            return 0.02
        
        returns = np.diff(np.log(np.array(prices) + 1e-8))
        return np.std(returns) * np.sqrt(252)
    
    def _calculate_mean_reversion(self, prices: List[float]) -> float:
        """Calculate mean reversion score (0-1). Higher = more mean-reverting."""
        if len(prices) < 50:
            return 0.5
        
        try:
            returns = np.diff(np.log(np.array(prices) + 1e-8))
            
            # Hurst Exponent
            lags = range(2, min(20, len(returns) // 3))
            tau = []
            
            for lag in lags:
                if len(returns) > lag:
                    diff = np.subtract(returns[lag:], returns[:-lag])
                    tau.append(np.std(diff))
            
            if len(tau) > 0 and np.std(tau) > 0:
                hurst = np.polyfit(np.log(lags[:len(tau)]), np.log(tau), 1)[0]
                # Hurst < 0.5 = mean-reverting, > 0.5 = trending
                mean_reversion_score = max(0, min(1, 1 - hurst))
            else:
                mean_reversion_score = 0.5
                
        except Exception as e:
            logger.debug(f"Mean reversion error: {e}")
            mean_reversion_score = 0.5
        
        return mean_reversion_score
    
    def _calculate_liquidity(self, spreads: List[float] = None, volumes: List[float] = None) -> float:
        """Calculate liquidity score (0-1). Higher = more liquid."""
        # Default liquidity score
        default_score = 0.7
        
        if spreads and len(spreads) > 0:
              try:
                    avg_spread = np.mean(spreads[-20:])
                    # Normalize: typical spread < 0.0002 = good liquidity
                    # Ensure score is between 0 and 1
                    if avg_spread <= 0:
                        return default_score
                    
                    # Calculate score (inverse of spread)
                    raw_score = 1 - (avg_spread / 0.001)  # 0.001 is max acceptable spread
                    score = max(0.0, min(1.0, raw_score))  # Clamp to 0-1
                    return score
              except:
                    pass
        
        # If no spread data, try volume
        if volumes and len(volumes) > 0:
              try:
                    avg_volume = np.mean(volumes[-20:])
                    # Normalize: typical volume > 1000 = good liquidity
                    raw_score = min(1.0, avg_volume / 5000)
                    return max(0.3, raw_score)  # Minimum 0.3
              except:
                    pass
        
        # Return default if no data
        return default_score
    def get_status(self) -> Dict:
        """Get current regime status."""
        return {
            'regime': self.current_regime,
            'confidence': self.confidence,
            'history_length': len(self.regime_history)
        }