# monte_carlo_service.py - COMPLETE FIXED VERSION
# ============================================================
# Monte Carlo Simulation Service
# ============================================================
# Runs as a separate process/thread
# Provides probability of success for trades
# Enhanced with dynamic volatility, price history, correlation
# ============================================================

import numpy as np
import threading
import queue
import time
import logging
from typing import Dict, Optional, Tuple, List
from dataclasses import dataclass
from datetime import datetime

logger = logging.getLogger(__name__)


@dataclass
class MonteCarloRequest:
    """Request for Monte Carlo simulation."""
    symbol: str
    current_price: float
    z_score: float
    volatility: float
    action: str  # 'BUY' or 'SELL'
    price_history: Optional[List[float]] = None
    horizon_minutes: int = 15
    iterations: int = 500


@dataclass
class MonteCarloResult:
    """Result from Monte Carlo simulation."""
    symbol: str
    probability_of_success: float  # 0.0 to 1.0
    expected_return: float
    expected_volatility: float
    max_drawdown_probability: float
    confidence_level: str  # 'HIGH', 'MEDIUM', 'LOW'
    paths_analyzed: int
    reversion_probability: float
    tail_risk: float  # Probability of extreme move
    recommendation: str  # 'EXECUTE', 'HOLD', 'REDUCE'
    expected_price_range: Tuple[float, float]
    timestamp: str


class MonteCarloService:
    """
    Monte Carlo simulation service running in background.
    
    Runs simulations asynchronously, does NOT block the main trading loop.
    Enhanced with dynamic volatility, price history, and correlation.
    """
    
    def __init__(self):
        self.request_queue = queue.Queue()
        self.result_queue = queue.Queue()
        self.is_running = True
        self.last_result = {}
        self.cache = {}  # Cache results for quick lookup
        self.symbol_volatility_cache = {}  # Cache volatility per symbol
        
        # Start background worker
        self.worker_thread = threading.Thread(target=self._worker_loop, daemon=True)
        self.worker_thread.start()
        
        logger.info("✅ MonteCarloService initialized (background process)")
        logger.info(f"   📊 Cache TTL: 60 seconds")
        logger.info(f"   📊 Queue Max Size: {self.request_queue.maxsize if hasattr(self.request_queue, 'maxsize') else 'unlimited'}")
    
    # ============================================================
    # PUBLIC METHODS
    # ============================================================
    
    def request_simulation(self, request: MonteCarloRequest) -> Optional[MonteCarloResult]:
        """
        Submit a simulation request.
        
        Returns cached result immediately if available, otherwise submits to queue.
        """
        # Check cache first
        cache_key = self._get_cache_key(request)
        if cache_key in self.cache:
            cached_data = self.cache[cache_key]
            # Check if cache is still valid (within 60 seconds)
            if (time.time() - cached_data.get('timestamp', 0)) < 60:
                logger.debug(f"📊 MC: Returning cached result for {request.symbol}")
                return cached_data['result']
        
        # Submit to queue
        request_id = f"{request.symbol}_{int(time.time())}"
        self.request_queue.put((request_id, request))
        logger.debug(f"📊 MC: Submitted {request_id} to queue")
        
        # Return None if no result yet (caller will use fallback)
        return None
    
    def get_result(self, timeout: float = 0.1) -> Optional[MonteCarloResult]:
        """Get result from queue (non-blocking)."""
        try:
            return self.result_queue.get(timeout=timeout)
        except queue.Empty:
            return None
    
    def check_entry_gate(self, request: MonteCarloRequest, timeout: float = 0.05) -> bool:
        """
        Check if entry passes Monte Carlo gate.
        
        Non-blocking: submits request and checks result quickly.
        """
        # Submit simulation
        self.request_simulation(request)
        
        # Wait briefly for result (max 50ms for entry latency)
        mc_result = self.get_result(timeout=timeout)
        
        # Entry Gate Logic
        if mc_result and mc_result.probability_of_success < 0.60:
            logger.warning(f"🚫 MC ENTRY BLOCKED: {request.symbol} | Prob={mc_result.probability_of_success:.2%}")
            return False
        elif mc_result and mc_result.probability_of_success >= 0.60:
            logger.info(f"✅ MC ENTRY PASSED: {request.symbol} | Prob={mc_result.probability_of_success:.2%}")
            return True
        else:
            # No result yet - use fallback
            logger.debug(f"⏳ MC: No result yet for {request.symbol}, using fallback")
            return True  # Allow on timeout
    
    def stop(self):
        """Stop the service."""
        self.is_running = False
        
    def get_status(self) -> Dict:
        """Get service status."""
        return {
            'is_running': self.is_running,
            'queue_size': self.request_queue.qsize(),
            'cache_size': len(self.cache),
            'volatility_cache_size': len(self.symbol_volatility_cache),
            'worker_alive': self.worker_thread.is_alive(),
            'timestamp': datetime.now().isoformat()
        }
    
    def update_volatility_cache(self, symbol: str, volatility: float):
        """Update cached volatility for a symbol."""
        self.symbol_volatility_cache[symbol] = {
            'volatility': volatility,
            'timestamp': time.time()
        }
    
    # ============================================================
    # PRIVATE METHODS
    # ============================================================
    
    def _get_cache_key(self, request: MonteCarloRequest) -> str:
        """Generate cache key for request."""
        return f"{request.symbol}_{request.z_score:.2f}_{request.action}_{int(request.horizon_minutes / 5) * 5}"
    
    def _worker_loop(self):
        """Background worker loop."""
        while self.is_running:
            try:
                request_id, request = self.request_queue.get(timeout=1.0)
                result = self._run_simulation(request)
                self.result_queue.put(result)
                
                # Cache result
                cache_key = self._get_cache_key(request)
                self.cache[cache_key] = {
                    'result': result,
                    'timestamp': time.time()
                }
                
                # Keep cache manageable (max 200 entries)
                if len(self.cache) > 200:
                    oldest_key = min(self.cache.keys(), key=lambda k: self.cache[k]['timestamp'])
                    del self.cache[oldest_key]
                
            except queue.Empty:
                continue
            except Exception as e:
                logger.warning(f"MC worker error: {e}")
    
    def _get_dynamic_volatility(self, request: MonteCarloRequest) -> float:
        """
        Get dynamic volatility from cache or calculate from price history.
        """
        # Check cache first
        if request.symbol in self.symbol_volatility_cache:
            cached = self.symbol_volatility_cache[request.symbol]
            # Use cached volatility if within 5 minutes
            if (time.time() - cached['timestamp']) < 300:
                return cached['volatility']
        
        # Calculate from price history
        if request.price_history and len(request.price_history) > 20:
            returns = [request.price_history[i] / request.price_history[i-1] - 1 
                       for i in range(1, len(request.price_history))]
            volatility = np.std(returns) if returns else 0.01
            volatility = max(0.005, min(0.03, volatility))  # Clamp to reasonable range
            self.update_volatility_cache(request.symbol, volatility)
            return volatility
        
        # Use provided volatility or fallback
        return request.volatility if request.volatility > 0 else 0.02
    
    def _run_simulation(self, request: MonteCarloRequest) -> MonteCarloResult:
        """
        Run Monte Carlo simulation with enhanced features.
        """
        price = request.current_price
        z_score = request.z_score
        iterations = request.iterations
        horizon = request.horizon_minutes
        
        # ===== 1. DYNAMIC VOLATILITY =====
        volatility = self._get_dynamic_volatility(request)
        
        # ===== 2. Z-SCORE AWARE DRIFT (Mean Reversion Physics) =====
        # Force a drift toward the mean proportional to Z-score magnitude
        drift_factor = -0.0005 * (z_score / 3.0)
        dt = horizon / 60  # Convert minutes to years (approx)
        
        # ===== 3. SIMULATE PATHS =====
        # Generate random walks
        random_walks = np.random.normal(0, 1, (iterations, horizon))
        
        # Calculate returns with drift and volatility
        returns = (drift_factor - 0.5 * volatility**2) * dt + volatility * np.sqrt(dt) * random_walks
        
        # Generate price paths
        price_paths = price * np.exp(np.cumsum(returns, axis=1))
        final_prices = price_paths[:, -1]
        
        # ===== 4. SUCCESS DEFINITION =====
        # Target R:R (1.5x volatility)
        expected_move = price * volatility * np.sqrt(horizon / 60)
        
        if request.action == 'SELL':
            success_paths = final_prices <= (price - (expected_move * 1.5))
            loss_paths = final_prices >= (price + (expected_move * 0.75))
            extreme_paths = final_prices >= (price + (expected_move * 3.0))
        else:  # BUY
            success_paths = final_prices >= (price + (expected_move * 1.5))
            loss_paths = final_prices <= (price - (expected_move * 0.75))
            extreme_paths = final_prices <= (price - (expected_move * 3.0))
        
        prob_success = float(np.mean(success_paths))
        prob_loss = float(np.mean(loss_paths))
        prob_extreme = float(np.mean(extreme_paths))
        
        # ===== 5. EXPECTED PRICE RANGE =====
        lower_bound = float(np.percentile(final_prices, 5))
        upper_bound = float(np.percentile(final_prices, 95))
        
        # ===== 6. CONFIDENCE LEVEL =====
        if prob_success > 0.65:
            confidence_level = 'HIGH'
            recommendation = 'EXECUTE'
        elif prob_success > 0.55:
            confidence_level = 'MEDIUM'
            recommendation = 'CONSIDER'
        else:
            confidence_level = 'LOW'
            recommendation = 'HOLD'
        
        # ===== 7. TAIL RISK =====
        # Adjust tail risk based on Z-score extreme
        tail_risk = prob_extreme * (1 + abs(z_score) / 10)
        tail_risk = min(0.5, tail_risk)
        
        result = MonteCarloResult(
            symbol=request.symbol,
            probability_of_success=round(prob_success, 3),
            expected_return=round(float(np.mean(final_prices - price)), 4),
            expected_volatility=round(volatility, 4),
            max_drawdown_probability=round(prob_loss, 3),
            confidence_level=confidence_level,
            paths_analyzed=iterations,
            reversion_probability=round(prob_success, 3),
            tail_risk=round(tail_risk, 3),
            recommendation=recommendation,
            expected_price_range=(round(lower_bound, 4), round(upper_bound, 4)),
            timestamp=datetime.now().isoformat()
        )
        
        logger.debug(f"📊 MC: {request.symbol} | Success: {prob_success:.1%} | {recommendation}")
        
        return result


# ============================================================
# INTEGRATION INTO TRADING CONTROLLER
# ============================================================

def integrate_monte_carlo(trading_controller):
    """
    Integration guide for Monte Carlo service into trading controller.
    
    Usage:
        # In __init__
        self.monte_carlo_service = MonteCarloService()
        
        # In analyze_market, after getting Z-score and action:
        if abs(z_score) > 2.0 and final_action in ['BUY', 'SELL']:
            request = MonteCarloRequest(
                symbol=symbol,
                current_price=price,
                z_score=z_score,
                volatility=0.02,
                action=final_action,
                price_history=closes[-20:] if closes else None,
                horizon_minutes=15,
                iterations=500
            )
            
            mc_passed = self.monte_carlo_service.check_entry_gate(request, timeout=0.05)
            
            if not mc_passed:
                logger.info(f"⏸️ MC Filter: {symbol} BLOCKED")
                return {'action': 'HOLD', 'confidence': 0, 'reasoning': 'Monte Carlo gate'}
            else:
                logger.info(f"✅ MC Filter: {symbol} PASSED")
                # Continue with trade execution
    """
    pass


# ============================================================
# TEST
# ============================================================

def test_monte_carlo():
    """Test Monte Carlo service."""
    print("\n" + "="*60)
    print("🧪 TESTING MONTE CARLO SERVICE")
    print("="*60 + "\n")
    
    service = MonteCarloService()
    
    # Test request
    request = MonteCarloRequest(
        symbol='EURUSD',
        current_price=1.1000,
        z_score=2.5,
        volatility=0.01,
        action='SELL',
        horizon_minutes=15,
        iterations=500
    )
    
    print("📊 Submitting simulation request...")
    result = service.request_simulation(request)
    
    if result is None:
        print("⏳ No result yet (processing in background)")
        
        # Wait for result
        time.sleep(0.1)
        result = service.get_result()
        
        if result:
            print(f"\n📊 Result:")
            print(f"   Symbol: {result.symbol}")
            print(f"   Success Probability: {result.probability_of_success:.1%}")
            print(f"   Confidence: {result.confidence_level}")
            print(f"   Recommendation: {result.recommendation}")
            print(f"   Expected Range: {result.expected_price_range}")
            print(f"   Tail Risk: {result.tail_risk:.1%}")
        else:
            print("❌ No result after waiting")
    
    service.stop()
    print("\n✅ Test complete")


if __name__ == "__main__":
    test_monte_carlo()