"""
World Model + Monte Carlo Simulations for Trading
Learns market dynamics and simulates possible futures
"""

import numpy as np
import random
from collections import defaultdict
from typing import Dict, List, Tuple, Any
from datetime import datetime

class MarketState:
    """Represents the current market state for world model"""
    
    def __init__(self, price: float, volume: float, rsi: float, trend: str):
        self.price = price
        self.volume = volume
        self.rsi = rsi
        self.trend = trend
        self.timestamp = datetime.now()
    
    def to_tuple(self) -> tuple:
        """Convert to hashable tuple for transition counting"""
        # Discretize continuous values
        price_bucket = int(self.price * 1000) / 1000
        volume_bucket = 'high' if self.volume > 10000 else 'low'
        rsi_bucket = 'overbought' if self.rsi > 70 else ('oversold' if self.rsi < 30 else 'neutral')
        
        return (price_bucket, volume_bucket, rsi_bucket, self.trend)
    
    @classmethod
    def from_signal(cls, signal_data: Dict):
        """Create state from signal data"""
        indicators = signal_data.get('indicators', {})
        return cls(
            price=signal_data.get('price', 0),
            volume=indicators.get('volume', 5000),
            rsi=indicators.get('rsi', 50),
            trend=indicators.get('trend', 'neutral')
        )


class WorldModel:
    """
    Learns market dynamics from historical data
    Builds transition probability matrix between states
    """
    
    def __init__(self, lookback: int = 100):
        self.lookback = lookback
        self.transitions = defaultdict(lambda: defaultdict(int))
        self.state_counts = defaultdict(int)
        self.history = []
        
    def learn_from_history(self, price_data: List[Dict]) -> None:
        """
        Learn transition probabilities from historical price data
        
        Args:
            price_data: List of dictionaries with 'price', 'volume', 'rsi', etc.
        """
        print(f"📚 World Model learning from {len(price_data)} historical points...")
        
        for i in range(len(price_data) - 1):
            current = self._create_state(price_data[i])
            next_state = self._create_state(price_data[i + 1])
            
            current_tuple = current.to_tuple()
            next_tuple = next_state.to_tuple()
            
            self.transitions[current_tuple][next_tuple] += 1
            self.state_counts[current_tuple] += 1
        
        print(f"✅ World Model learned {len(self.transitions)} state transitions")
    
    def _create_state(self, data_point: Dict) -> MarketState:
        """Create MarketState from data point"""
        return MarketState(
            price=data_point.get('close', data_point.get('price', 0)),
            volume=data_point.get('volume', 5000),
            rsi=data_point.get('rsi', 50),
            trend=data_point.get('trend', 'neutral')
        )
    
    def predict_next_state(self, current_state: MarketState) -> MarketState:
        """
        Predict next state based on learned probabilities
        """
        current_tuple = current_state.to_tuple()
        
        if current_tuple not in self.transitions:
            # No data, return small random move
            return self._default_next_state(current_state)
        
        # Get possible next states with their probabilities
        next_states = list(self.transitions[current_tuple].keys())
        probabilities = [self.transitions[current_tuple][s] / self.state_counts[current_tuple] 
                        for s in next_states]
        
        # Choose randomly based on probability
        chosen = np.random.choice(len(next_states), p=probabilities)
        next_tuple = next_states[chosen]
        
        # Convert tuple back to MarketState
        return self._tuple_to_state(next_tuple, current_state)
    
    def _default_next_state(self, current_state: MarketState) -> MarketState:
        """Default transition when no data available"""
        # Random walk with drift
        price_change = random.gauss(0, 0.005)  # 0.5% standard deviation
        new_price = current_state.price * (1 + price_change)
        
        return MarketState(
            price=new_price,
            volume=current_state.volume * (1 + random.gauss(0, 0.1)),
            rsi=min(100, max(0, current_state.rsi + random.gauss(0, 5))),
            trend=random.choice(['up', 'down', 'neutral'])
        )
    
    def _tuple_to_state(self, state_tuple: tuple, reference: MarketState) -> MarketState:
        """Convert tuple back to MarketState"""
        price, volume_bucket, rsi_bucket, trend = state_tuple
        
        # Convert back from buckets
        volume = 15000 if volume_bucket == 'high' else 5000
        rsi = 85 if rsi_bucket == 'overbought' else (15 if rsi_bucket == 'oversold' else 50)
        
        return MarketState(price=price, volume=volume, rsi=rsi, trend=trend)
    
    def get_transition_probability(self, from_state: MarketState, to_state: MarketState) -> float:
        """Get probability of transitioning from one state to another"""
        from_tuple = from_state.to_tuple()
        to_tuple = to_state.to_tuple()
        
        if from_tuple not in self.transitions:
            return 0.0
        
        total = self.state_counts[from_tuple]
        if total == 0:
            return 0.0
        
        return self.transitions[from_tuple].get(to_tuple, 0) / total


class MonteCarloSimulator:
    """
    Runs Monte Carlo simulations to evaluate possible futures
    """
    
    def __init__(self, world_model: WorldModel, n_simulations: int = 2000, horizon: int = 20):
        """
        Args:
            world_model: Trained WorldModel instance
            n_simulations: Number of simulations to run (default 2000)
            horizon: Number of steps to simulate (default 20)
        """
        self.world_model = world_model
        self.n_simulations = n_simulations
        self.horizon = horizon
    
    def simulate_futures(self, current_state: MarketState) -> List[List[MarketState]]:
        """
        Generate multiple possible futures
        
        Returns:
            List of simulation paths, each path is a list of MarketState objects
        """
        all_paths = []
        
        for _ in range(self.n_simulations):
            path = [current_state]
            current = current_state
            
            for _ in range(self.horizon):
                next_state = self.world_model.predict_next_state(current)
                path.append(next_state)
                current = next_state
            
            all_paths.append(path)
        
        return all_paths
    
    def evaluate_action(self, action: str, current_price: float, 
                        futures: List[List[MarketState]]) -> Dict:
        """
        Evaluate how an action performs across all simulated futures
        
        Args:
            action: 'BUY', 'SELL', or 'HOLD'
            current_price: Current price to execute at
            futures: List of simulated future paths
            
        Returns:
            Dictionary with outcome statistics
        """
        outcomes = []
        
        for path in futures:
            if action == 'BUY':
                # Buy now, sell at end of simulation
                entry = current_price
                exit_price = path[-1].price
                pnl = (exit_price - entry) / entry
            elif action == 'SELL':
                entry = current_price
                exit_price = path[-1].price
                pnl = (entry - exit_price) / entry
            else:  # HOLD
                pnl = 0
            
            outcomes.append(pnl)
        
        outcomes = np.array(outcomes)
        
        return {
            'action': action,
            'mean_return': np.mean(outcomes),
            'std_return': np.std(outcomes),
            'win_rate': np.mean(outcomes > 0) * 100,
            'max_loss': np.min(outcomes),
            'max_gain': np.max(outcomes),
            'sharpe': np.mean(outcomes) / (np.std(outcomes) + 0.0001),
            'percentile_25': np.percentile(outcomes, 25),
            'percentile_75': np.percentile(outcomes, 75)
        }
    
    def best_action(self, current_state: MarketState, current_price: float) -> Dict:
        """
        Find the best action using Monte Carlo simulation
        
        Returns:
            Dictionary with best action and statistics
        """
        print(f"🎲 Running {self.n_simulations} Monte Carlo simulations over {self.horizon} steps...")
        
        # Generate futures once
        futures = self.simulate_futures(current_state)
        
        # Evaluate each action
        results = []
        for action in ['BUY', 'SELL', 'HOLD']:
            result = self.evaluate_action(action, current_price, futures)
            results.append(result)
        
        # Find best action by Sharpe ratio (risk-adjusted return)
        best = max(results, key=lambda x: x['sharpe'])
        
        return {
            'best_action': best['action'],
            'confidence': min(95, 50 + best['sharpe'] * 20),
            'expected_return': best['mean_return'] * 100,
            'win_rate': best['win_rate'],
            'risk_metrics': {
                'sharpe': round(best['sharpe'], 2),
                'max_loss': round(best['max_loss'] * 100, 2),
                'max_gain': round(best['max_gain'] * 100, 2),
                'range_25_75': f"{round(best['percentile_25'] * 100, 1)}% to {round(best['percentile_75'] * 100, 1)}%"
            },
            'all_actions': results
        }


class AdaptiveThresholdPolicy:
    """
    Dynamically adjusts trading thresholds based on market conditions
    """
    
    def __init__(self, base_threshold: float = 0.6):
        """
        Args:
            base_threshold: Base confidence threshold (0-1)
        """
        self.base_threshold = base_threshold
        self.history = []
    
    def adjust_threshold(self, market_volatility: float, recent_win_rate: float = None) -> float:
        """
        Adjust threshold based on market conditions
        
        Args:
            market_volatility: Current market volatility (ATR ratio)
            recent_win_rate: Recent win rate (0-1)
        
        Returns:
            Adjusted threshold
        """
        threshold = self.base_threshold
        
        # Increase threshold in high volatility (be more selective)
        if market_volatility > 1.5:
            threshold += 0.1
        elif market_volatility > 1.2:
            threshold += 0.05
        elif market_volatility < 0.8:
            threshold -= 0.05
        
        # Adjust based on recent performance
        if recent_win_rate is not None:
            if recent_win_rate < 0.4:
                threshold += 0.1  # Losing streak, be more selective
            elif recent_win_rate > 0.7:
                threshold -= 0.05  # Winning streak, can be more aggressive
        
        return min(0.95, max(0.4, threshold))
    
    def should_trade(self, confidence: float, market_volatility: float) -> Tuple[bool, str]:
        """
        Determine if trade should be executed
        
        Returns:
            (should_trade, reason)
        """
        adjusted = self.adjust_threshold(market_volatility)
        confidence_pct = confidence / 100
        
        if confidence_pct >= adjusted:
            return True, f"Confidence {confidence}% >= threshold {adjusted*100:.0f}%"
        else:
            return False, f"Confidence {confidence}% < threshold {adjusted*100:.0f}%"


class MonteCarloTrader:
    """
    Complete Monte Carlo trading agent
    Combines world model, simulations, and adaptive policy
    """
    
    def __init__(self, world_model: WorldModel, n_simulations: int = 2000):
        self.world_model = world_model
        self.simulator = MonteCarloSimulator(world_model, n_simulations=n_simulations)
        self.policy = AdaptiveThresholdPolicy()
        
    def decide(self, signal_data: Dict) -> Dict:
        """
        Make trading decision using Monte Carlo simulations
        """
        # Create current state from signal
        current_state = MarketState.from_signal(signal_data)
        current_price = signal_data.get('price', 0)
        
        # Get market volatility
        volatility = signal_data.get('indicators', {}).get('volatility', 1.0)
        
        # Run Monte Carlo simulation
        result = self.simulator.best_action(current_state, current_price)
        
        # Apply adaptive threshold
        should_trade, reason = self.policy.should_trade(
            result['confidence'], 
            volatility
        )
        
        final_action = result['best_action'] if should_trade else 'HOLD'
        final_confidence = result['confidence'] if should_trade else result['confidence'] * 0.5
        
        return {
            'vote': final_action,
            'confidence': round(final_confidence, 1),
            'reasoning': f"🎲 Monte Carlo: {result['win_rate']:.0f}% win rate, {result['expected_return']:.1f}% expected return. {reason}",
            'monte_carlo_stats': {
                'expected_return': result['expected_return'],
                'win_rate': result['win_rate'],
                'sharpe': result['risk_metrics']['sharpe'],
                'risk_range': result['risk_metrics']['range_25_75']
            }
        }
