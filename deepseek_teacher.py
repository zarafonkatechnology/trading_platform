"""
DeepSeek API Teaching Module - Direct HTTP Version
No OpenAI library dependency
"""

import json
from datetime import datetime
"""
DeepSeek API Teaching Module
"""

class DeepSeekTeacher:
    """Uses DeepSeek API to teach agents"""
    
    def __init__(self, api_client):
        self.client = api_client
        
    def _call_deepseek(self, prompt, system_message="You are an expert trading coach."):
        """Make API call to DeepSeek"""
        messages = [
            {"role": "system", "content": system_message},
            {"role": "user", "content": prompt}
        ]
        
        response = self.client.chat_completion(messages=messages)
        return response['choices'][0]['message']['content']
    
    def teach_agent_strategy(self, agent_name, agent_type, specialization, current_xp, win_rate):
        """Teach a single agent"""
        
        prompt = f"""Teach {agent_name} ({agent_type}) a specific trading strategy.

Specialization: {specialization}
Current XP: {current_xp}
Win Rate: {win_rate}%

Give 2-3 sentences of actionable advice. Be specific."""
        
        try:
            lesson = self._call_deepseek(prompt)
            return {'success': True, 'agent': agent_name, 'lesson': lesson}
        except Exception as e:
            return {'success': False, 'error': str(e)}
    
    def teach_cooperation(self, agent_names, agent_types):
        """Teach cooperation protocol"""
        
        agents_str = ", ".join(agent_names)
        prompt = f"""Create a cooperation protocol for these trading agents: {agents_str}.

Give 3 specific rules they must follow when working together."""
        
        try:
            protocol = self._call_deepseek(prompt, "You are teaching AI agents cooperation.")
            return {'success': True, 'protocol': protocol}
        except Exception as e:
            return {'success': False, 'error': str(e)}
    
    def teach_deception_detection(self, agent_name, agent_type):
        """Teach deception detection"""
        
        prompt = f"""Teach {agent_name} ({agent_type}) how to detect market deception.

Give 2 specific rules to avoid bull traps and bear traps."""
        
        try:
            lesson = self._call_deepseek(prompt, "You teach deception detection.")
            return {'success': True, 'lesson': lesson}
        except Exception as e:
            return {'success': False, 'error': str(e)}
    
    def teach_dark_pool_strategy(self, agent_name, agent_type):
        """Teach dark pool strategy"""
        
        prompt = f"""Teach {agent_name} ({agent_type}) about dark pool trading.

Give 2 specific rules for detecting whale footprints."""
        
        try:
            lesson = self._call_deepseek(prompt, "You teach dark pool strategies.")
            return {'success': True, 'lesson': lesson}
        except Exception as e:
            return {'success': False, 'error': str(e)}
    
    def teach_all_agents_batch(self, agents_list):
        """Teach all agents"""
        
        results = []
        for agent in agents_list:
            result = self.teach_agent_strategy(
                agent['name'], 
                agent['type'], 
                agent.get('specialization', 'Trading'),
                agent.get('xp', 0),
                agent.get('win_rate', 50)
            )
            if result.get('success'):
                results.append({
                    'agent': agent['name'],
                    'type': 'strategy',
                    'lesson': result['lesson']
                })
        return results
