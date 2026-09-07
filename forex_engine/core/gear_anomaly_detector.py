# core/gear_anomaly_detector.py

import numpy as np
from collections import deque
from typing import Dict, List, Optional
import logging

logger = logging.getLogger(__name__)

class GearAnomalyDetector:
    """
    Detects anomalies in gear behavior:
    - Gear slippage (deviation from expected movement)
    - Gear disconnection (correlation breaks)
    - Gear failure (extreme deviations)
    - Liquidity sweeps
    - Stop hunting
    """
    
    def __init__(self, brokers: Dict = None, config: Dict = None):
        self.brokers = brokers or {}
        self.config = config or {}
        
        # Anomaly tracking
        self.anomaly_log = deque(maxlen=100)
        self.correlation_matrix = {}
        self.baseline_correlations = {}
        
        # Thresholds
        self.slippage_threshold = self.config.get('slippage_threshold', 0.5)  # 50% deviation
        self.correlation_break_threshold = self.config.get('correlation_break_threshold', 0.3)
        self.health_threshold = self.config.get('health_threshold', 60)
        self.critical_health_threshold = self.config.get('critical_health_threshold', 40)
        
        # History for correlation calculation
        self.price_history = {}
        self.return_history = {}
        
        # Protection flags
        self.sweep_detected = False
        self.stop_hunt_detected = False
        self.protection_active = False
        
        logger.info("✅ GearAnomalyDetector initialized")
        logger.info(f"   Slippage Threshold: {self.slippage_threshold*100}%")
        logger.info(f"   Correlation Break Threshold: {self.correlation_break_threshold}")
    
    def set_brokers(self, brokers: Dict):
        """Set brokers to monitor"""
        self.brokers = brokers
        self.price_history = {pair: deque(maxlen=100) for pair in brokers.keys()}
        self.return_history = {pair: deque(maxlen=100) for pair in brokers.keys()}
    
    def update(self, market_data: Dict) -> Dict:
        """
        Update anomaly detection with new market data
        
        Args:
            market_data: Dictionary with price data for all pairs
        
        Returns:
            Dictionary with anomaly detection results
        """
        anomalies = []
        
        # Update price history
        for pair, price in market_data.items():
            if pair in self.price_history:
                self.price_history[pair].append(price)
                
                # Calculate returns
                if len(self.price_history[pair]) >= 2:
                    prev_price = list(self.price_history[pair])[-2]
                    if prev_price > 0:
                        return_pct = (price - prev_price) / prev_price
                        self.return_history[pair].append(return_pct)
        
        # Check each broker
        for pair, broker in self.brokers.items():
            if pair in market_data:
                anomaly = self._check_broker_anomaly(pair, broker, market_data)
                if anomaly:
                    anomalies.append(anomaly)
        
        # Check correlation breaks
        correlation_anomalies = self._check_correlations()
        anomalies.extend(correlation_anomalies)
        
        # Check for liquidity sweeps
        sweep_detected = self._detect_liquidity_sweep(market_data)
        if sweep_detected:
            anomalies.append({
                'type': 'LIQUIDITY_SWEEP',
                'severity': 'CRITICAL',
                'message': 'Liquidity sweep detected - protection active',
                'timestamp': self._get_timestamp()
            })
            self.sweep_detected = True
            self.protection_active = True
        
        # Check for stop hunts
        stop_hunt = self._detect_stop_hunt(market_data)
        if stop_hunt:
            anomalies.append({
                'type': 'STOP_HUNT',
                'severity': 'CRITICAL',
                'message': 'Stop hunting detected - expect reversal',
                'timestamp': self._get_timestamp()
            })
            self.stop_hunt_detected = True
        
        # Log anomalies
        if anomalies:
            for anomaly in anomalies:
                logger.warning(f"⚠️ Anomaly Detected: {anomaly['type']} - {anomaly['message']}")
        
        return {
            'anomalies': anomalies,
            'count': len(anomalies),
            'sweep_detected': self.sweep_detected,
            'stop_hunt_detected': self.stop_hunt_detected,
            'protection_active': self.protection_active,
            'timestamp': self._get_timestamp()
        }
    
    def _check_broker_anomaly(self, pair: str, broker, market_data: Dict) -> Optional[Dict]:
        """
        Check individual broker for anomalies
        """
        # Check gear health
        gear_health = getattr(broker, 'gear_health', 100)
        
        if gear_health < self.critical_health_threshold:
            return {
                'type': 'GEAR_DISCONNECTION',
                'pair': pair,
                'severity': 'CRITICAL',
                'health': gear_health,
                'message': f'Gear {pair} disconnected! Health: {gear_health:.1f}%',
                'timestamp': self._get_timestamp()
            }
        elif gear_health < self.health_threshold:
            return {
                'type': 'LOW_HEALTH',
                'pair': pair,
                'severity': 'WARNING',
                'health': gear_health,
                'message': f'Gear {pair} health low: {gear_health:.1f}%',
                'timestamp': self._get_timestamp()
            }
        
        # Check slippage
        slippage = getattr(broker, 'slippage_detected', False)
        if slippage:
            return {
                'type': 'SLIPPAGE',
                'pair': pair,
                'severity': 'WARNING',
                'message': f'Gear {pair} slippage detected',
                'timestamp': self._get_timestamp()
            }
        
        return None
    
    def _check_correlations(self) -> List[Dict]:
        """
        Check for correlation breaks between pairs
        """
        anomalies = []
        pairs = list(self.brokers.keys())
        
        for i, pair1 in enumerate(pairs):
            for pair2 in pairs[i+1:]:
                # Calculate current correlation
                current_corr = self._calculate_correlation(pair1, pair2)
                
                if current_corr is None:
                    continue
                
                key = f"{pair1}_{pair2}"
                
                # Store baseline if first time
                if key not in self.baseline_correlations:
                    self.baseline_correlations[key] = current_corr
                    continue
                
                # Check for correlation break
                baseline = self.baseline_correlations[key]
                if abs(current_corr - baseline) > self.correlation_break_threshold:
                    anomalies.append({
                        'type': 'CORRELATION_BREAK',
                        'pair': key,
                        'severity': 'WARNING',
                        'baseline': round(baseline, 3),
                        'current': round(current_corr, 3),
                        'message': f'Correlation break: {pair1}/{pair2} ({baseline:.2f} → {current_corr:.2f})',
                        'timestamp': self._get_timestamp()
                    })
        
        return anomalies
    
    def _calculate_correlation(self, pair1: str, pair2: str) -> Optional[float]:
        """
        Calculate correlation between two pairs
        """
        if pair1 not in self.return_history or pair2 not in self.return_history:
            return None
        
        returns1 = list(self.return_history[pair1])
        returns2 = list(self.return_history[pair2])
        
        if len(returns1) < 20 or len(returns2) < 20:
            return None
        
        # Align lengths
        min_len = min(len(returns1), len(returns2))
        returns1 = returns1[-min_len:]
        returns2 = returns2[-min_len:]
        
        if min_len < 20:
            return None
        
        # Calculate correlation
        corr = np.corrcoef(returns1, returns2)[0, 1]
        
        return float(corr)
    
    def _detect_liquidity_sweep(self, market_data: Dict) -> bool:
        """
        Detect liquidity sweep (price spike above resistance or below support)
        """
        # Simplified detection
        for pair, price in market_data.items():
            if pair in self.price_history and len(self.price_history[pair]) >= 20:
                prices = list(self.price_history[pair])
                
                # Calculate recent high and low
                recent_high = max(prices[-20:])
                recent_low = min(prices[-20:])
                current = prices[-1]
                
                # Check for sweep above resistance
                if current > recent_high * 1.001:
                    # Check if it immediately reversed (sweep and reverse)
                    if len(prices) >= 3:
                        if prices[-2] > prices[-3] and prices[-1] < prices[-2]:
                            return True
                
                # Check for sweep below support
                if current < recent_low * 0.999:
                    if len(prices) >= 3:
                        if prices[-2] < prices[-3] and prices[-1] > prices[-2]:
                            return True
        
        return False
    
    def _detect_stop_hunt(self, market_data: Dict) -> bool:
        """
        Detect stop hunting (price moving to obvious stop levels)
        """
        # Simplified detection
        for pair, price in market_data.items():
            if pair in self.price_history and len(self.price_history[pair]) >= 20:
                prices = list(self.price_history[pair])
                
                # Look for aggressive move to key level
                recent_high = max(prices[-20:])
                recent_low = min(prices[-20:])
                current = prices[-1]
                
                # Check if price moved aggressively to high/low
                if current > recent_high * 0.995 or current < recent_low * 1.005:
                    # Check for high volatility
                    volatility = np.std([p for p in prices[-10:] if p > 0])
                    if volatility > 0.005:  # 0.5% volatility
                        return True
        
        return False
    
    def get_protection_status(self) -> Dict:
        """
        Get current protection status
        """
        return {
            'sweep_detected': self.sweep_detected,
            'stop_hunt_detected': self.stop_hunt_detected,
            'protection_active': self.protection_active,
            'anomaly_count': len(self.anomaly_log)
        }
    
    def reset_protection(self):
        """Reset protection flags"""
        self.sweep_detected = False
        self.stop_hunt_detected = False
        self.protection_active = False
        logger.info("🔄 Protection flags reset")
    
    def _get_timestamp(self) -> str:
        """Get current timestamp"""
        from datetime import datetime
        return datetime.now().isoformat()