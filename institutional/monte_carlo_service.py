# ============================================================
# monte_carlo_service.py - Monte Carlo Simulation Service
# ============================================================
# Runs as a separate process/thread
# Provides probability of success for trades
# ============================================================

import numpy as np
import threading
import queue
import time
from typing import Dict, Optional, Tuple
from dataclasses import dataclass
import logging

logger = logging.getLogger(__name__)


@dataclass
class MonteCarloRequest:
    """Request for Monte Carlo simulation."""
    symbol: str
    current_price: float
    z_score: float
    volatility: float
    action: str  # 'BUY' or 'SELL'
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


class MonteCarloService:
    """
    Monte Carlo simulation service running in background.
    
    Runs simulations asynchronously, does NOT block the main trading loop.
    """
    
    def __init__(self):
        self.request_queue = queue.Queue()
        self.result_queue = queue.Queue()
        self.is_running = True
        self.last_result = {}
        self.cache = {}  # Cache results for quick lookup
        
        # Start background worker
        self.worker_thread = threading.Thread(target=self._worker_loop, daemon=True)
        self.worker_thread.start()
        
        logger.info("✅ MonteCarloService initialized (background process)")
    
    def request_simulation(self, request: MonteCarloRequest) -> Optional[MonteCarloResult]:
        """
        Submit a simulation request.
        
        Returns cached result immediately if available, otherwise submits to queue.
        """
        # Check cache first
        cache_key = f"{request.symbol}_{request.z_score:.2f}_{request.action}"
        if cache_key in self.cache:
            cached_result = self.cache[cache_key]
            # Check if cache is still valid (within 60 seconds)
            if (time.time() - cached_result.get('timestamp', 0)) < 60:
                logger.debug(f"📊 Monte Carlo: Returning cached result for {request.symbol}")
                return cached_result['result']
        
        # Submit to queue
        request_id = f"{request.symbol}_{int(time.time())}"
        self.request_queue.put((request_id, request))
        logger.debug(f"📊 Monte Carlo: Submitted {request_id} to queue")
        
        # Return None if no result yet (caller will use fallback)
        return None
    
    def get_result(self, timeout: float = 0.1) -> Optional[MonteCarloResult]:
        """Get result from queue (non-blocking)."""
        try:
            return self.result_queue.get(timeout=timeout)
        except queue.Empty:
            return None
    
    def _worker_loop(self):
        """Background worker loop."""
        while self.is_running:
            try:
                request_id, request = self.request_queue.get(timeout=1.0)
                result = self._run_simulation(request)
                self.result_queue.put(result)
                
                # Cache result
                cache_key = f"{request.symbol}_{request.z_score:.2f}_{request.action}"
                self.cache[cache_key] = {
                    'result': result,
                    'timestamp': time.time()
                }
                
                # Keep cache manageable
                if len(self.cache) > 100:
                    oldest_key = min(self.cache.keys(), key=lambda k: self.cache[k]['timestamp'])
                    del self.cache[oldest_key]
                
            except queue.Empty:
                continue
            except Exception as e:
                logger.warning(f"Monte Carlo worker error: {e}")
    
    def _run_simulation(self, request: MonteCarloRequest) -> MonteCarloResult:
        price = request.current_price
        volatility = request.volatility
        z_score = request.z_score
        
        # 1. Z-Score Aware Drift (Mean Reversion Physics)
        # Force a drift toward the mean proportional to Z-score magnitude
        drift_factor = -0.0005 * (z_score / 3.0) 
        dt = 15/60 # Horizon is 15 minutes
        
        # 2. Simulate Paths
        random_walks = np.random.normal(0, 1, (request.iterations, request.horizon_minutes))
        returns = (drift_factor - 0.5 * volatility**2) * dt + volatility * np.sqrt(dt) * random_walks
        price_paths = price * np.exp(np.cumsum(returns, axis=1))
        final_prices = price_paths[:, -1]
        
        # 3. Success defined by Target R:R (1.5x Volatility)
        expected_move = price * volatility * np.sqrt(request.horizon_minutes / 60)
        
        if request.action == 'SELL':
            success_paths = final_prices <= (price - (expected_move * 1.5))
            loss_paths = final_prices >= (price + (expected_move * 0.75))
        else: # BUY
            success_paths = final_prices >= (price + (expected_move * 1.5))
            loss_paths = final_prices <= (price - (expected_move * 0.75))
            
        prob_success = np.mean(success_paths)
        
        return MonteCarloResult(
            symbol=request.symbol,
            probability_of_success=round(prob_success, 3),
            expected_return=round(np.mean(final_prices - price), 4),
            expected_volatility=round(np.std(final_prices - price), 4),
            max_drawdown_probability=round(np.mean(loss_paths), 3),
            confidence_level='HIGH' if prob_success > 0.65 else 'LOW',
            paths_analyzed=request.iterations,
            reversion_probability=round(prob_success, 3),
            tail_risk=round(np.mean(loss_paths), 3),
            recommendation='EXECUTE' if prob_success > 0.60 else 'HOLD'
        )
        
        logger.debug(f"📊 Monte Carlo: {request.symbol} | Success: {probability_of_success:.1%} | {recommendation}")
        
        return result
    def check_entry_gate(self, symbol, price, z_score, action):
    # Submit simulation
        request = MonteCarloRequest(
                symbol=symbol,
                current_price=price,
                z_score=z_score,
                volatility=0.02, # Use your dynamic volatility source here
                action=action
        )
        
        # Non-blocking submission
        self.mc_service.request_simulation(request)
        
        # Wait briefly for result from worker (max 50ms for entry latency)
        mc_result = self.mc_service.get_result(timeout=0.05)
        
        # Entry Gate Logic
        if mc_result and mc_result.probability_of_success < 0.60:
                logger.warning(f"🚫 ENTRY BLOCKED: {symbol} | Prob={mc_result.probability_of_success:.2%}")
                return False
                
        return True
    
    def stop(self):
        """Stop the service."""
        self.is_running = False
        
    def get_status(self) -> Dict:
        """Get service status."""
        return {
            'is_running': self.is_running,
            'queue_size': self.request_queue.qsize(),
            'cache_size': len(self.cache),
            'worker_alive': self.worker_thread.is_alive()
        }


# ============================================================
# INTEGRATION INTO TRADING CONTROLLER
# ============================================================

def integrate_monte_carlo(trading_controller):
    """
    Integrate Monte Carlo service into trading controller.
    
    Usage:
        mc_service = MonteCarloService()
        
        # In analyze_market, after getting Z-score:
        if abs(z_score) > 2.5:
            request = MonteCarloRequest(
                symbol=symbol,
                current_price=price,
                z_score=z_score,
                volatility=0.02,
                action=final_action
            )
            mc_result = mc_service.request_simulation(request)
            
            if mc_result:
                if mc_result.probability_of_success < 0.6:
                    logger.info(f"⏸️ MC Filter: {mc_result.probability_of_success:.1%} success - BLOCKED")
                    return {'action': 'HOLD'}
                else:
                    logger.info(f"✅ MC Filter: {mc_result.probability_of_success:.1%} success - PASSED")
    """
    pass