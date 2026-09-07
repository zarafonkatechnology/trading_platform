# ============================================================
# agent_coordinator.py - CORRELATION MONITOR & KILL SWITCH
# ============================================================
# Designated as the "Supervisory Agent"
# Single task: Calculate variable correlation between SPX and NDX
# ============================================================

import numpy as np
import pandas as pd
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
import threading
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class CoordinationAgent:
    """
    Supervisory Agent - Monitors correlation and enforces safety rules.
    
    Rules:
    1. If correlation < 0.7 → Send STOP signal to ALL agents
    2. Track return time (Z=2.5 → Z=0)
    3. Enforce calibration window (9:30-9:35 AM EST)
    """
    
    def __init__(self, name="Coordinator"):
        self.name = name
        self.agent_type = "Supervisory"
        self.timeframe = "M15"
        
        # ===== FIX: Add missing attributes =====
        self.entry_threshold = 2.5
        self.exit_threshold = 0.5
        
        # Correlation tracking
        self.correlation = 1.0
        self.correlation_history = []
        self.correlation_window = 60  # 60 minutes
        
        # Return time tracking
        self.return_times = []
        self.current_reversion_start = None
        self.current_entry_z = 0
        
        # Kill switch state
        self.kill_switch_active = False
        self.kill_switch_reason = ""
        self.kill_switch_time = None
        
        # Calibration window
        self.is_calibration_window = False
        
        # Safety thresholds
        self.correlation_threshold = 0.7
        self.max_return_time_minutes = 30
        
        # Thread safety
        self.lock = threading.Lock()
        
        # Agent communication
        self.agent_signals = {}
        
        logger.info(f"✅ {self.name} initialized (Correlation Monitor + Kill Switch)")
        self.z_score = 0
        self.spread = 0
        self.beta = 1.05
    
    def calculate_and_broadcast(self, spx_price: float, ndx_price: float) -> Dict:
        """
        Calculate Z-score and broadcast to all agents.
        This is the single source of truth for spread data.
        """
        # 1. Calculate spread
        if spx_price > 0 and ndx_price > 0:
            self.spread = np.log(spx_price) - self.beta * np.log(ndx_price)
            self.spread_history.append(self.spread)
            
            if len(self.spread_history) > self.max_history:
                self.spread_history.pop(0)
        
        # 2. Calculate Z-score
        if len(self.spread_history) >= 30:
            self.mu = np.mean(self.spread_history)
            self.sigma = np.std(self.spread_history)
            if self.sigma > 0:
                self.z_score = (self.spread - self.mu) / self.sigma
        
        # 3. Broadcast to all agents
        broadcast_data = {
            'z_score': round(self.z_score, 3),
            'spread': round(self.spread, 6),
            'beta': round(self.beta, 4),
            'mu': round(self.mu, 6),
            'sigma': round(self.sigma, 6),
            'samples': len(self.spread_history),
            'timestamp': datetime.now().isoformat()
        }
        
        # 4. Update all agent's signal_data
        self.agent_signals = broadcast_data
        
        return broadcast_data
    
    def get_agent_signal_data(self) -> Dict:
        """Return Z-score data for agents."""
        return {
            'z_score': self.z_score,
            'spread': self.spread,
            'beta': self.beta,
            'mu': self.mu,
            'sigma': self.sigma,
            'samples': len(self.spread_history),
            'is_calibration_window': self.is_calibration_window,
            'kill_switch_active': self.kill_switch_active
        }
    def update_correlation(self, spx_prices: List[float], ndx_prices: List[float]) -> float:
        """
        Calculate rolling correlation between SPX and NDX.
        """
        if len(spx_prices) < 30 or len(ndx_prices) < 30:
            return self.correlation
        
        # Use last 60 minutes of data
        spx_recent = spx_prices[-self.correlation_window:]
        ndx_recent = ndx_prices[-self.correlation_window:]
        
        # Calculate returns
        spx_returns = np.diff(np.log(spx_recent))
        ndx_returns = np.diff(np.log(ndx_recent))
        
        if len(spx_returns) < 10:
            return self.correlation
        
        # Calculate Pearson correlation
        self.correlation = np.corrcoef(spx_returns, ndx_returns)[0, 1]
        self.correlation_history.append(self.correlation)
        
        # Keep history manageable
        if len(self.correlation_history) > 1000:
            self.correlation_history.pop(0)
        
        return self.correlation
    
    def check_kill_switch(self, correlation: float) -> Tuple[bool, str]:
        """
        Check if kill switch should be triggered.
        """
        with self.lock:
            if correlation < self.correlation_threshold:
                self.kill_switch_active = True
                self.kill_switch_reason = f"Correlation dropped to {correlation:.3f} < {self.correlation_threshold}"
                self.kill_switch_time = datetime.now()
                logger.warning(f"⚠️ KILL SWITCH ACTIVE: {self.kill_switch_reason}")
                return True, self.kill_switch_reason
            
            # Check if kill switch should be deactivated
            if self.kill_switch_active and correlation >= self.correlation_threshold:
                # Wait 5 minutes before deactivating
                if self.kill_switch_time and (datetime.now() - self.kill_switch_time).seconds > 300:
                    self.kill_switch_active = False
                    self.kill_switch_reason = ""
                    logger.info("✅ Kill switch deactivated - correlation restored")
            
            return self.kill_switch_active, self.kill_switch_reason
    
    def track_return_time(self, z_score: float) -> Optional[float]:
        """
        Track the time it takes for Z-score to return from >2.5 to <0.5.
        Returns: Return time in minutes, or None if no reversion in progress.
        """
        # ===== FIX: Use self.entry_threshold and self.exit_threshold =====
        if abs(z_score) > self.entry_threshold:
            # Start timing
            if self.current_reversion_start is None:
                self.current_reversion_start = datetime.now()
                self.current_entry_z = z_score
                logger.info(f"⏱️ Reversion started: Z={z_score:.2f}")
            return None
        
        elif abs(z_score) < self.exit_threshold and self.current_reversion_start is not None:
            # Reversion complete
            return_time = (datetime.now() - self.current_reversion_start).seconds / 60
            self.return_times.append(return_time)
            logger.info(f"✅ Reversion complete: {return_time:.1f} minutes (Z: {self.current_entry_z:.2f} → {z_score:.2f})")
            self.current_reversion_start = None
            self.current_entry_z = 0
            return return_time
        
        # Still in reversion
        return None
    
    def check_calibration_window(self) -> bool:
        """
        Check if we're in the calibration window (9:30-9:35 AM EST).
        """
        current_time = datetime.now()
        # Convert to EST (assuming UTC-4)
        est_time = current_time - timedelta(hours=4)
        
        is_calibration = (est_time.hour == 9 and 30 <= est_time.minute < 35)
        
        if is_calibration and not self.is_calibration_window:
            logger.info("🔧 CALIBRATION WINDOW STARTED (9:30-9:35 AM EST)")
            self.is_calibration_window = True
        elif not is_calibration and self.is_calibration_window:
            logger.info("✅ Calibration window ended")
            self.is_calibration_window = False
        
        return self.is_calibration_window
    
    def check_liquidity_anomaly(self, volume: float, volume_history: List[float]) -> bool:
        """
        Detect liquidity anomalies: sudden volume spikes without price movement.
        """
        if len(volume_history) < 10:
            return False
        
        avg_volume = np.mean(volume_history[-10:])
        std_volume = np.std(volume_history[-10:])
        
        if std_volume > 0 and volume > avg_volume + 3 * std_volume:
            logger.warning(f"⚠️ Liquidity anomaly detected: Volume {volume:.0f} > {avg_volume + 3*std_volume:.0f}")
            return True
        
        return False
    
    def analyze(self, market_data: Dict) -> Dict:
        """
        Main analysis function - returns coordination signals.
        """
        spx_prices = market_data.get('spx_history', [])
        ndx_prices = market_data.get('ndx_history', [])
        spx_price = market_data.get('spx', 0)
        ndx_price = market_data.get('ndx', 0)
        z_score = market_data.get('z_score', 0)
        volume = market_data.get('volume', 0)
        volume_history = market_data.get('volume_history', [])
        
        # 1. Update correlation
        if spx_prices and ndx_prices:
            correlation = self.update_correlation(spx_prices, ndx_prices)
        else:
            correlation = self.correlation
        
        # 2. Check kill switch
        kill_active, kill_reason = self.check_kill_switch(correlation)
        
        # 3. Track return time
        return_time = self.track_return_time(z_score)
        
        # 4. Check calibration window
        is_calibration = self.check_calibration_window()
        
        # 5. Check liquidity anomaly
        liquidity_anomaly = self.check_liquidity_anomaly(volume, volume_history) if volume_history else False
        
        # 6. Build response
        response = {
            'agent': self.name,
            'correlation': round(correlation, 4),
            'kill_switch_active': kill_active,
            'kill_switch_reason': kill_reason,
            'is_calibration_window': is_calibration,
            'liquidity_anomaly': liquidity_anomaly,
            'return_time': return_time,
            'avg_return_time': np.mean(self.return_times) if self.return_times else 0,
            'return_time_count': len(self.return_times),
            'signal': 'KILL' if kill_active else ('CALIBRATE' if is_calibration else 'NORMAL'),
            'confidence': 100 if kill_active else 85 if is_calibration else 50,
            'timestamp': datetime.now().isoformat()
        }
        
        return response
    
    def get_status(self) -> Dict:
        """Return current status."""
        return {
            'name': self.name,
            'correlation': self.correlation,
            'kill_switch': self.kill_switch_active,
            'kill_reason': self.kill_switch_reason,
            'calibration_window': self.is_calibration_window,
            'return_times': len(self.return_times),
            'avg_return_time': np.mean(self.return_times) if self.return_times else 0,
            'active': True
        }


# ============================================================
# GLOBAL INSTANCE
# ============================================================

coordinator = CoordinationAgent()

if __name__ == "__main__":
    print("=" * 60)
    print("🎯 COORDINATION AGENT - TEST")
    print("=" * 60)
    
    # Simulate market data
    market_data = {
        'spx_history': [6000 + i for i in range(100)],
        'ndx_history': [22000 + i * 2 for i in range(100)],
        'spx': 6050,
        'ndx': 22200,
        'z_score': 0.5,
        'volume': 1000,
        'volume_history': [1000] * 20
    }
    
    result = coordinator.analyze(market_data)
    print(f"Correlation: {result['correlation']:.3f}")
    print(f"Kill Switch: {result['kill_switch_active']}")
    print(f"Calibration Window: {result['is_calibration_window']}")
    print(f"Signal: {result['signal']}")
    print("=" * 60)