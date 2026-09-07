# ============================================================
# liquidity_filter.py - Professional Liquidity Filter
# ============================================================
# Combines Z-score with spread width and volume for optimal entries
# ============================================================

from typing import Dict
import logging

logger = logging.getLogger(__name__)


class ProfessionalSpreadFilter:
    """
    Professional-grade spread + liquidity filter.
    Combines Z-score with spread width for optimal entries.
    """
    
    def __init__(self):
        # ===== CONFIGURATION =====
        self.max_spread_pips = {
            'FOREX': 2.0,      # Maximum 2 pips spread
            'METALS': 0.50,    # Maximum 0.5 pips spread (GOLD)
            'INDICES': 5.0,    # Maximum 5 points spread
            'ENERGY': 0.10,    # Maximum 0.10 pips spread (OIL)
        }
        
        self.spread_percentile_threshold = 0.30  # Only trade when spread < 30th percentile
        self.liquidity_window = 20  # 20 candles for calculation
        self.min_volume = 1000      # Minimum volume required
        
        # ===== TRACKING =====
        self.spread_history = {}
        self.volume_history = {}
        
        logger.info("✅ ProfessionalSpreadFilter initialized")
        logger.info(f"   Spread Percentile Threshold: {self.spread_percentile_threshold*100}%")
        logger.info(f"   Liquidity Window: {self.liquidity_window} candles")
        logger.info(f"   Min Volume: {self.min_volume}")
    
    def check_liquidity(self, symbol: str, current_spread: float, current_volume: float) -> Dict:
        """
        Check if liquidity conditions are favorable for trading.
        
        Args:
            symbol: Trading symbol (e.g., '#S&P500', 'EURUSD')
            current_spread: Current spread value
            current_volume: Current volume
            
        Returns:
            Dict with liquidity check results
        """
        # ===== 1. SPREAD WIDTH CHECK =====
        spread_ok = self._check_spread_width(symbol, current_spread)
        
        # ===== 2. SPREAD PERCENTILE CHECK =====
        spread_percentile = self._calculate_spread_percentile(symbol, current_spread)
        spread_tight = spread_percentile < self.spread_percentile_threshold
        
        # ===== 3. VOLUME CHECK =====
        volume_ok = current_volume > self.min_volume
        
        # ===== 4. SPREAD DIRECTION =====
        spread_trend = self._get_spread_trend(symbol)
        
        # ===== FINAL DECISION =====
        can_trade = spread_ok and spread_tight and volume_ok
        
        result = {
            'can_trade': can_trade,
            'spread_ok': spread_ok,
            'spread_percentile': round(spread_percentile, 3),
            'spread_tight': spread_tight,
            'volume_ok': volume_ok,
            'spread_trend': spread_trend,
            'action': 'TRADE' if can_trade else 'WAIT',
            'reason': self._get_reason(spread_ok, spread_tight, volume_ok)
        }
        
        logger.debug(f"   💧 Liquidity Check for {symbol}: {result['action']}")
        return result
    
    def _check_spread_width(self, symbol: str, current_spread: float) -> bool:
        """Check if spread is within acceptable range."""
        symbol_type = self._get_symbol_type(symbol)
        max_spread = self.max_spread_pips.get(symbol_type, 2.0)
        return current_spread <= max_spread
    
    def _calculate_spread_percentile(self, symbol: str, current_spread: float) -> float:
        """Calculate percentile of current spread vs historical."""
        if symbol not in self.spread_history:
            self.spread_history[symbol] = []
        
        # Store history
        self.spread_history[symbol].append(current_spread)
        if len(self.spread_history[symbol]) > self.liquidity_window:
            self.spread_history[symbol].pop(0)
        
        # Calculate percentile
        if len(self.spread_history[symbol]) >= 10:
            sorted_history = sorted(self.spread_history[symbol])
            lower = sorted_history[0]
            upper = sorted_history[-1]
            
            if upper > lower:
                percentile = (current_spread - lower) / (upper - lower)
                return min(1.0, max(0.0, percentile))
        
        return 0.5  # Default if not enough data
    
    def _get_spread_trend(self, symbol: str) -> str:
        """Determine if spread is narrowing or widening."""
        if symbol not in self.spread_history or len(self.spread_history[symbol]) < 10:
            return 'NEUTRAL'
        
        history = self.spread_history[symbol][-10:]
        if len(history) < 5:
            return 'NEUTRAL'
        
        # Compare first 5 vs last 5
        first_half = sum(history[:5]) / 5
        second_half = sum(history[-5:]) / 5
        
        if second_half < first_half * 0.9:
            return 'NARROWING'  # GOOD - liquidity increasing
        elif second_half > first_half * 1.1:
            return 'WIDENING'   # BAD - liquidity decreasing
        else:
            return 'STABLE'
    
    def _get_symbol_type(self, symbol: str) -> str:
        """Determine symbol type."""
        symbol_map = {
            'EURUSD': 'FOREX', 
            'GBPUSD': 'FOREX', 
            'USDJPY': 'FOREX',
            'AUDUSD': 'FOREX',
            'USDCAD': 'FOREX',
            'NZDUSD': 'FOREX',
            'GOLD': 'METALS', 
            'SILVER': 'METALS',
            '#NASDAQ100': 'INDICES', 
            '#S&P500': 'INDICES', 
            '#DJ30': 'INDICES',
            'BRENT_OIL': 'ENERGY', 
            'CrudeOIL': 'ENERGY',
        }
        return symbol_map.get(symbol, 'FOREX')
    
    def _get_reason(self, spread_ok: bool, spread_tight: bool, volume_ok: bool) -> str:
        """Return human-readable reason."""
        if spread_ok and spread_tight and volume_ok:
            return "All conditions met"
        
        reasons = []
        if not spread_ok:
            reasons.append("Spread too wide")
        if not spread_tight:
            reasons.append("Spread not tight enough (percentile)")
        if not volume_ok:
            reasons.append("Volume too low")
        
        return ", ".join(reasons)
    
    def get_stats(self, symbol: str) -> Dict:
        """Get statistics for a symbol."""
        if symbol not in self.spread_history:
            return {'spread_samples': 0}
        
        history = self.spread_history[symbol]
        return {
            'spread_samples': len(history),
            'spread_min': round(min(history), 4),
            'spread_max': round(max(history), 4),
            'spread_avg': round(sum(history) / len(history), 4),
            'spread_trend': self._get_spread_trend(symbol)
        }