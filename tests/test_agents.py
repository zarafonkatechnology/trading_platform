import unittest
import sys
sys.path.insert(0, '/home/mohammed/trading_platform')

from backend.agents.agent_a_trend import AgentATrend
from backend.agents.agent_b_mean_reversion import AgentBMeanReversion
from backend.agents.base_agent import BaseAgent

class TestAgents(unittest.TestCase):
    
    def setUp(self):
        self.agent_a = AgentATrend()
        self.agent_b = AgentBMeanReversion()
        self.base_agent = BaseAgent("Test", "Test", "Test")
    
    def test_agent_initialization(self):
        self.assertEqual(self.agent_a.name, "Agent_A")
        self.assertEqual(self.agent_a.agent_type, "Trend Follower")
        self.assertEqual(self.agent_a.xp_points, 0)
        self.assertEqual(self.agent_a.token_balance, 1000)
    
    def test_agent_prediction_returns_valid_action(self):
        signal = {'confidence_percent': 85}
        features = {}
        
        action, confidence = self.agent_a.predict(signal, features)
        self.assertIn(action, ['BUY', 'SELL', 'HOLD'])
        self.assertGreaterEqual(confidence, 0)
        self.assertLessEqual(confidence, 100)
    
    def test_agent_reward_update(self):
        result = self.agent_a.update_from_reward(True, 25, 0)
        self.assertEqual(result['xp_points'], 25)
        self.assertEqual(result['token_balance'], 1012)  # 1000 + 25//2
        
        result2 = self.agent_a.update_from_reward(False, 0, 15)
        self.assertEqual(result2['xp_points'], 10)  # 25 - 15
    
    def test_agent_vote_returns_dict(self):
        signal = {'confidence_percent': 80}
        features = {}
        
        vote = self.agent_a.vote(signal, features)
        self.assertIn('vote', vote)
        self.assertIn('confidence', vote)
        self.assertIn('agent_name', vote)
    
    def test_base_agent_status(self):
        status = self.base_agent.get_status()
        self.assertEqual(status['name'], 'Test')
        self.assertEqual(status['type'], 'Test')
        self.assertIn('xp_points', status)
        self.assertIn('token_balance', status)

if __name__ == '__main__':
    unittest.main()
