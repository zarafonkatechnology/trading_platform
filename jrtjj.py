#!/usr/bin/env python3
# ============================================================
# test_monte_carlo_telemetry.py - Monte Carlo Telemetry Test
# ============================================================

import logging
import time
import sys
from typing import Optional

# Configure logging with detailed format
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)

# Create logger
logger = logging.getLogger(__name__)

# ============================================================
# MONTE CARLO SERVICE (Complete Implementation)
# ============================================================

import numpy as np
import threading
import queue
from dataclasses import dataclass
from typing import Dict, Optional, Tuple

# Suppress numpy warnings for clean output
import warnings
warnings.filterwarnings('ignore')


@dataclass
class MonteCarloRequest:
    """Request for Monte Carlo simulation."""
    symbol: str
    current_price: float
    z_score: float
    volatility: float
    action: str  # 'BUY' or 'SELL'
    horizon_minutes: int = 15
    iterations: int = 10000


@dataclass
class MonteCarloResult:
    """Result from Monte Carlo simulation with telemetry data."""
    symbol: str
    probability_of_success: float
    expected_return: float
    expected_volatility: float
    max_drawdown_probability: float
    confidence_level: str
    paths_analyzed: int
    reversion_probability: float
    tail_risk: float
    recommendation: str
    
    # Telemetry data
    loss_probability: float = 0.0
    var_95: float = 0.0
    expected_shortfall: float = 0.0
    convergence_score: float = 0.0
    simulation_time_ms: float = 0.0
    entry_price_optimal: float = 0.0
    stop_loss_optimal: float = 0.0
    take_profit_optimal: float = 0.0
    
    def get_telemetry_line(self) -> str:
        """Generate a single-line telemetry summary."""
        return (
            f"🎲 MC Stats (N={self.paths_analyzed:,}): "
            f"Success={self.probability_of_success:.1%} | "
            f"Loss={self.loss_probability:.1%} | "
            f"VaR(95%)={self.var_95:.4f} | "
            f"CVaR={self.expected_shortfall:.4f} | "
            f"Convergence={self.convergence_score:.1%} | "
            f"Confidence={self.confidence_level} | "
            f"Rec={self.recommendation}"
        )
    
    def get_detailed_log(self) -> str:
        """Get detailed log for debugging."""
        return f"""
🎲 MONTE CARLO TELEMETRY:
   ─────────────────────────────────────
   Symbol:              {self.symbol}
   Paths Analyzed:      {self.paths_analyzed:,}
   Simulation Time:     {self.simulation_time_ms:.1f}ms
   Convergence Score:   {self.convergence_score:.1%}
   ─────────────────────────────────────
   Success Probability: {self.probability_of_success:.1%}
   Loss Probability:    {self.loss_probability:.1%}
   Reversion Prob:      {self.reversion_probability:.1%}
   Tail Risk:           {self.tail_risk:.1%}
   ─────────────────────────────────────
   VaR (95%):           {self.var_95:.4f}
   CVaR (Expected Loss):{self.expected_shortfall:.4f}
   ─────────────────────────────────────
   Optimal Entry:       {self.entry_price_optimal:.4f}
   Optimal Stop-Loss:   {self.stop_loss_optimal:.4f}
   Optimal Take-Profit: {self.take_profit_optimal:.4f}
   ─────────────────────────────────────
   Recommendation:      {self.recommendation}
   Confidence Level:    {self.confidence_level}
   ─────────────────────────────────────
"""


class MonteCarloService:
    """Monte Carlo simulation service with telemetry."""
    
    def __init__(self):
        self.request_queue = queue.Queue()
        self.result_queue = queue.Queue()
        self.is_running = True
        self.cache = {}
        self.simulation_stats = {
            'total_simulations': 0,
            'avg_time_ms': 0,
            'total_time_ms': 0
        }
        
        self.worker_thread = threading.Thread(target=self._worker_loop, daemon=True)
        self.worker_thread.start()
        
        logger.info("✅ MonteCarloService initialized (background process)")
        logger.info("   📊 Telemetry logging ENABLED")
        logger.info("   📊 Iterations: 10,000 paths per simulation")
    
    def request_simulation(self, request: MonteCarloRequest) -> Optional[MonteCarloResult]:
        """Submit a simulation request."""
        cache_key = f"{request.symbol}_{request.z_score:.2f}_{request.action}"
        if cache_key in self.cache:
            cached = self.cache[cache_key]
            if (time.time() - cached.get('timestamp', 0)) < 60:
                logger.debug(f"📊 MC Cache hit for {request.symbol}")
                return cached['result']
        
        self.request_queue.put((cache_key, request))
        logger.debug(f"📊 MC: Submitted {request.symbol} to queue")
        return None
    
    def get_result(self, timeout: float = 0.1) -> Optional[MonteCarloResult]:
        """Get result from queue."""
        try:
            return self.result_queue.get(timeout=timeout)
        except queue.Empty:
            return None
    
    def _worker_loop(self):
        """Background worker loop."""
        while self.is_running:
            try:
                cache_key, request = self.request_queue.get(timeout=1.0)
                start_time = time.perf_counter()
                result = self._run_simulation(request)
                elapsed_ms = (time.perf_counter() - start_time) * 1000
                
                result.simulation_time_ms = elapsed_ms
                
                self.simulation_stats['total_simulations'] += 1
                self.simulation_stats['total_time_ms'] += elapsed_ms
                self.simulation_stats['avg_time_ms'] = (
                    self.simulation_stats['total_time_ms'] / 
                    self.simulation_stats['total_simulations']
                )
                
                # Log telemetry
                logger.info(f"📊 {result.get_telemetry_line()}")
                
                self.result_queue.put(result)
                
                self.cache[cache_key] = {
                    'result': result,
                    'timestamp': time.time()
                }
                
                if len(self.cache) > 100:
                    oldest = min(self.cache.keys(), key=lambda k: self.cache[k]['timestamp'])
                    del self.cache[oldest]
                
            except queue.Empty:
                continue
            except Exception as e:
                logger.warning(f"MC worker error: {e}")
    
    def _run_simulation(self, request: MonteCarloRequest) -> MonteCarloResult:
        """Run Monte Carlo simulation with full telemetry."""
        price = request.current_price
        volatility = request.volatility
        z_score = request.z_score
        iterations = request.iterations
        horizon = request.horizon_minutes
        
        # ===== 1. SIMULATE PRICE PATHS =====
        dt = 1/60
        mu = 0.0001
        steps = horizon
        random_walks = np.random.normal(0, 1, (iterations, steps))
        returns = (mu - 0.5 * volatility**2) * dt + volatility * np.sqrt(dt) * random_walks
        cumulative_returns = np.cumsum(returns, axis=1)
        price_paths = price * np.exp(cumulative_returns)
        
        # ===== 2. CALCULATE METRICS =====
        final_prices = price_paths[:, -1]
        
        # Calculate optimal levels
        atr = volatility * price
        stop_loss_pct = 0.005
        take_profit_pct = 0.015
        
        if request.action == 'SELL':
            optimal_entry = price
            optimal_sl = price * (1 + stop_loss_pct * (1 + abs(z_score) / 10))
            optimal_tp = price * (1 - take_profit_pct * (1 + abs(z_score) / 10))
            
            success_paths = final_prices < optimal_tp
            loss_paths = final_prices > optimal_sl
            
            returns_dist = (price - final_prices) / price
            var_95 = np.percentile(returns_dist, 5)
            expected_shortfall = np.mean(returns_dist[returns_dist < var_95])
            
        else:  # BUY
            optimal_entry = price
            optimal_sl = price * (1 - stop_loss_pct * (1 + abs(z_score) / 10))
            optimal_tp = price * (1 + take_profit_pct * (1 + abs(z_score) / 10))
            
            success_paths = final_prices > optimal_tp
            loss_paths = final_prices < optimal_sl
            
            returns_dist = (final_prices - price) / price
            var_95 = np.percentile(returns_dist, 5)
            expected_shortfall = np.mean(returns_dist[returns_dist < var_95])
        
        # Calculate probabilities
        probability_of_success = np.mean(success_paths)
        loss_probability = np.mean(loss_paths)
        
        # Calculate convergence score
        batch_size = iterations // 10
        batch_success = []
        for i in range(10):
            start = i * batch_size
            end = (i + 1) * batch_size
            batch_success.append(np.mean(success_paths[start:end]))
        
        if batch_success:
            convergence_score = 1 - (np.std(batch_success) / (np.mean(batch_success) + 1e-8))
            convergence_score = min(1.0, max(0.0, convergence_score))
        else:
            convergence_score = 0.5
        
        # Determine confidence
        if probability_of_success > 0.75 and convergence_score > 0.8:
            confidence_level = 'HIGH'
            recommendation = 'EXECUTE'
        elif probability_of_success > 0.55 and convergence_score > 0.6:
            confidence_level = 'MEDIUM'
            recommendation = 'REDUCE'
        else:
            confidence_level = 'LOW'
            recommendation = 'HOLD'
        
        result = MonteCarloResult(
            symbol=request.symbol,
            probability_of_success=round(probability_of_success, 3),
            expected_return=round(np.mean(price_paths[:, -1] - price), 4),
            expected_volatility=round(np.std(price_paths[:, -1] - price), 4),
            max_drawdown_probability=round(np.mean(np.min(price_paths, axis=1) < price * 0.97), 3),
            confidence_level=confidence_level,
            paths_analyzed=iterations,
            reversion_probability=round(1 - probability_of_success, 3),
            tail_risk=round(1 - np.mean(np.abs(final_prices - price) < 2 * np.std(final_prices - price)), 3),
            recommendation=recommendation,
            loss_probability=round(loss_probability, 3),
            var_95=round(var_95, 4),
            expected_shortfall=round(expected_shortfall, 4),
            convergence_score=round(convergence_score, 3),
            simulation_time_ms=0,
            entry_price_optimal=round(optimal_entry, 4),
            stop_loss_optimal=round(optimal_sl, 4),
            take_profit_optimal=round(optimal_tp, 4)
        )
        
        return result
    
    def stop(self):
        """Stop the service."""
        self.is_running = False
    
    def get_status(self) -> Dict:
        """Get service status."""
        return {
            'is_running': self.is_running,
            'queue_size': self.request_queue.qsize(),
            'cache_size': len(self.cache),
            'worker_alive': self.worker_thread.is_alive(),
            'stats': self.simulation_stats
        }


# ============================================================
# TEST SUITE
# ============================================================

class MonteCarloTest:
    """Test suite for Monte Carlo service."""
    
    def __init__(self):
        self.monte_carlo = MonteCarloService()
        self.test_results = []
        
    def run_all_tests(self):
        """Run all test cases."""
        print("\n" + "="*70)
        print("🧪 MONTE CARLO TELEMETRY TEST SUITE")
        print("="*70)
        
        # Test 1: Basic Simulation
        self.test_basic_simulation()
        
        # Test 2: Different Market Conditions
        self.test_market_conditions()
        
        # Test 3: Cache Performance
        self.test_cache_performance()
        
        # Test 4: Extreme Volatility
        self.test_extreme_volatility()
        
        # Test 5: Convergence Analysis
        self.test_convergence_analysis()
        
        # Print Summary
        self.print_summary()
        
        # Cleanup
        self.monte_carlo.stop()
    
    def test_basic_simulation(self):
        """Test basic simulation with default parameters."""
        print("\n" + "─"*50)
        print("📊 TEST 1: Basic Simulation (BUY Signal)")
        print("─"*50)
        
        request = MonteCarloRequest(
            symbol="BTC/USD",
            current_price=75550.00,
            z_score=2.5,
            volatility=0.02,
            action="BUY",
            horizon_minutes=15,
            iterations=10000
        )
        
        # Submit request
        result = self.monte_carlo.request_simulation(request)
        
        if result is None:
            # Wait for result
            print("⏳ Waiting for simulation to complete...")
            time.sleep(0.5)
            result = self.monte_carlo.get_result()
        
        if result:
            print(result.get_detailed_log())
            self.test_results.append({
                'test': 'Basic Simulation',
                'passed': result.convergence_score > 0.8,
                'success_rate': result.probability_of_success,
                'convergence': result.convergence_score
            })
        else:
            print("❌ Failed to get result")
            self.test_results.append({
                'test': 'Basic Simulation',
                'passed': False,
                'error': 'No result'
            })
    
    def test_market_conditions(self):
        """Test different market conditions."""
        print("\n" + "─"*50)
        print("📊 TEST 2: Different Market Conditions")
        print("─"*50)
        
        test_cases = [
            ('BULL', 'BUY', 2.8, 0.015),
            ('BEAR', 'SELL', -2.8, 0.015),
            ('RANGING', 'BUY', 1.2, 0.008),
            ('NEUTRAL', 'SELL', -0.5, 0.010)
        ]
        
        for condition, action, z_score, volatility in test_cases:
            print(f"\n🔸 Condition: {condition} (Action: {action})")
            
            request = MonteCarloRequest(
                symbol="BTC/USD",
                current_price=75550.00,
                z_score=z_score,
                volatility=volatility,
                action=action,
                horizon_minutes=15,
                iterations=10000
            )
            
            result = self.monte_carlo.request_simulation(request)
            if result is None:
                time.sleep(0.3)
                result = self.monte_carlo.get_result()
            
            if result:
                print(f"   {result.get_telemetry_line()}")
                print(f"   Entry: {result.entry_price_optimal:.4f} | "
                      f"SL: {result.stop_loss_optimal:.4f} | "
                      f"TP: {result.take_profit_optimal:.4f}")
                
                self.test_results.append({
                    'test': f'Condition: {condition}',
                    'passed': result.convergence_score > 0.7,
                    'success_rate': result.probability_of_success,
                    'convergence': result.convergence_score,
                    'recommendation': result.recommendation
                })
    
    def test_cache_performance(self):
        """Test cache performance."""
        print("\n" + "─"*50)
        print("📊 TEST 3: Cache Performance")
        print("─"*50)
        
        # First request (cache miss)
        request = MonteCarloRequest(
            symbol="ETH/USD",
            current_price=3450.00,
            z_score=2.0,
            volatility=0.025,
            action="BUY",
            horizon_minutes=15,
            iterations=10000
        )
        
        print("🔄 First request (should be cache miss)...")
        start = time.perf_counter()
        result1 = self.monte_carlo.request_simulation(request)
        if result1 is None:
            time.sleep(0.3)
            result1 = self.monte_carlo.get_result()
        time1 = time.perf_counter() - start
        
        print("🔄 Second request (should be cache hit)...")
        start = time.perf_counter()
        result2 = self.monte_carlo.request_simulation(request)
        time2 = time.perf_counter() - start
        
        if result1 and result2:
            print(f"   First request time: {time1*1000:.1f}ms")
            print(f"   Second request time: {time2*1000:.1f}ms")
            print(f"   Cache speedup: {time1/time2:.1f}x")
            
            self.test_results.append({
                'test': 'Cache Performance',
                'passed': result2 is not None,
                'speedup': time1/time2,
                'convergence': result1.convergence_score
            })
    
    def test_extreme_volatility(self):
        """Test extreme volatility scenarios."""
        print("\n" + "─"*50)
        print("📊 TEST 4: Extreme Volatility Scenarios")
        print("─"*50)
        
        volatility_levels = [0.01, 0.02, 0.04, 0.08]
        
        for vol in volatility_levels:
            print(f"\n🔸 Volatility: {vol:.1%}")
            
            request = MonteCarloRequest(
                symbol="BTC/USD",
                current_price=75550.00,
                z_score=2.5,
                volatility=vol,
                action="BUY",
                horizon_minutes=15,
                iterations=10000
            )
            
            result = self.monte_carlo.request_simulation(request)
            if result is None:
                time.sleep(0.3)
                result = self.monte_carlo.get_result()
            
            if result:
                print(f"   Success: {result.probability_of_success:.1%} | "
                      f"Loss: {result.loss_probability:.1%} | "
                      f"VaR: {result.var_95:.4f} | "
                      f"Convergence: {result.convergence_score:.1%}")
                
                self.test_results.append({
                    'test': f'Volatility {vol:.1%}',
                    'passed': result.convergence_score > 0.6,
                    'success_rate': result.probability_of_success,
                    'convergence': result.convergence_score,
                    'var_95': result.var_95
                })
    
    def test_convergence_analysis(self):
        """Test convergence across different iteration counts."""
        print("\n" + "─"*50)
        print("📊 TEST 5: Convergence Analysis")
        print("─"*50)
        
        iteration_counts = [1000, 5000, 10000, 20000]
        results = []
        
        for iterations in iteration_counts:
            print(f"\n🔸 Iterations: {iterations:,}")
            
            request = MonteCarloRequest(
                symbol="BTC/USD",
                current_price=75550.00,
                z_score=2.0,
                volatility=0.02,
                action="BUY",
                horizon_minutes=15,
                iterations=iterations
            )
            
            result = self.monte_carlo.request_simulation(request)
            if result is None:
                time.sleep(0.3 * (iterations / 10000))
                result = self.monte_carlo.get_result()
            
            if result:
                print(f"   Success: {result.probability_of_success:.1%} | "
                      f"Convergence: {result.convergence_score:.1%} | "
                      f"Time: {result.simulation_time_ms:.1f}ms")
                
                results.append({
                    'iterations': iterations,
                    'convergence': result.convergence_score,
                    'time_ms': result.simulation_time_ms,
                    'success_rate': result.probability_of_success
                })
                
                self.test_results.append({
                    'test': f'Iterations {iterations:,}',
                    'passed': result.convergence_score > 0.7,
                    'convergence': result.convergence_score,
                    'time_ms': result.simulation_time_ms
                })
        
        # Print convergence summary
        print("\n📈 Convergence Summary:")
        print("-" * 60)
        print(f"{'Iterations':>12} | {'Convergence':>12} | {'Time (ms)':>12} | {'Success Rate':>12}")
        print("-" * 60)
        for r in results:
            print(f"{r['iterations']:>12,} | {r['convergence']:>11.1%} | {r['time_ms']:>11.1f} | {r['success_rate']:>11.1%}")
    
    def print_summary(self):
        """Print test summary."""
        print("\n" + "="*70)
        print("📊 TEST SUMMARY")
        print("="*70)
        
        passed = sum(1 for r in self.test_results if r.get('passed', False))
        total = len(self.test_results)
        
        print(f"\n✅ Tests Passed: {passed}/{total}")
        
        print("\n📈 Detailed Results:")
        print("-" * 80)
        for i, result in enumerate(self.test_results, 1):
            status = "✅" if result.get('passed', False) else "❌"
            name = result.get('test', 'Unknown')
            convergence = result.get('convergence', 0)
            success_rate = result.get('success_rate', 0)
            
            print(f"   {i:2}. {status} {name[:30]:<30} | "
                  f"Convergence: {convergence:.1%} | "
                  f"Success: {success_rate:.1%}")
        
        # Print service status
        status = self.monte_carlo.get_status()
        print(f"\n🔧 Service Status:")
        print(f"   Queue Size: {status['queue_size']}")
        print(f"   Cache Size: {status['cache_size']}")
        print(f"   Worker Alive: {status['worker_alive']}")
        print(f"   Total Sims: {status['stats']['total_simulations']}")
        print(f"   Avg Time: {status['stats']['avg_time_ms']:.1f}ms")


# ============================================================
# MAIN EXECUTION
# ============================================================

if __name__ == "__main__":
    try:
        test = MonteCarloTest()
        test.run_all_tests()
        
        print("\n" + "="*70)
        print("✅ All tests completed successfully!")
        print("="*70)
        
    except KeyboardInterrupt:
        print("\n\n⚠️ Tests interrupted by user")
    except Exception as e:
        print(f"\n❌ Error during tests: {e}")
        import traceback
        traceback.print_exc()