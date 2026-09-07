# ============================================================
# deviation_monitor.py - Deviation Detection & Monitoring
# ============================================================
# Detects when data is stale or Z-score is stuck at 0
# ============================================================

import numpy as np
from typing import Dict, List, Optional
from datetime import datetime, timedelta
import logging

logger = logging.getLogger(__name__)


class DeviationMonitor:
    """
    Monitors data freshness and Z-score deviations.
    
    Triggers refresh if Z-score stays at 0 for too long.
    """
    
    def __init__(self, max_stall_seconds: int = 60):
        self.max_stall_seconds = max_stall_seconds
        self.symbol_history = {}
        self.alert_triggered = False
        self.last_refresh = datetime.now()
        
        logger.info(f"✅ DeviationMonitor initialized (max stall: {max_stall_seconds}s)")
    
    def update_symbol(self, symbol: str, z_score: float, price: float):
        """Update symbol data."""
        if symbol not in self.symbol_history:
            self.symbol_history[symbol] = {
                'z_scores': [],
                'prices': [],
                'timestamps': []
            }
        
        history = self.symbol_history[symbol]
        history['z_scores'].append(z_score)
        history['prices'].append(price)
        history['timestamps'].append(datetime.now())
        
        # Keep limited history
        if len(history['z_scores']) > 100:
            history['z_scores'] = history['z_scores'][-100:]
            history['prices'] = history['prices'][-100:]
            history['timestamps'] = history['timestamps'][-100:]
    
    def check_stall(self, symbol: str) -> Dict:
        """Check if Z-score is stalled for a symbol."""
        if symbol not in self.symbol_history:
            return {'is_stalled': False, 'reason': 'No data'}
        
        history = self.symbol_history[symbol]
        if len(history['z_scores']) < 5:
            return {'is_stalled': False, 'reason': 'Insufficient data'}
        
        # Check if Z-score is stuck at 0
        recent_z = history['z_scores'][-10:]
        all_zero = all(abs(z) < 0.01 for z in recent_z)
        
        if all_zero:
            # Check if we have price changes (market might be moving but Z is stuck)
            recent_prices = history['prices'][-10:]
            price_changed = len(set(recent_prices)) > 1
            
            if price_changed:
                return {
                    'is_stalled': True,
                    'reason': f'Z-score stuck at 0 while price moves ({recent_prices[-1]} vs {recent_prices[0]})'
                }
            
            # Check time elapsed
            last_time = history['timestamps'][-1]
            elapsed = (datetime.now() - last_time).seconds
            
            if elapsed > self.max_stall_seconds:
                return {
                    'is_stalled': True,
                    'reason': f'No new data for {elapsed}s'
                }
        
        return {'is_stalled': False, 'reason': 'Normal operation'}
    
    def check_all_symbols(self, symbols: List[str]) -> Dict:
        """Check all symbols for stalls."""
        results = {}
        stalled_symbols = []
        
        for symbol in symbols:
            result = self.check_stall(symbol)
            results[symbol] = result
            if result['is_stalled']:
                stalled_symbols.append(symbol)
        
        if stalled_symbols and not self.alert_triggered:
            self.alert_triggered = True
            logger.warning(f"🔴 STALL DETECTED: {len(stalled_symbols)} symbols stalled")
            for symbol in stalled_symbols:
                logger.warning(f"   - {symbol}: {results[symbol]['reason']}")
            
            # Trigger refresh
            self._trigger_refresh()
        
        elif not stalled_symbols:
            self.alert_triggered = False
        
        return {
            'stalled_symbols': stalled_symbols,
            'results': results,
            'need_refresh': len(stalled_symbols) > 0,
            'last_refresh': self.last_refresh
        }
    
    def _trigger_refresh(self):
        """Trigger data refresh."""
        self.last_refresh = datetime.now()
        # Try to refresh MT4 connection
        try:
            from mt4_price_provider import get_mt4_prices
            mt4 = get_mt4_prices()
            if mt4:
                mt4._send({"command": "PING"})
                logger.info("🔄 MT4 connection refreshed")
        except Exception as e:
            logger.warning(f"⚠️ Refresh failed: {e}")
    
    def get_status(self) -> Dict:
        """Get monitor status."""
        return {
            'alert_triggered': self.alert_triggered,
            'last_refresh': self.last_refresh.isoformat(),
            'stalled_count': sum(
                1 for h in self.symbol_history.values()
                if len(h['z_scores']) > 5 and all(abs(z) < 0.01 for z in h['z_scores'][-10:])
            ),
            'total_symbols': len(self.symbol_history)
        }