# core/monte_carlo_simulator.py

import numpy as np
import random
from typing import Dict, List, Optional
from collections import deque
import logging
from datetime import datetime

logger = logging.getLogger(__name__)

class MonteCarloSimulator:
    """
    Monte Carlo Simulation Engine for Forex Trading
    Simulates price paths to determine optimal entry points and success probability
    """
    
    def __init__(self, config: Dict = None):
        self.config = config or {}
        self.n_simulations = self.config.get('n_simulations', 10000)
        self.horizon = self.config.get('horizon', 20)
        self.volatility_lookback = self.config.get('volatility_lookback', 20)
        self.confidence_level = self.config.get('confidence_level', 0.95)
        
        # Performance tracking
        self.simulation_history = deque(maxlen=100)
        self.last_results = {}
        
        logger.info("✅ MonteCarloSimulator initialized")
        logger.info(f"   Simulations: {self.n_simulations}")
        logger.info(f"   Horizon: {self.horizon} periods")
        logger.info(f"   Confidence Level: {self.confidence_level}")
    def _evaluate_outcome_improved(self, price_path: List[float], direction: str,
                               entry_price: float, stop_loss_pct: float) -> Dict:
        """
        Evaluate outcome with dynamic stop loss.
        """
        entry = price_path[0]
        max_price = max(price_path)
        min_price = min(price_path)
        final_price = price_path[-1]
        
        stop_loss = abs(entry * stop_loss_pct)
        
        if direction == 'BUY':
               pnl = final_price - entry
               max_gain = max_price - entry
               max_loss = entry - min_price
               max_drawdown = min(0, min_price - entry)
        else:  # SELL
               pnl = entry - final_price
               max_gain = entry - min_price
               max_loss = max_price - entry
               max_drawdown = min(0, entry - max_price)
        
        stop_hit = abs(max_loss) > stop_loss
        
        return {
               'pnl': pnl,
               'pnl_pct': (pnl / entry) * 100 if entry > 0 else 0,
               'max_gain': max_gain,
               'max_loss': max_loss,
               'max_drawdown': max_drawdown,
               'stop_hit': stop_hit,
               'success': pnl > 0 and not stop_hit,
               'final_price': final_price,
               'max_price': max_price,
               'min_price': min_price
        }

    def _analyze_outcomes_improved(self, outcomes: List[Dict], entry_price: float) -> Dict:
        """
        Analyze outcomes with improved metrics.
        """
        if not outcomes:
              return {
                      'win_rate': 0.0,
                      'entry_confidence': 0.0,
                      'expected_return': 0.0,
                      'max_drawdown': 0.0,
                      'risk_reward_ratio': 0.0,
                      'sharpe_ratio': 0.0,
                      'optimal_stop_loss': 0.0,
                      'optimal_take_profit': 0.0,
              }
        
        pnls = [o['pnl'] for o in outcomes]
        successes = [o['success'] for o in outcomes]
        max_drawdowns = [o['max_drawdown'] for o in outcomes]
        
        win_rate = sum(successes) / len(outcomes)
        expected_return = np.mean(pnls)
        max_drawdown = min(max_drawdowns)
        
        wins = [o['pnl'] for o in outcomes if o['pnl'] > 0]
        losses = [abs(o['pnl']) for o in outcomes if o['pnl'] < 0]
        avg_win = np.mean(wins) if wins else 0
        avg_loss = np.mean(losses) if losses else 0.01
        risk_reward_ratio = avg_win / avg_loss if avg_loss > 0 else 0
        
        # Calculate entry confidence
        entry_confidence = min(95, (
              win_rate * 0.5 +
              min(1, risk_reward_ratio / 2) * 0.3 +
              (1 - min(1, abs(max_drawdown) / abs(entry_price * 0.05))) * 0.2
        ) * 100)
        
        return {
              'win_rate': round(win_rate * 100, 1),
              'entry_confidence': round(entry_confidence, 1),
              'expected_return': round(expected_return, 4),
              'max_drawdown': round(max_drawdown, 4),
              'risk_reward_ratio': round(risk_reward_ratio, 2),
              'sharpe_ratio': round(np.mean([o.get('pnl_pct', 0) for o in outcomes]) / (np.std([o.get('pnl_pct', 0) for o in outcomes]) + 0.0001), 2),
              'optimal_stop_loss': round(abs(entry_price * 0.015), 4),
              'optimal_take_profit': round(abs(entry_price * 0.03), 4),
              'num_simulations': len(outcomes),
              'avg_pnl': round(np.mean(pnls), 4)
        }
    def simulate_entry(self, current_price: float, volatility: float = None,
                   direction: str = 'BUY', num_simulations: int = None,
                   horizon: int = None, mean_reversion: float = None,
                   price_history: List[float] = None, atr: float = None) -> Dict:
        """
        Improved Monte Carlo simulation with adaptive parameters.
        """
        num_sims = num_simulations or self.n_simulations
        horizon = horizon or self.horizon
        
        # Calculate dynamic volatility
        if volatility is None:
               volatility = self._calculate_volatility(price_history)
        
        # Calculate mean reversion if not provided
        if mean_reversion is None:
               mean_reversion = self._calculate_mean_reversion(price_history)
        
        # Calculate dynamic stop loss
        stop_loss_pct = 0.02  # Default
        if atr:
               stop_distance = self._calculate_dynamic_stop(current_price, atr)
               stop_loss_pct = stop_distance / current_price
        
        # ===== FIX: Initialize outcomes list =====
        outcomes = []
        for _ in range(num_sims):
               price_path = self._simulate_price_path_improved(
                     current_price, volatility, horizon, mean_reversion
               )
               outcome = self._evaluate_outcome_improved(
                     price_path, direction, current_price, stop_loss_pct
               )
               outcomes.append(outcome)
        
        # ===== Analyze results =====
        results = self._analyze_outcomes_improved(outcomes, current_price)
        
        # Store results
        self.last_results = results
        self.simulation_history.append({
               'timestamp': datetime.now().isoformat(),
               'price': current_price,
               'volatility': volatility,
               'mean_reversion': mean_reversion,
               'stop_loss_pct': stop_loss_pct,
               'direction': direction,
               'results': results
        })
        
        return results
    def _calculate_trend_factor(self, price_history: List[float]) -> float:
        """
        Calculate trend factor from price history.
        Returns: -1 (strong downtrend) to +1 (strong uptrend)
        """
        if price_history is None or len(price_history) < 20:
            return 0.0
        
        # Calculate slope of recent prices
        recent = price_history[-20:]
        x = np.arange(len(recent))
        slope = np.polyfit(x, recent, 1)[0]
        slope_pct = slope / recent[0] if recent[0] > 0 else 0
        
        # Normalize to -1 to 1
        return max(-1.0, min(1.0, slope_pct * 50))  # 50x amplification
    def _simulate_price_path_improved(self, current_price: float, volatility: float,
                                  horizon: int, mean_reversion: float) -> List[float]:
        """Improved price path simulation with better mean reversion."""
        price_path = [current_price]
        target_price = current_price * (1 + random.uniform(-0.02, 0.02))  # Random target
        
        for i in range(horizon):
               # Random shock
               shock = np.random.normal(0, volatility)
               
               # Mean reversion with drift toward target
               if mean_reversion != 0:
                     # Exponential decay toward target
                     drift_factor = 1 - np.exp(-mean_reversion * (i + 1) / horizon)
                     drift = drift_factor * (target_price - price_path[-1]) / current_price
               else:
                     drift = 0
               
               # Add small momentum component (trend persistence)
               momentum = 0.0
               if len(price_path) > 2:
                     recent_return = (price_path[-1] - price_path[-2]) / price_path[-2]
                     momentum = 0.1 * recent_return  # 10% momentum
               
               # New price with drift + momentum + shock
               new_price = price_path[-1] * (1 + drift + momentum + shock)
               price_path.append(max(0.0001, new_price))
        
        return price_path
    
    def _run_simulations(self, current_price: float, volatility: float,
                        direction: str, num_sims: int, horizon: int,
                        mean_reversion: float) -> List[Dict]:
        """
        Run multiple price path simulations
        """
        outcomes = []
        
        for _ in range(num_sims):
            # Simulate price path
            price_path = self._simulate_price_path(
                current_price, volatility, horizon, mean_reversion
            )
            
            # Evaluate outcome
            outcome = self._evaluate_outcome(price_path, direction, current_price)
            outcomes.append(outcome)
        
        return outcomes
    
    def _simulate_price_path(self, current_price: float, volatility: float,
                            horizon: int, mean_reversion: float) -> List[float]:
        """
        Simulate one price path using geometric Brownian motion + mean reversion
        """
        price_path = [current_price]
        
        for _ in range(horizon):
            # Random shock (Brownian motion)
            shock = np.random.normal(0, volatility)
            
            # Mean reversion component (optional)
            if mean_reversion != 0:
                drift = (mean_reversion * (current_price - price_path[-1])) / horizon
            else:
                drift = 0
            
            # New price
            new_price = price_path[-1] * (1 + drift + shock)
            price_path.append(max(0.0001, new_price))  # Prevent negative prices
        
        return price_path
    
    def _evaluate_outcome(self, price_path: List[float], direction: str,
                         entry_price: float) -> Dict:
        """
        Evaluate the outcome of a simulated price path
        """
        entry = price_path[0]
        max_price = max(price_path)
        min_price = min(price_path)
        final_price = price_path[-1]
        
        if direction == 'BUY':
            # Long position
            pnl = final_price - entry
            max_gain = max_price - entry
            max_loss = entry - min_price
            max_drawdown = min(0, min_price - entry)
        else:  # SELL
            # Short position
            pnl = entry - final_price
            max_gain = entry - min_price
            max_loss = max_price - entry
            max_drawdown = min(0, entry - max_price)
        
        # Check if stop loss was hit (2% stop loss by default)
        stop_loss = abs(entry * 0.02)
        stop_hit = abs(max_loss) > stop_loss
        
        return {
            'pnl': pnl,
            'pnl_pct': (pnl / entry) * 100 if entry > 0 else 0,
            'max_gain': max_gain,
            'max_loss': max_loss,
            'max_drawdown': max_drawdown,
            'stop_hit': stop_hit,
            'success': pnl > 0 and not stop_hit,
            'final_price': final_price,
            'max_price': max_price,
            'min_price': min_price
        }
    
    def _analyze_outcomes(self, outcomes: List[Dict], entry_price: float,
                         direction: str) -> Dict:
        """
        Analyze simulation outcomes to extract key metrics
        """
        if not outcomes:
            return {
                'win_rate': 0.0,
                'expected_return': 0.0,
                'max_drawdown': 0.0,
                'risk_reward_ratio': 0.0,
                'optimal_stop_loss': 0.0,
                'optimal_take_profit': 0.0,
                'entry_confidence': 0.0,
                'sharpe_ratio': 0.0,
                'var_95': 0.0,
                'expected_shortfall': 0.0
            }
        
        # Extract metrics
        pnls = [o['pnl'] for o in outcomes]
        pnl_pcts = [o['pnl_pct'] for o in outcomes]
        successes = [o['success'] for o in outcomes]
        max_drawdowns = [o['max_drawdown'] for o in outcomes]
        stop_hits = [o['stop_hit'] for o in outcomes]
        
        # Calculate win rate
        win_rate = sum(successes) / len(outcomes)
        
        # Calculate expected return
        expected_return = np.mean(pnls)
        
        # Calculate max drawdown
        max_drawdown = min(max_drawdowns)
        
        # Calculate risk-reward ratio
        wins = [o['pnl'] for o in outcomes if o['pnl'] > 0]
        losses = [abs(o['pnl']) for o in outcomes if o['pnl'] < 0]
        avg_win = np.mean(wins) if wins else 0
        avg_loss = np.mean(losses) if losses else 0.01
        risk_reward_ratio = avg_win / avg_loss if avg_loss > 0 else 0
        
        # Calculate optimal stop loss (where loss probability spikes)
        loss_distribution = [o['max_loss'] for o in outcomes if o['max_loss'] < 0]
        if loss_distribution:
            optimal_stop_loss = abs(np.percentile(loss_distribution, 95))
        else:
            optimal_stop_loss = abs(entry_price * 0.02)
        
        # Calculate optimal take profit
        gain_distribution = [o['max_gain'] for o in outcomes if o['max_gain'] > 0]
        if gain_distribution:
            optimal_take_profit = np.percentile(gain_distribution, 75)
        else:
            optimal_take_profit = abs(entry_price * 0.03)
        
        # Calculate Sharpe ratio (assuming risk-free rate = 0)
        sharpe_ratio = np.mean(pnl_pcts) / (np.std(pnl_pcts) + 0.0001)
        
        # Calculate VaR (Value at Risk)
        var_95 = np.percentile(pnls, 5)
        
        # Calculate Expected Shortfall (CVaR)
        expected_shortfall = np.mean([p for p in pnls if p <= var_95]) if any(p <= var_95 for p in pnls) else 0
        
        # Calculate entry confidence (weighted combination)
        entry_confidence = min(95, (
            win_rate * 0.4 +
            min(1, abs(risk_reward_ratio) / 2) * 0.3 +
            (1 - min(1, abs(max_drawdown) / abs(entry_price * 0.1))) * 0.3
        ) * 100)
        # Calculate entry confidence (MORE DECISIVE)
        entry_confidence = 50 + (win_rate - 0.5) * 80  # 50% win rate → 50%, 60% win rate → 58%
        entry_confidence = min(95, max(5, entry_confidence))
        return {
            'win_rate': round(win_rate * 100, 1),
            'expected_return': round(expected_return, 4),
            'max_drawdown': round(max_drawdown, 4),
            'risk_reward_ratio': round(risk_reward_ratio, 2),
            'optimal_stop_loss': round(optimal_stop_loss, 4),
            'optimal_take_profit': round(optimal_take_profit, 4),
            'entry_confidence': round(entry_confidence, 1),
            'sharpe_ratio': round(sharpe_ratio, 2),
            'var_95': round(var_95, 4),
            'expected_shortfall': round(expected_shortfall, 4),
            'num_simulations': len(outcomes),
            'stop_hit_rate': round(sum(stop_hits) / len(outcomes) * 100, 1),
            'avg_pnl': round(np.mean(pnls), 4),
            'std_pnl': round(np.std(pnls), 4)
        }
    
    def _calculate_volatility(self, price_history: List[float] = None) -> float:
        """
        Calculate volatility from actual price history.
        Uses ATR (Average True Range) for better estimation.
        """
        # ===== FIX: Handle None price_history =====
        if price_history is None or len(price_history) < 14:
                 return 0.005  # Default 0.5%
        
        # Calculate returns
        returns = []
        for i in range(1, len(price_history)):
                 ret = (price_history[i] - price_history[i-1]) / price_history[i-1]
                 returns.append(ret)
        
        if returns:
                 # Annualized volatility
                 daily_vol = np.std(returns)
                 # Scale to period (15 minutes = 96 periods per day)
                 period_vol = daily_vol / np.sqrt(96)
                 return max(0.001, period_vol)
        
        return 0.005  # 0.5%
     
    def _calculate_mean_reversion(self, price_history: List[float] = None) -> float:
        """
        Calculate mean reversion speed based on market regime.
        """
        # ===== FIX: Handle None price_history =====
        if price_history is None:
               return 0.0  # Default: random walk
        
        if len(price_history) < 50:
               return 0.0
        
        # Calculate Hurst exponent (0.5 = random walk, <0.5 = mean reverting)
        # Simplified: use autocorrelation
        returns = []
        for i in range(1, len(price_history)):
               ret = (price_history[i] - price_history[i-1]) / price_history[i-1]
               returns.append(ret)
        
        if len(returns) > 20:
               # Lag-1 autocorrelation
               try:
                     lag1 = np.corrcoef(returns[:-1], returns[1:])[0, 1]
                     # If negative autocorrelation, market is mean reverting
                     if lag1 < -0.1:
                          return 0.05  # Strong mean reversion
                     elif lag1 < 0:
                          return 0.02  # Weak mean reversion
               except:
                     return 0.0
        
        return 0.0  # Random walk
    def _calculate_dynamic_stop(self, entry_price: float, atr: float) -> float:
        """
        Calculate stop loss based on ATR.
        """
        if atr > 0:
              # 2x ATR for normal markets, 1.5x for volatile
              atr_multiplier = 2.0
              stop_distance = atr * atr_multiplier
              return max(entry_price * 0.005, stop_distance)  # Minimum 0.5%
        
        return entry_price * 0.02  # Default 2%
    def calculate_position_size(self, account_balance: float, 
                               risk_per_trade: float = 0.02,
                               entry_price: float = None,
                               stop_loss: float = None) -> Dict:
        """
        Calculate optimal position size using Kelly Criterion and risk management
        """
        # Use last results if available
        if not self.last_results:
            return {
                'position_size': 0.1,
                'risk_amount': account_balance * risk_per_trade,
                'units': 0,
                'kelly_fraction': 0.25
            }
        
        win_rate = self.last_results.get('win_rate', 50) / 100
        risk_reward = self.last_results.get('risk_reward_ratio', 1)
        
        # Kelly Criterion: f* = (p * b - q) / b
        # where p = win rate, q = loss rate, b = risk-reward ratio
        q = 1 - win_rate
        if risk_reward > 0:
            kelly_fraction = (win_rate * risk_reward - q) / risk_reward
        else:
            kelly_fraction = 0.25
        
        # Cap Kelly fraction (never risk more than 25% of account)
        kelly_fraction = max(0, min(0.25, kelly_fraction))
        
        # Calculate risk amount
        risk_amount = account_balance * risk_per_trade * kelly_fraction * 2
        
        # Calculate position size based on stop loss
        if stop_loss and entry_price:
            risk_per_unit = abs(entry_price - stop_loss)
            if risk_per_unit > 0:
                units = risk_amount / risk_per_unit
            else:
                units = risk_amount / (entry_price * 0.01)
        else:
            units = risk_amount / (entry_price * 0.01) if entry_price else 0
        
        return {
            'position_size': round(kelly_fraction * 100, 1),
            'risk_amount': round(risk_amount, 2),
            'units': round(units, 0),
            'kelly_fraction': round(kelly_fraction, 3),
            'win_rate': self.last_results.get('win_rate', 50),
            'risk_reward_ratio': self.last_results.get('risk_reward_ratio', 1)
        }
    
    def get_simulation_summary(self) -> Dict:
        """
        Get summary of recent simulations
        """
        if not self.simulation_history:
            return {'status': 'No simulations run'}
        
        last = self.simulation_history[-1]
        return {
            'last_simulation': last,
            'total_simulations': len(self.simulation_history),
            'last_results': self.last_results
        }
    
    def reset(self):
        """Reset simulation history"""
        self.simulation_history.clear()
        self.last_results = {}
        logger.info("🔄 MonteCarloSimulator reset")


# For backward compatibility
class MonteCarlosSimulator(MonteCarloSimulator):
    """Alias for backward compatibility"""
    pass