"""
Execution Quality Analysis System
- Tracks slippage, latency, and fill quality
- Adjusts position sizing based on execution metrics
- Provides real-time execution feedback
"""

import json
import os
import time
import numpy as np
from collections import deque
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass, field
import threading


@dataclass
class ExecutionRecord:
    """Single execution record"""
    timestamp: datetime
    asset: str
    order_type: str  # MARKET, LIMIT, STOP
    requested_price: float
    filled_price: float
    slippage_pips: float
    slippage_pct: float
    latency_ms: float
    order_size: float
    filled_size: float
    partial_fill: bool
    venue: str  # OANDA, DARK_POOL, etc.
    success: bool
    error_message: str = ""


@dataclass
class BrokerMetrics:
    """Broker-specific performance metrics"""
    avg_latency_ms: float = 0
    avg_slippage_pips: float = 0
    fill_rate_pct: float = 100
    partial_fill_rate: float = 0
    total_orders: int = 0
    failed_orders: int = 0
    last_update: datetime = field(default_factory=datetime.now)


class ExecutionAnalyzer:
    """
    Analyzes execution quality to provide:
    - Slippage statistics per asset and time of day
    - Latency tracking for order routing
    - Fill rate analysis
    - Dynamic position sizing adjustments
    """
    
    def __init__(self, history_size: int = 1000):
        self.history: deque = deque(maxlen=history_size)
        self.asset_stats: Dict[str, List[ExecutionRecord]] = {}
        self.broker_stats: Dict[str, BrokerMetrics] = {}
        self.time_of_day_stats: Dict[int, List[float]] = {h: [] for h in range(24)}
        self.market_condition_stats: Dict[str, List[float]] = {
            'NORMAL': [], 'HIGH_VOLATILITY': [], 'LOW_VOLATILITY': [],
            'NEWS': [], 'SESSION_OPEN': [], 'SESSION_CLOSE': []
        }
        self.lock = threading.Lock()
        self.history_file = "execution_history.json"
        self._load_history()
    
    def _load_history(self):
        """Load execution history from disk"""
        if os.path.exists(self.history_file):
            try:
                with open(self.history_file, 'r') as f:
                    data = json.load(f)
                    for record in data.get('records', []):
                        self.history.append(ExecutionRecord(**record))
                print(f"📊 Loaded {len(self.history)} execution records")
            except Exception as e:
                print(f"Failed to load execution history: {e}")
    
    def _save_history(self):
        """Save execution history to disk"""
        try:
            data = {
                'timestamp': datetime.now().isoformat(),
                'records': [
                    {
                        'timestamp': r.timestamp.isoformat(),
                        'asset': r.asset,
                        'order_type': r.order_type,
                        'requested_price': r.requested_price,
                        'filled_price': r.filled_price,
                        'slippage_pips': r.slippage_pips,
                        'slippage_pct': r.slippage_pct,
                        'latency_ms': r.latency_ms,
                        'order_size': r.order_size,
                        'filled_size': r.filled_size,
                        'partial_fill': r.partial_fill,
                        'venue': r.venue,
                        'success': r.success,
                        'error_message': r.error_message
                    }
                    for r in list(self.history)[-500:]
                ]
            }
            with open(self.history_file, 'w') as f:
                json.dump(data, f, indent=2)
        except Exception as e:
            print(f"Failed to save execution history: {e}")
    
    def record_execution(self, execution: ExecutionRecord):
        """Record an execution for analysis"""
        with self.lock:
            self.history.append(execution)
            
            # Update asset stats
            if execution.asset not in self.asset_stats:
                self.asset_stats[execution.asset] = []
            self.asset_stats[execution.asset].append(execution)
            
            # Update time-of-day stats
            hour = execution.timestamp.hour
            self.time_of_day_stats[hour].append(execution.slippage_pips)
            
            # Keep only last 100 per hour
            if len(self.time_of_day_stats[hour]) > 100:
                self.time_of_day_stats[hour] = self.time_of_day_stats[hour][-100:]
            
            # Update broker stats
            if execution.venue not in self.broker_stats:
                self.broker_stats[execution.venue] = BrokerMetrics()
            
            broker = self.broker_stats[execution.venue]
            broker.total_orders += 1
            if not execution.success:
                broker.failed_orders += 1
            
            # Update rolling averages (exponential smoothing)
            alpha = 0.1
            broker.avg_latency_ms = alpha * execution.latency_ms + (1 - alpha) * broker.avg_latency_ms
            broker.avg_slippage_pips = alpha * abs(execution.slippage_pips) + (1 - alpha) * broker.avg_slippage_pips
            
            if execution.partial_fill:
                broker.partial_fill_rate = alpha * 1 + (1 - alpha) * broker.partial_fill_rate
            
            broker.fill_rate_pct = 100 * (broker.total_orders - broker.failed_orders) / broker.total_orders
            broker.last_update = datetime.now()
            
            # Auto-save every 50 records
            if len(self.history) % 50 == 0:
                self._save_history()
    
    def get_asset_slippage(self, asset: str, lookback_hours: int = 24) -> Dict:
        """Get slippage statistics for a specific asset"""
        cutoff = datetime.now() - timedelta(hours=lookback_hours)
        relevant = [r for r in self.asset_stats.get(asset, []) 
                   if r.timestamp >= cutoff and r.success]
        
        if not relevant:
            return {
                'avg_slippage_pips': 0,
                'avg_slippage_pct': 0,
                'max_slippage': 0,
                'sample_count': 0,
                'reliable': False
            }
        
        slippages = [r.slippage_pips for r in relevant]
        return {
            'avg_slippage_pips': np.mean(slippages),
            'std_slippage_pips': np.std(slippages),
            'avg_slippage_pct': np.mean([r.slippage_pct for r in relevant]),
            'max_slippage': max(slippages),
            'min_slippage': min(slippages),
            'sample_count': len(relevant),
            'reliable': len(relevant) >= 20
        }
    
    def get_time_of_day_slippage(self, hour: int = None) -> Dict:
        """Get slippage by time of day"""
        if hour is not None:
            slippages = self.time_of_day_stats.get(hour, [])
            return {
                'hour': hour,
                'avg_slippage': np.mean(slippages) if slippages else 0,
                'sample_count': len(slippages),
                'is_best': len(slippages) > 0 and np.mean(slippages) == min(
                    [np.mean(self.time_of_day_stats.get(h, [0])) for h in range(24) if self.time_of_day_stats.get(h)]
                ) if slippages else False
            }
        
        # Return all hours
        return {
            h: {
                'avg_slippage': np.mean(self.time_of_day_stats.get(h, [0])),
                'sample_count': len(self.time_of_day_stats.get(h, []))
            }
            for h in range(24)
        }
    
    def get_broker_metrics(self, venue: str = None) -> Dict:
        """Get broker performance metrics"""
        if venue:
            broker = self.broker_stats.get(venue)
            if broker:
                return {
                    'venue': venue,
                    'avg_latency_ms': round(broker.avg_latency_ms, 1),
                    'avg_slippage_pips': round(broker.avg_slippage_pips, 3),
                    'fill_rate': round(broker.fill_rate_pct, 1),
                    'partial_fill_rate': round(broker.partial_fill_rate * 100, 1),
                    'total_orders': broker.total_orders,
                    'failed_orders': broker.failed_orders
                }
            return {'venue': venue, 'error': 'No data'}
        
        # Return all venues
        return {v: self.get_broker_metrics(v) for v in self.broker_stats.keys()}
    
    def get_slippage_adjustment(self, asset: str, order_size: float = None) -> float:
        """
        Calculate position size multiplier based on recent slippage.
        
        Returns:
            Multiplier between 0.5 and 1.0 (reduce size if slippage is high)
        """
        stats = self.get_asset_slippage(asset, lookback_hours=24)
        
        if not stats['reliable']:
            return 1.0
        
        # Base adjustment on average slippage
        # Target: keep slippage under 0.05% of position value
        target_slippage_pct = 0.0005
        
        if stats['avg_slippage_pct'] <= 0:
            return 1.0
        
        ratio = target_slippage_pct / stats['avg_slippage_pct']
        multiplier = min(1.0, max(0.5, ratio))
        
        # Additional adjustment for high volatility periods
        hour = datetime.now().hour
        hour_slippage = self.get_time_of_day_slippage(hour)
        if hour_slippage['avg_slippage'] > stats['avg_slippage_pips'] * 1.5:
            multiplier *= 0.8
        
        return round(multiplier, 2)
    
    def get_latency_adjustment(self, venue: str = 'MT4') -> float:
        """
        Calculate adjustment based on order latency.
        High latency = reduce position size (market may move before fill)
        """
        metrics = self.get_broker_metrics(venue)
        if 'error' in metrics:
            return 1.0
        
        avg_latency = metrics.get('avg_latency_ms', 0)
        
        # Target latency < 100ms
        if avg_latency <= 50:
            return 1.0
        elif avg_latency <= 100:
            return 0.95
        elif avg_latency <= 200:
            return 0.85
        elif avg_latency <= 500:
            return 0.7
        else:
            return 0.5
    
    def get_fill_quality_score(self, asset: str) -> float:
        """
        Calculate fill quality score (0-100) for an asset.
        Higher score = better execution conditions.
        """
        stats = self.get_asset_slippage(asset)
        broker = self.get_broker_metrics('MT4')
        
        score = 100
        
        # Slippage penalty
        if stats['reliable']:
            slippage_penalty = min(30, stats['avg_slippage_pips'] * 100)
            score -= slippage_penalty
        
        # Latency penalty
        if 'avg_latency_ms' in broker:
            latency_penalty = min(20, broker['avg_latency_ms'] / 10)
            score -= latency_penalty
        
        # Fill rate penalty
        if 'fill_rate' in broker:
            fill_penalty = (100 - broker['fill_rate']) / 2
            score -= fill_penalty
        
        return max(0, min(100, score))
    
    def get_recommendation(self, asset: str, order_size: float = None) -> Dict:
        """
        Get execution recommendation for an order.
        """
        slippage_mult = self.get_slippage_adjustment(asset, order_size)
        latency_mult = self.get_latency_adjustment()
        quality_score = self.get_fill_quality_score(asset)
        
        # Determine best time to execute
        hour_slippage = self.get_time_of_day_slippage()
        best_hours = sorted(
            [(h, data['avg_slippage']) for h, data in hour_slippage.items() if data['sample_count'] > 5],
            key=lambda x: x[1]
        )[:3]
        
        recommendation = {
            'asset': asset,
            'position_multiplier': round(slippage_mult * latency_mult, 2),
            'quality_score': round(quality_score, 1),
            'is_good_time': quality_score > 70,
            'best_hours': [{'hour': h, 'avg_slippage': round(s, 3)} for h, s in best_hours],
            'suggested_action': None
        }
        
        if quality_score < 50:
            recommendation['suggested_action'] = 'REDUCE_SIZE'
        elif quality_score < 70:
            recommendation['suggested_action'] = 'NORMAL'
        else:
            recommendation['suggested_action'] = 'AGGRESSIVE'
        
        return recommendation
    
    def get_summary_stats(self) -> Dict:
        """Get overall execution quality summary"""
        total_executions = len(self.history)
        successful = sum(1 for r in self.history if r.success)
        
        if total_executions == 0:
            return {'status': 'No data', 'total_executions': 0}
        
        avg_slippage = np.mean([abs(r.slippage_pips) for r in self.history if r.success])
        avg_latency = np.mean([r.latency_ms for r in self.history if r.success])
        partial_fills = sum(1 for r in self.history if r.partial_fill)
        
        return {
            'total_executions': total_executions,
            'success_rate': round(successful / total_executions * 100, 1),
            'avg_slippage_pips': round(avg_slippage, 3),
            'avg_latency_ms': round(avg_latency, 1),
            'partial_fill_rate': round(partial_fills / total_executions * 100, 1),
            'top_assets': sorted(
                [(a, len(r)) for a, r in self.asset_stats.items()],
                key=lambda x: x[1], reverse=True
            )[:5]
        }


# ============================================================
# Integration with Trading System
# ============================================================

class ExecutionQualityIntegration:
    """Integrates execution quality with your trading system"""
    
    def __init__(self):
        self.analyzer = ExecutionAnalyzer()
        self.telegram_bot = None
    
    def set_telegram_bot(self, bot):
        self.telegram_bot = bot
    
    def before_trade(self, asset: str, order_size: float, order_type: str = 'MARKET') -> Dict:
        """Get execution recommendations before trading"""
        rec = self.analyzer.get_recommendation(asset, order_size)
        return rec
    
    def after_trade(self, execution: ExecutionRecord):
        """Record execution after trade"""
        self.analyzer.record_execution(execution)
        
        # Send alert for poor execution
        if execution.slippage_pips > 0.5:  # More than 0.5 pips slippage
            if self.telegram_bot:
                self.telegram_bot.send_message(
                    f"⚠️ Poor execution on {execution.asset}: "
                    f"slippage {execution.slippage_pips:.2f} pips, "
                    f"latency {execution.latency_ms:.0f}ms"
                )
    
    def get_position_multiplier(self, asset: str) -> float:
        """Get position size multiplier based on execution quality"""
        rec = self.analyzer.get_recommendation(asset)
        return rec['position_multiplier']
    
    def get_status_message(self) -> str:
        """Get formatted status message for Telegram"""
        summary = self.analyzer.get_summary_stats()
        
        if summary['total_executions'] == 0:
            return "📊 No execution data yet. Place some trades to collect data."
        
        message = f"""
📊 *EXECUTION QUALITY REPORT*

📈 *Overall Stats:*
   • Total Executions: {summary['total_executions']}
   • Success Rate: {summary['success_rate']}%
   • Avg Slippage: {summary['avg_slippage_pips']:.2f} pips
   • Avg Latency: {summary['avg_latency_ms']:.0f} ms
   • Partial Fill Rate: {summary['partial_fill_rate']:.1f}%

🎯 *Top Assets by Volume:*
"""
        for asset, count in summary['top_assets'][:5]:
            message += f"\n   • {asset}: {count} trades"
        
        return message


# ============================================================
# Test
# ============================================================

if __name__ == '__main__':
    print("=" * 60)
    print("EXECUTION QUALITY ANALYSIS - TEST")
    print("=" * 60)
    
    # Initialize
    executor = ExecutionQualityIntegration()
    analyzer = executor.analyzer
    
    # Simulate executions
    print("\n📊 Simulating executions...")
    
    np.random.seed(42)
    
    for i in range(100):
        asset = np.random.choice(['EURUSD', 'XAU/USD', 'S&P500/USD'])
        requested = np.random.uniform(1.09, 1.11) if 'EUR' in asset else np.random.uniform(2350, 2420)
        
        # Simulate slippage (worse during certain hours)
        hour = datetime.now().hour
        slippage_base = 0.1 if 8 <= hour <= 16 else 0.3
        
        slippage_pips = abs(np.random.normal(slippage_base, 0.05))
        filled = requested + (np.random.choice([-1, 1]) * slippage_pips / 10000)
        
        latency = np.random.exponential(50)
        success = np.random.random() > 0.05
        
        execution = ExecutionRecord(
            timestamp=datetime.now(),
            asset=asset,
            order_type='MARKET',
            requested_price=requested,
            filled_price=filled,
            slippage_pips=abs(filled - requested) * 10000,
            slippage_pct=abs(filled - requested) / requested,
            latency_ms=latency,
            order_size=np.random.uniform(0.1, 2.0),
            filled_size=np.random.uniform(0.1, 2.0),
            partial_fill=np.random.random() < 0.05,
            venue='MT4',
            success=success
        )
        
        analyzer.record_execution(execution)
    
    # Test recommendations
    print("\n📊 Execution Recommendations:")
    for asset in ['EURUSD', 'XAU/USD', 'S&P500/USD']:
        rec = analyzer.get_recommendation(asset)
        print(f"\n{asset}:")
        print(f"   Position Multiplier: {rec['position_multiplier']}x")
        print(f"   Quality Score: {rec['quality_score']}/100")
        print(f"   Best Hours: {rec['best_hours'][:2]}")
        print(f"   Action: {rec['suggested_action']}")
    
    print("\n" + "=" * 60)
    print(executor.get_status_message())
    print("=" * 60)
    
    print("\n✅ Execution quality system ready")
