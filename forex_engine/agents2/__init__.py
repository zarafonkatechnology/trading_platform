# agents2/__init__.py

# Import your actual agent files
from .forex_agent_x import ForexAgentX
from .forex_agent_u import ForexLiquidityAgentEnhanced
from .forex_agent_d import AgentDVolatility

__all__ = [
    'ForexAgentX',
    'ForexLiquidityAgentEnhanced',
    'AgentDVolatility'
]