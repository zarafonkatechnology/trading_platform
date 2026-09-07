# deepseek_coach.py
"""
DeepSeek Coach - Reinforcement Learning for Agents
"""

import json
import requests
import os
from datetime import datetime
from typing import Dict, List

DEEPSEEK_API_KEY = os.getenv('DEEPSEEK_API_KEY', 'sk-155bc1f42252453585b37d2655dca432')
DEEPSEEK_URL = "https://api.deepseek.com/v1/chat/completions"

class DeepSeekCoach:
    """DeepSeek as Reinforcement Learning Coach"""
    
    def __init__(self):
        self.xp_system = {
            'correct_buy': {'xp': 10, 'tokens': 50},
            'correct_sell': {'xp': 10, 'tokens': 50},
            'correct_hold': {'xp': 5, 'tokens': 25},
            'incorrect_buy': {'xp': -25, 'tokens': -15},
            'incorrect_sell': {'xp': -25, 'tokens': -15},
            'incorrect_hold': {'xp': -15, 'tokens': -10},
        }
    
    def evaluate_agent_votes(self, symbol: str, agent_votes: Dict, actual_result: str) -> Dict:
        """
        Evaluate agent votes against actual result
        """
        results = {}
        
        for agent_name, vote_data in agent_votes.items():
            vote = vote_data.get('vote', 'HOLD')
            confidence = vote_data.get('confidence', 50)
            
            # Determine if correct
            correct = False
            if actual_result == 'UP':
                correct = vote == 'BUY'
            elif actual_result == 'DOWN':
                correct = vote == 'SELL'
            else:  # SIDEWAYS
                correct = vote == 'HOLD'
            
            # Calculate rewards
            key = f"{'correct' if correct else 'incorrect'}_{vote.lower()}"
            rewards = self.xp_system.get(key, {'xp': 0, 'tokens': 0})
            
            results[agent_name] = {
                'vote': vote,
                'confidence': confidence,
                'correct': correct,
                'xp': rewards['xp'],
                'tokens': rewards['tokens'],
                'reasoning': vote_data.get('reasoning', '')
            }
        
        return results
    
    def get_deepseek_feedback(self, symbol: str, agent_results: Dict, actual_result: str) -> str:
        """
        Get detailed feedback from DeepSeek
        """
        # Build prompt
        agents_summary = ""
        for agent, result in agent_results.items():
            status = "✅ CORRECT" if result['correct'] else "❌ WRONG"
            agents_summary += f"- {agent}: {result['vote']} ({result['confidence']}%) - {status}\n"
        
        prompt = f"""
You are a trading coach analyzing agent performance.

SYMBOL: {symbol}
ACTUAL RESULT: {actual_result}

AGENT VOTES:
{agents_summary}

Please provide:
1. A brief analysis of why each agent was right or wrong
2. Specific rules or patterns they should follow
3. How they can improve their decision-making
4. A short "lesson" from this trade

Format your response as JSON:
{{
    "analysis": "Overall analysis",
    "agent_feedback": {{
        "Agent_R": "Specific feedback for Agent_R",
        "Agent_Q": "Specific feedback for Agent_Q",
        ...
    }},
    "rules": ["Rule 1", "Rule 2", ...],
    "lesson": "Short lesson summary"
}}
"""
        
        try:
            headers = {
                "Authorization": f"Bearer {DEEPSEEK_API_KEY}",
                "Content-Type": "application/json"
            }
            
            data = {
                "model": "deepseek-chat",
                "messages": [
                    {"role": "system", "content": "You are a trading coach helping AI agents improve."},
                    {"role": "user", "content": prompt}
                ],
                "temperature": 0.5,
                "max_tokens": 800
            }
            
            response = requests.post(DEEPSEEK_URL, headers=headers, json=data, timeout=30)
            
            if response.status_code == 200:
                content = response.json()['choices'][0]['message']['content']
                # Try to parse JSON
                import re
                json_match = re.search(r'\{.*\}', content, re.DOTALL)
                if json_match:
                    return json.loads(json_match.group())
                return {'analysis': content, 'agent_feedback': {}, 'rules': [], 'lesson': content}
            else:
                return {'analysis': 'DeepSeek feedback unavailable', 'agent_feedback': {}, 'rules': [], 'lesson': ''}
                
        except Exception as e:
            print(f"DeepSeek feedback error: {e}")
            return {'analysis': 'Error getting feedback', 'agent_feedback': {}, 'rules': [], 'lesson': ''}
    
    def update_strategies(self, symbol: str, feedback: Dict) -> Dict:
        """
        Update agent strategies based on DeepSeek feedback
        """
        rules = feedback.get('rules', [])
        lesson = feedback.get('lesson', '')
        
        strategies = {
            'symbol': symbol,
            'rules': rules,
            'lesson': lesson,
            'timestamp': datetime.now().isoformat()
        }
        
        # Save to database
        # ... DB logic here ...
        
        return strategies