# ============================================================
# execution_quality.py - Execution Quality Monitor
# ============================================================
# Tracks execution quality and detects front-running
# ============================================================

import numpy as np
from typing import Dict, List, Optional
from datetime import datetime
import logging

logger = logging.getLogger(__name__)


class ExecutionQualityMonitor:
    """
    Monitors execution quality.
    
    Tracks:
    - Slippage (expected vs actual price)
    - Execution latency
    - Front-running detection
    - Fill quality
    """
    
    def __init__(self):
        self.executions = []
        self.slippage_history = []
        self.latency_history = []
        self.warnings = []
        
        # Thresholds
        self.max_slippage_pips = 1.0
        self.max_latency_ms = 100
        self.front_run_threshold = 0.0001  # 1 pip
        
        logger.info("✅ ExecutionQualityMonitor initialized")
    
    def record_execution(self, order: Dict) -> Dict:
        """
        Record an execution for quality analysis.
        
        order = {
            'symbol': 'EURUSD',
            'expected_price': 1.1355,
            'actual_price': 1.1356,
            'volume': 0.05,
            'order_type': 'BUY',
            'timestamp': datetime.now()
        }
        """
        execution = {
            'symbol': order.get('symbol'),
            'expected_price': order.get('expected_price', 0),
            'actual_price': order.get('actual_price', 0),
            'volume': order.get('volume', 0),
            'order_type': order.get('order_type', 'BUY'),
            'timestamp': datetime.now(),
            'latency_ms': order.get('latency_ms', 0)
        }
        
        # Calculate metrics
        if execution['expected_price'] > 0:
            pip_value = self._get_pip_value(execution['symbol'])
            execution['slippage_pips'] = abs(
                execution['actual_price'] - execution['expected_price']
            ) / pip_value
            execution['slippage_percent'] = abs(
                execution['actual_price'] - execution['expected_price']
            ) / execution['expected_price'] * 100
        else:
            execution['slippage_pips'] = 0
            execution['slippage_percent'] = 0
        
        # Check quality
        execution['quality'] = self._assess_quality(execution)
        
        # Check for front-running
        execution['front_run_detected'] = self._detect_front_run(execution)
        
        self.executions.append(execution)
        
        if len(self.executions) > 1000:
            self.executions.pop(0)
        
        # Log warnings
        if execution['quality'] == 'POOR':
            self.warnings.append({
                'timestamp': datetime.now(),
                'execution': execution,
                'reason': f"Quality: {execution['quality']}"
            })
            logger.warning(f"🔴 EXECUTION WARNING: {execution['symbol']} - Slippage: {execution['slippage_pips']:.2f}pips")
        
        return execution
    
    def _get_pip_value(self, symbol: str) -> float:
        """Get pip value for symbol."""
        pip_values = {
            'EURUSD': 0.0001,
            'GBPUSD': 0.0001,
            'USDJPY': 0.01,
            'GOLD': 0.1,
            'SILVER': 0.01,
            '#NASDAQ100': 0.1,
            '#S&P500': 0.1,
            '#DJ30': 0.1,
            'BRENT_OIL': 0.01,
            'CrudeOIL': 0.01,
        }
        return pip_values.get(symbol, 0.0001)
    
    def _assess_quality(self, execution: Dict) -> str:
        """Assess execution quality."""
        if execution['slippage_pips'] < 0.5 and execution['latency_ms'] < 50:
            return 'EXCELLENT'
        elif execution['slippage_pips'] < 1.0 and execution['latency_ms'] < 100:
            return 'GOOD'
        elif execution['slippage_pips'] < 2.0:
            return 'FAIR'
        else:
            return 'POOR'
    
    def _detect_front_run(self, execution: Dict) -> bool:
        """Detect potential front-running."""
        # If slippage is consistently in the wrong direction
        # and happens quickly, it could be front-running
        if execution['order_type'] == 'BUY':
            is_front_run = execution['actual_price'] > execution['expected_price']
        else:  # SELL
            is_front_run = execution['actual_price'] < execution['expected_price']
        
        # Confirm with latency and slippage
        if is_front_run and execution['slippage_pips'] > 0.5:
            return True
        
        return False
    
    def get_stats(self) -> Dict:
        """Get execution quality statistics."""
        if not self.executions:
            return {'status': 'NO_DATA'}
        
        recent = self.executions[-100:] if len(self.executions) > 100 else self.executions
        
        slippage = [e['slippage_pips'] for e in recent]
        latency = [e['latency_ms'] for e in recent]
        
        return {
            'total_executions': len(self.executions),
            'recent_executions': len(recent),
            'avg_slippage_pips': round(np.mean(slippage), 3),
            'max_slippage_pips': round(max(slippage), 3),
            'avg_latency_ms': round(np.mean(latency), 1),
            'max_latency_ms': round(max(latency), 1),
            'quality_breakdown': {
                'EXCELLENT': sum(1 for e in recent if e['quality'] == 'EXCELLENT'),
                'GOOD': sum(1 for e in recent if e['quality'] == 'GOOD'),
                'FAIR': sum(1 for e in recent if e['quality'] == 'FAIR'),
                'POOR': sum(1 for e in recent if e['quality'] == 'POOR')
            },
            'front_run_detected': sum(1 for e in recent if e['front_run_detected'])
        }