# ============================================================
# resilience_tester.py - Sensitivity Analysis
# ============================================================
# Tests system resilience by varying parameters
# ============================================================

import numpy as np
from typing import Dict, List, Optional
import logging

logger = logging.getLogger(__name__)


class ResilienceTester:
    """
    Sensitivity Analysis - Tests system vulnerability.
    
    If P&L swings > 10% with 10% parameter change,
    system is over-optimized.
    """
    
    def __init__(self):
        self.sensitivity_report = {}
        self.parameter_history = {}
        
        logger.info("✅ ResilienceTester initialized")
    
    def test_sensitivity(self, trades: List[Dict], parameters: Dict) -> Dict:
        """
        Test system sensitivity to parameter changes.
        
        Args:
            trades: List of trade dictionaries with 'z_score' and 'pnl'
            parameters: Dict of parameter name -> base value
        
        Returns:
            Dict with sensitivity analysis results
        """
        results = {}
        
        for param_name, base_value in parameters.items():
            if param_name == 'z_threshold':
                results[param_name] = self._test_z_threshold_sensitivity(trades, base_value)
            elif param_name == 'position_size':
                results[param_name] = self._test_position_size_sensitivity(trades, base_value)
            elif param_name == 'stop_loss':
                results[param_name] = self._test_stop_loss_sensitivity(trades, base_value)
            elif param_name == 'take_profit':
                results[param_name] = self._test_take_profit_sensitivity(trades, base_value)
        
        self.sensitivity_report = results
        return results
    
    def _test_z_threshold_sensitivity(self, trades: List[Dict], base_threshold: float) -> Dict:
        """Test Z-threshold sensitivity."""
        if len(trades) < 20:
            return {'status': 'INSUFFICIENT_DATA'}
        
        variations = [
            ('-10%', base_threshold * 0.9),
            ('-5%', base_threshold * 0.95),
            ('+5%', base_threshold * 1.05),
            ('+10%', base_threshold * 1.1)
        ]
        
        results = []
        base_pnl = self._simulate_trades(trades, base_threshold)
        
        for label, threshold in variations:
            simulated_pnl = self._simulate_trades(trades, threshold)
            results.append({
                'label': label,
                'threshold': threshold,
                'pnl': simulated_pnl,
                'change_percent': ((simulated_pnl - base_pnl) / abs(base_pnl)) * 100 if base_pnl != 0 else 0
            })
        
        max_change = max(abs(r['change_percent']) for r in results)
        
        return {
            'base_threshold': base_threshold,
            'base_pnl': base_pnl,
            'variations': results,
            'max_change_percent': round(max_change, 1),
            'status': self._get_status(max_change)
        }
    
    def _test_position_size_sensitivity(self, trades: List[Dict], base_size: float) -> Dict:
        """Test position size sensitivity."""
        variations = [
            ('-20%', base_size * 0.8),
            ('-10%', base_size * 0.9),
            ('+10%', base_size * 1.1),
            ('+20%', base_size * 1.2)
        ]
        
        results = []
        base_pnl = sum(t.get('pnl', 0) for t in trades)
        
        for label, size in variations:
            simulated_pnl = base_pnl * (size / base_size)
            results.append({
                'label': label,
                'size': size,
                'pnl': simulated_pnl,
                'change_percent': ((simulated_pnl - base_pnl) / abs(base_pnl)) * 100 if base_pnl != 0 else 0
            })
        
        max_change = max(abs(r['change_percent']) for r in results)
        
        return {
            'base_size': base_size,
            'base_pnl': base_pnl,
            'variations': results,
            'max_change_percent': round(max_change, 1),
            'status': self._get_status(max_change)
        }
    
    def _test_stop_loss_sensitivity(self, trades: List[Dict], base_sl: float) -> Dict:
        """Test stop loss sensitivity."""
        # Implementation similar to above
        return {'status': 'IMPLEMENTATION_PENDING'}
    
    def _test_take_profit_sensitivity(self, trades: List[Dict], base_tp: float) -> Dict:
        """Test take profit sensitivity."""
        return {'status': 'IMPLEMENTATION_PENDING'}
    
    def _simulate_trades(self, trades: List[Dict], threshold: float) -> float:
        """Simulate trades with given threshold."""
        total_pnl = 0
        
        for trade in trades:
            z_score = trade.get('z_score', 0)
            pnl = trade.get('pnl', 0)
            
            if abs(z_score) > threshold:
                total_pnl += pnl
        
        return total_pnl
    
    def _get_status(self, max_change: float) -> str:
        """Get status based on max change percentage."""
        if max_change < 10:
            return '✅ STABLE'
        elif max_change < 20:
            return '⚠️ VULNERABLE'
        else:
            return '🔴 OVER-OPTIMIZED'
    
    def generate_report(self) -> str:
        """Generate a formatted report."""
        report = []
        report.append("=" * 70)
        report.append("🔬 RESILIENCE TEST REPORT")
        report.append("=" * 70)
        
        if not self.sensitivity_report:
            report.append("No sensitivity data available. Run test_sensitivity() first.")
            return "\n".join(report)
        
        for param, data in self.sensitivity_report.items():
            report.append(f"\n📊 {param.upper()}:")
            report.append(f"   Base Value: {data.get('base_threshold', data.get('base_size', 'N/A'))}")
            report.append(f"   Max Change: {data.get('max_change_percent', 'N/A')}%")
            report.append(f"   Status: {data.get('status', 'UNKNOWN')}")
            
            if 'variations' in data:
                report.append("   Variations:")
                for v in data['variations']:
                    report.append(f"      {v['label']}: {v['change_percent']:.1f}%")
        
        # Overall assessment
        vulnerable = [p for p, d in self.sensitivity_report.items() if d.get('status') == '⚠️ VULNERABLE']
        over_optimized = [p for p, d in self.sensitivity_report.items() if d.get('status') == '🔴 OVER-OPTIMIZED']
        
        report.append("\n" + "=" * 70)
        report.append("📊 OVERALL ASSESSMENT")
        report.append("=" * 70)
        
        if not vulnerable and not over_optimized:
            report.append("✅ System is RESILIENT - Parameters are stable")
            report.append("   Profit/Loss remains stable across parameter variations")
        else:
            if vulnerable:
                report.append(f"⚠️ {len(vulnerable)} VULNERABLE parameters:")
                for p in vulnerable:
                    report.append(f"   - {p}")
            if over_optimized:
                report.append(f"🔴 {len(over_optimized)} OVER-OPTIMIZED parameters:")
                for p in over_optimized:
                    report.append(f"   - {p}")
            report.append("\n   Recommendation: Reduce sensitivity or add safeguards")
        
        report.append("=" * 70)
        
        return "\n".join(report)