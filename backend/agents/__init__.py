# agents/__init__.py
"""
Agents Package
"""

from .agent_i_sentiment import SentimentMaster
from .base_agent import BaseAgent
from .agent_x_spread import AgentXSpread  # ← NEW

__all__ = ['SentimentMaster', 'BaseAgent',  'AgentXSpread']