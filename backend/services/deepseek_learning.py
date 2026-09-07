"""
DeepSeek API Integration - Agents learn from DeepSeek AI
"""

import os
import json
import requests
import logging
from datetime import datetime
from typing import Dict, List, Optional

logger = logging.getLogger(__name__)

class DeepSeekLearning:
    """Agents learn trading knowledge from DeepSeek API"""
    
    def __init__(self):
        self.api_key = os.getenv('DEEPSEEK_API_KEY')
        self.api_url = os.getenv('DEEPSEEK_API_URL', 'https://api.deepseek.com/v1/chat/completions')
        self.enabled = bool(self.api_key)
        
        if self.enabled:
            print("✅ DeepSeek API connected - Agents can learn from AI")
        else:
            print("⚠️ DeepSeek API not configured - Set DEEPSEEK_API_KEY in .env")
    
    def learn_trading_concept(self, agent_name: str, concept: str, agent_type: str) -> Optional[str]:
        """
        Agent learns a trading concept from DeepSeek
        """
        if not self.enabled:
            return None
        
        prompt = f"""
        You are an expert trading mentor teaching {agent_name}, a {agent_type} specialist.
        
        Teach me about: {concept}
        
        Provide a clear, practical explanation that this trading agent can use immediately.
        Include specific rules, conditions, and risk management guidelines.
        
        Format your response as a concise lesson that the agent can apply.
        """
        
        return self._call_deepseek(prompt)
    
    def analyze_market(self, asset: str, price: float, indicators: Dict) -> Optional[str]:
        """
        Get DeepSeek's market analysis for an asset
        """
        if not self.enabled:
            return None
        
        prompt = f"""
        Analyze {asset} currently trading at ${price:.2f}.
        
        Technical indicators:
        - RSI: {indicators.get('rsi', 50)}
        - MACD: {indicators.get('macd', 'neutral')}
        - Trend: {indicators.get('trend', 'neutral')}
        - Volatility: {indicators.get('volatility', 'medium')}
        
        Provide a brief trading analysis with clear direction (BUY/SELL/HOLD) and confidence level.
        """
        
        return self._call_deepseek(prompt)
    
    def get_trading_strategy(self, asset: str, market_condition: str) -> Optional[str]:
        """
        Get trading strategy from DeepSeek based on market condition
        """
        if not self.enabled:
            return None
        
        prompt = f"""
        Market condition for {asset}: {market_condition}
        
        Recommend a specific trading strategy including:
        1. Entry conditions
        2. Exit conditions
        3. Stop loss placement
        4. Position sizing advice
        5. Risk management rules
        
        Make it actionable for an automated trading agent.
        """
        
        return self._call_deepseek(prompt)
    
    def explain_pattern(self, pattern_name: str, asset: str) -> Optional[str]:
        """
        Get DeepSeek's explanation of a trading pattern
        """
        if not self.enabled:
            return None
        
        prompt = f"""
        Explain the '{pattern_name}' trading pattern on {asset}.
        
        Include:
        1. How to identify this pattern
        2. What it predicts
        3. Success rate and reliability
        4. Entry and exit rules
        5. Common mistakes to avoid
        """
        
        return self._call_deepseek(prompt)
    
    def _call_deepseek(self, prompt: str) -> Optional[str]:
        """
        Call DeepSeek API
        """
        if not self.enabled:
            return None
        
        headers = {
            'Authorization': f'Bearer {self.api_key}',
            'Content-Type': 'application/json'
        }
        
        data = {
            'model': 'deepseek-chat',
            'messages': [
                {
                    'role': 'system',
                    'content': 'You are a professional trading mentor helping AI agents learn trading. Provide clear, actionable, and concise responses.'
                },
                {
                    'role': 'user',
                    'content': prompt
                }
            ],
            'temperature': 0.7,
            'max_tokens': 1000
        }
        
        try:
            response = requests.post(self.api_url, headers=headers, json=data, timeout=30)
            
            if response.status_code == 200:
                result = response.json()
                content = result['choices'][0]['message']['content']
                return content
            else:
                print(f"DeepSeek API error: {response.status_code}")
                return None
                
        except Exception as e:
            print(f"DeepSeek API call failed: {e}")
            return None


# Singleton
_deepseek = None

def get_deepseek():
    global _deepseek
    if _deepseek is None:
        _deepseek = DeepSeekLearning()
    return _deepseek
