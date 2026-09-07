"""
Integration of Monte Carlo simulations into existing agents
"""

import numpy as np
from backend.utils.world_model import WorldModel, MonteCarloTrader, MarketState

class MonteCarloAgentWrapper:
    """
    Wraps an existing agent with Monte Carlo capabilities
    """
    
    def __init__(self, base_agent, world_model: WorldModel = None, n_simulations: int = 1000):
        self.base_agent = base_agent
        self.world_model = world_model or WorldModel()
        self.mc_trader = MonteCarloTrader(self.world_model, n_simulations=n_simulations)
        self.name = base_agent.name
        self.agent_type = base_agent.agent_type
    
    def analyze(self, signal_data: Dict) -> Dict:
        """
        Enhanced analyze with Monte Carlo simulation
        """
        # Get base agent's vote
        base_result = self.base_agent.analyze(signal_data)
        
        # Get Monte Carlo recommendation
        mc_result = self.mc_trader.decide(signal_data)
        
        # Combine results (weighted average)
        # Give more weight to Monte Carlo for trend-following agents
        if 'trend' in self.agent_type.lower():
            mc_weight = 0.7
        else:
            mc_weight = 0.5
        
        combined_confidence = (
            base_result['confidence'] * (1 - mc_weight) + 
            mc_result['confidence'] * mc_weight
        )
        
        # If Monte Carlo strongly disagrees, override
        if mc_result['vote'] != base_result['vote'] and mc_result['confidence'] > 75:
            final_vote = mc_result['vote']
            reasoning = f"🔄 Monte Carlo override: {mc_result['reasoning']}"
        else:
            final_vote = base_result['vote']
            reasoning = f"🤝 Combined analysis: {base_result['reasoning']} | {mc_result['reasoning']}"
        
        return {
            'agent': self.name,
            'vote': final_vote,
            'confidence': round(combined_confidence, 1),
            'reasoning': reasoning,
            'base_vote': base_result['vote'],
            'mc_vote': mc_result['vote'],
            'mc_stats': mc_result.get('monte_carlo_stats', {})
        }


class AdaptiveWorldModel:
    """
    World model that continuously learns from new trades
    """
    
    def __init__(self, world_model: WorldModel, update_frequency: int = 10):
        self.world_model = world_model
        self.update_frequency = update_frequency
        self.trade_counter = 0
        self.trade_history = []
    
    def record_trade_outcome(self, trade_data: Dict):
        """
        Record trade outcome for continuous learning
        """
        self.trade_history.append(trade_data)
        self.trade_counter += 1
        
        # Update world model periodically
        if self.trade_counter >= self.update_frequency:
            self._update_model()
            self.trade_counter = 0
    
    def _update_model(self):
        """Update world model with recent trades"""
        print(f"🔄 Updating World Model with {len(self.trade_history)} new trades...")
        
        # Convert trades to price data format
        price_data = []
        for trade in self.trade_history[-50:]:  # Last 50 trades
            price_data.append({
                'price': trade.get('entry_price', 0),
                'volume': trade.get('volume', 5000),
                'rsi': trade.get('rsi', 50),
                'trend': trade.get('trend', 'neutral')
            })
        
        if len(price_data) > 10:
            self.world_model.learn_from_history(price_data)
