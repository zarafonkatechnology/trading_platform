# agent_pipeline.py
import json
from datetime import datetime
from decimal import Decimal
from backend.agents.agent_manager import AgentManager
from backend.services.deepseek_advisor import get_deepseek_advisor
from price_cache_manager import price_cache

class AgentDeliberativePipeline:
    """Sequential agent reasoning pipeline"""
    
    def __init__(self):
        self.agent_manager = AgentManager()
        self.advisor = get_deepseek_advisor()
        
        # Define agent roles in sequence
        self.pipeline = [
            {'role': 'Analyst', 'agents': ['Agent_A', 'Agent_C', 'Agent_K']},
            {'role': 'Challenger', 'agents': ['Agent_B', 'Agent_D', 'Agent_R']},
            {'role': 'Validator', 'agents': ['Agent_G', 'Agent_J', 'Agent_P']},
            {'role': 'Executor', 'agents': ['Agent_E', 'Agent_F']}
        ]
        
        print("✅ Agent Deliberative Pipeline initialized")
    
    def _to_float(self, value):
        """Convert Decimal to float safely"""
        if value is None:
            return 0.0
        if isinstance(value, Decimal):
            return float(value)
        return float(value) if value else 0.0
    
    def get_market_context(self, symbol: str) -> dict:
        """Get market context for analysis"""
        try:
            price_data = price_cache.get_price(symbol)
            
            if not price_data:
                return {
                    'symbol': symbol,
                    'current_price': 0,
                    'recent_prices': [],
                    'volume': 0,
                    'timestamp': datetime.now().isoformat()
                }
            
            current_price = self._to_float(price_data.get('mid', 0))
            
            return {
                'symbol': symbol,
                'current_price': current_price,
                'price_data': price_data,
                'timestamp': datetime.now().isoformat()
            }
        except Exception as e:
            print(f"Error getting market context for {symbol}: {e}")
            return {
                'symbol': symbol,
                'current_price': 0,
                'price_data': {},
                'timestamp': datetime.now().isoformat()
            }
    
    def analyze_symbol(self, symbol: str, current_price: float = None) -> dict:
        """Run complete analysis pipeline for a symbol"""
        
        # Get current price if not provided
        if current_price is None:
            price_data = price_cache.get_price(symbol)
            if price_data:
                current_price = self._to_float(price_data.get('mid', 0))
            else:
                return {'decision': 'HOLD', 'confidence': 0, 'reason': 'No price data'}
        
        # Get market context
        market_data = self.get_market_context(symbol)
        
        # Create signal_data in the format agents expect
        signal_data = {
            'pair': symbol,
            'price': current_price,
            'current_price': current_price,
            'symbol': symbol,
            'timestamp': datetime.now().isoformat()
        }
        
        # Stage 1: Analyst – Identify signal
        analyst_votes = self.run_stage('Analyst', signal_data, market_data)
        analyst_consensus = self.aggregate_votes(analyst_votes)
        # Change this block (around line 60-70):
        if abs(analyst_consensus['score']) < 30:
            return {
                   'decision': 'HOLD', 
                   'confidence': 0, 
                   'reason': 'No clear analyst signal',
                   'analyst_score': analyst_consensus['score'],  # Add this
                   'score': analyst_consensus['score'],          # Add this
                   'analyst_votes': self._simplify_votes(analyst_votes)  # Add this
    }
        
        # Stage 2: Challenger – Challenge the signal
        challenger_votes = self.run_stage('Challenger', signal_data, market_data)
        challenger_consensus = self.aggregate_votes(challenger_votes)
        
        # Stage 3: Validator – Confirm with additional data
        validator_votes = self.run_stage('Validator', signal_data, market_data)
        validator_consensus = self.aggregate_votes(validator_votes)
        
        final_score = (analyst_consensus['score'] * 0.4 + 
                       challenger_consensus['score'] * 0.3 + 
                       validator_consensus['score'] * 0.3)
        
        # Determine decision
        if final_score > 30:
            decision = 'BUY'
        elif final_score < -30:
            decision = 'SELL'
        else:
            decision = 'HOLD'
        
        return {
            'decision': decision,
            'confidence': min(95, abs(final_score)),
            'score': final_score,
            'analyst_score': analyst_consensus['score'],
            'challenger_score': challenger_consensus['score'],
            'validator_score': validator_consensus['score'],
            'analyst_votes': self._simplify_votes(analyst_votes),
            'challenger_votes': self._simplify_votes(challenger_votes),
            'validator_votes': self._simplify_votes(validator_votes),
            'timestamp': datetime.now().isoformat()
        }
    
    def run_stage(self, stage_name: str, signal_data: dict, market_data: dict):
        """Run agents in a stage"""
        stage_config = next((s for s in self.pipeline if s['role'] == stage_name), None)
        if not stage_config:
            return {}
        
        votes = {}
        for agent_name in stage_config['agents']:
            agent = self.agent_manager.get_agent(agent_name)
            if agent:
                try:
                    # Try different method signatures based on what the agent supports
                    vote = self._call_agent(agent, signal_data, market_data)
                    
                    # Ensure vote has required fields
                    if isinstance(vote, dict):
                        if 'vote' not in vote:
                            vote['vote'] = 'HOLD'
                        if 'confidence' not in vote:
                            vote['confidence'] = 50
                    else:
                        vote = {'vote': 'HOLD', 'confidence': 50, 'reason': 'Invalid vote format'}
                    
                    votes[agent_name] = vote
                    
                except Exception as e:
                    print(f"Error running {agent_name}: {e}")
                    votes[agent_name] = {'vote': 'HOLD', 'confidence': 50, 'error': str(e)}
        
        return votes
    
    def _call_agent(self, agent, signal_data: dict, market_data: dict) -> dict:
        """Call agent with appropriate method signature"""
        
        # Method 1: analyze_signal(signal_data) - single argument
        if hasattr(agent, 'analyze_signal'):
            try:
                result = agent.analyze_signal(signal_data)
                if isinstance(result, dict):
                    return result
            except TypeError:
                pass
        
        # Method 2: analyze_signal(signal_data, market_data) - two arguments
        if hasattr(agent, 'analyze_signal'):
            try:
                result = agent.analyze_signal(signal_data, market_data)
                if isinstance(result, dict):
                    return result
            except TypeError:
                pass
        
        # Method 3: analyze(signal_data) - single argument
        if hasattr(agent, 'analyze'):
            try:
                result = agent.analyze(signal_data)
                if isinstance(result, dict):
                    return result
            except TypeError:
                pass
        
        # Method 4: get_vote(symbol, price, context)
        if hasattr(agent, 'get_vote'):
            try:
                result = agent.get_vote(
                    signal_data.get('symbol', 'UNKNOWN'),
                    signal_data.get('price', 0),
                    market_data
                )
                if isinstance(result, dict):
                    return result
            except TypeError:
                pass
        
        # Method 5: Simple vote based on agent type (fallback)
        return self._fallback_vote(agent, signal_data)
    
    def _fallback_vote(self, agent, signal_data: dict) -> dict:
        """Fallback voting logic when agent methods fail"""
        agent_name = getattr(agent, 'name', 'Unknown')
        agent_type = getattr(agent, 'agent_type', 'Unknown')
        
        # Simple bias based on agent type
        if 'Trend' in agent_type or 'Momentum' in agent_type:
            bias = 'BUY'
            confidence = 65
        elif 'Mean' in agent_type or 'Reversion' in agent_type:
            bias = 'SELL'
            confidence = 60
        elif 'Supply' in agent_type or 'Demand' in agent_type:
            bias = 'HOLD'
            confidence = 55
        else:
            bias = 'HOLD'
            confidence = 50
        
        return {
            'vote': bias,
            'confidence': confidence,
            'agent': agent_name,
            'type': agent_type,
            'note': 'Fallback vote'
        }
    
    def _simplify_votes(self, votes: dict) -> dict:
        """Simplify votes for output"""
        simplified = {}
        for agent, vote in votes.items():
            simplified[agent] = {
                'vote': vote.get('vote', 'HOLD'),
                'confidence': vote.get('confidence', 50)
            }
        return simplified
    
    def aggregate_votes(self, votes: dict) -> dict:
        """Aggregate votes with weighted confidence"""
        buy_score = 0
        sell_score = 0
        total_weight = 0
        
        for agent_name, vote in votes.items():
            weight = vote.get('trust_weight', 1.0)
            confidence = vote.get('confidence', 50)
            
            if vote.get('vote') == 'BUY':
                buy_score += confidence * weight
            elif vote.get('vote') == 'SELL':
                sell_score += confidence * weight
            total_weight += weight
        
        if total_weight == 0:
            return {'direction': 'HOLD', 'score': 0}
        
        net_score = (buy_score - sell_score) / total_weight
        direction = 'BUY' if net_score > 10 else 'SELL' if net_score < -10 else 'HOLD'
        
        return {'direction': direction, 'score': net_score}
    
    def get_deepseek_review(self, symbol: str, price: float, market_data: dict, score: float) -> str:
        """Get AI review from DeepSeek"""
        try:
            if self.advisor and hasattr(self.advisor, 'analyze'):
                response = self.advisor.analyze(symbol, price, {'score': score})
                return response if response else "No AI review available"
        except Exception as e:
            print(f"DeepSeek review error: {e}")
        
        return "AI review unavailable"


# Test function
if __name__ == "__main__":
    print("Testing Agent Pipeline...")
    print("=" * 50)
    
    pipeline = AgentDeliberativePipeline()
    
    # Test with NASDAQ100
    print("\nAnalyzing #NASDAQ100...")
    result = pipeline.analyze_symbol('#NASDAQ100', 19850.00)
    
    print(f"\nResult:")
    print(f"  Decision: {result['decision']}")
    print(f"  Confidence: {result['confidence']:.1f}%")
    print(f"  Score: {result['score']:.1f}")
    print(f"  Analyst Score: {result['analyst_score']:.1f}")
    print(f"  Challenger Score: {result['challenger_score']:.1f}")
    print(f"  Validator Score: {result['validator_score']:.1f}")
    
    if result.get('analyst_votes'):
        print(f"\n  Analyst Votes:")
        for agent, vote in result['analyst_votes'].items():
            print(f"    {agent}: {vote['vote']} ({vote['confidence']}%)")
    
    # Test with GOLD
    print("\n" + "=" * 50)
    print("Analyzing GOLD...")
    result2 = pipeline.analyze_symbol('GOLD', 2350.00)
    
    print(f"\nResult:")
    print(f"  Decision: {result2['decision']}")
    print(f"  Confidence: {result2['confidence']:.1f}%")
    print(f"  Score: {result2['score']:.1f}")