"""
Prometheus Metrics Exporter for Trading System
Exposes real-time metrics for Grafana dashboard
"""

from prometheus_client import Counter, Gauge, Histogram, generate_latest, CONTENT_TYPE_LATEST
from flask import Response
import time
from datetime import datetime
import threading

# ============================================================
# Define Prometheus Metrics
# ============================================================

# Trading metrics
trade_counter = Counter('trading_trades_total', 'Total number of trades executed', 
                        ['asset', 'action', 'outcome'])
trade_pnl = Gauge('trading_pnl', 'Current PnL', ['asset'])
daily_pnl = Gauge('trading_daily_pnl', 'Daily PnL', ['asset'])
win_rate = Gauge('trading_win_rate', 'Win rate percentage', ['asset', 'period'])

# Agent metrics
agent_votes = Counter('agent_votes_total', 'Total votes by agent', ['agent', 'vote'])
agent_confidence = Gauge('agent_confidence', 'Agent confidence score', ['agent'])
agent_win_rate = Gauge('agent_win_rate', 'Agent win rate', ['agent'])
agent_xp = Gauge('agent_xp', 'Agent XP points', ['agent'])

# Market metrics
current_price = Gauge('market_price', 'Current price', ['asset'])
market_volatility = Gauge('market_volatility', 'Current volatility', ['asset'])
market_regime = Gauge('market_regime', 'Market regime (0=trending,1=ranging,2=choppy)', ['asset'])

# System metrics
cycle_duration = Histogram('trading_cycle_duration_seconds', 'Trading cycle duration', buckets=[1,5,10,30,60,120,300])
system_uptime = Gauge('system_uptime_seconds', 'System uptime in seconds')
active_agents = Gauge('active_agents_count', 'Number of active agents')
queue_size = Gauge('alert_queue_size', 'Size of alert queue')

# Risk metrics
position_size = Gauge('position_size_percent', 'Current position size as % of capital', ['asset'])
daily_drawdown = Gauge('daily_drawdown_percent', 'Daily drawdown percentage')
max_drawdown = Gauge('max_drawdown_percent', 'Maximum drawdown percentage')

# Backtest metrics (from walk-forward)
sharpe_ratio = Gauge('sharpe_ratio', 'Sharpe ratio', ['period'])
profit_factor = Gauge('profit_factor', 'Profit factor', ['period'])

# Thread safety
metrics_lock = threading.Lock()


class MetricsCollector:
    """Collects and updates metrics from trading system"""
    
    def __init__(self):
        self.start_time = time.time()
        self.is_running = True
        self._thread = None
    
    def start(self):
        """Start background metrics collection"""
        self._thread = threading.Thread(target=self._collect_loop, daemon=True)
        self._thread.start()
        print("📊 Metrics collector started")
    
    def _collect_loop(self):
        """Background loop to update metrics"""
        while self.is_running:
            try:
                self._update_system_metrics()
                time.sleep(30)  # Update every 30 seconds
            except Exception as e:
                print(f"Metrics collection error: {e}")
    
    def _update_system_metrics(self):
        """Update system-level metrics"""
        # Update uptime
        system_uptime.set(time.time() - self.start_time)
        
        # Update queue size (from your alert system)
        try:
            from voice_alerts import alert_queue
            queue_size.set(len(alert_queue))
        except:
            queue_size.set(0)
    
    def record_trade(self, asset: str, action: str, outcome: str, pnl: float):
        """Record a completed trade"""
        with metrics_lock:
            trade_counter.labels(asset=asset, action=action, outcome=outcome).inc()
            trade_pnl.labels(asset=asset).set(pnl)
    
    def update_daily_pnl(self, asset: str, pnl: float):
        """Update daily PnL"""
        with metrics_lock:
            daily_pnl.labels(asset=asset).set(pnl)
    
    def update_win_rate(self, asset: str, rate: float, period: str = "30d"):
        """Update win rate"""
        with metrics_lock:
            win_rate.labels(asset=asset, period=period).set(rate)
    
    def update_agent_metrics(self, agent_name: str, vote: str, confidence: float, 
                             win_rate_val: float, xp: float):
        """Update agent-specific metrics"""
        with metrics_lock:
            agent_votes.labels(agent=agent_name, vote=vote).inc()
            agent_confidence.labels(agent=agent_name).set(confidence)
            agent_win_rate.labels(agent=agent_name).set(win_rate_val)
            agent_xp.labels(agent=agent_name).set(xp)
    
    def update_market_metrics(self, asset: str, price: float, volatility: float, regime: str):
        """Update market metrics"""
        with metrics_lock:
            current_price.labels(asset=asset).set(price)
            market_volatility.labels(asset=asset).set(volatility)
            
            # Encode regime as numeric
            regime_map = {'TRENDING': 0, 'RANGING': 1, 'CHOPPY': 2, 'MIXED': 3}
            market_regime.labels(asset=asset).set(regime_map.get(regime, 3))
    
    def update_cycle_duration(self, duration_seconds: float):
        """Record trading cycle duration"""
        cycle_duration.observe(duration_seconds)
    
    def update_risk_metrics(self, position_pct: float, daily_dd: float, max_dd: float):
        """Update risk metrics"""
        with metrics_lock:
            position_size.labels(asset="all").set(position_pct)
            daily_drawdown.set(daily_dd)
            max_drawdown.set(max_dd)
    
    def update_backtest_metrics(self, sharpe: float, pf: float, period: str = "walk_forward"):
        """Update backtest metrics"""
        with metrics_lock:
            sharpe_ratio.labels(period=period).set(sharpe)
            profit_factor.labels(period=period).set(pf)
    
    def update_active_agents(self, count: int):
        """Update number of active agents"""
        active_agents.set(count)


# Global metrics collector instance
metrics_collector = MetricsCollector()


# ============================================================
# Flask Endpoint for Prometheus
# ============================================================

def register_monitoring_endpoints(app):
    """Register Prometheus metrics endpoint"""
    
    @app.route('/metrics')
    def metrics():
        """Prometheus metrics endpoint"""
        return Response(generate_latest(), mimetype=CONTENT_TYPE_LATEST)
    
    @app.route('/health')
    def health():
        """Health check endpoint"""
        return {
            'status': 'healthy',
            'timestamp': datetime.now().isoformat(),
            'uptime_seconds': time.time() - metrics_collector.start_time
        }
    
    @app.route('/metrics/collector/start', methods=['POST'])
    def start_collector():
        """Start metrics collector"""
        metrics_collector.start()
        return {'status': 'started'}
    
    print("✅ Monitoring endpoints registered at /metrics")
