"""
Voting Configuration - Only relevant agents vote per layer
"""

# ============ VOTING WEIGHTS PER LAYER ============
# Each layer contributes differently to final decision

LAYER_WEIGHTS = {
    'direction': 0.35,      # 35% - Most important (trend is king)
    'confirmation': 0.30,   # 30% - Confirms direction
    'entry': 0.25,          # 25% - Timing and entry
    'risk': 0.10,           # 10% - Override/veto power
}

# ============ AGENTS THAT VOTE PER LAYER ============

# Layer 1: DIRECTION AGENTS (4H/1H/Daily)
# These agents determine the primary trend
DIRECTION_VOTING_AGENTS = [
    'Agent_K',   # Ichimoku (4H) - Primary direction
    'Agent_A',   # Trend Follower (1H) - Secondary direction
    'Agent_N',   # Intermarket (4H) - Correlation check
    'Agent_O',   # Seasonality (Daily) - Macro context
]

# Weight within direction layer
DIRECTION_WEIGHTS = {
    'Agent_K': 1.3,   # Highest weight - Ichimoku is primary
    'Agent_A': 1.0,   # Medium weight - Trend confirmation
    'Agent_N': 0.9,   # Lower weight - Intermarket
    'Agent_O': 0.7,   # Lowest weight - Seasonality
}

# Layer 2: CONFIRMATION AGENTS (15M)
# These agents confirm the direction is valid
CONFIRMATION_VOTING_AGENTS = [
    'Agent_F',   # Pattern Recognition (15M)
    'Agent_I',   # Sentiment & Volume (15M)
    'Agent_G',   # Whale Tracker (15M)
    'Agent_P',   # Whisper Dark Pool (15M)
]

CONFIRMATION_WEIGHTS = {
    'Agent_F': 1.0,
    'Agent_I': 1.0,
    'Agent_G': 1.1,  # Whale confirmation is important
    'Agent_P': 0.9,
}

# Layer 3: ENTRY AGENTS (5M)
# These agents provide precise entry timing
ENTRY_VOTING_AGENTS = [
    'Agent_R',   # Supply/Demand (5M)
    'Agent_H',   # Fibonacci (5M)
    'Agent_B',   # Mean Reversion (5M)
    'Agent_C',   # Momentum (5M)
    'Agent_D',   # Volatility ATR (5M)
    'Agent_J',   # Volume Master (5M)
]

ENTRY_WEIGHTS = {
    'Agent_R': 1.0,
    'Agent_H': 1.0,
    'Agent_B': 0.8,
    'Agent_C': 0.9,
    'Agent_D': 0.7,
    'Agent_J': 1.0,
}

# Layer 4: RISK AGENTS (Veto Power)
# These agents can block trades
RISK_VOTING_AGENTS = [
    'Agent_W',   # Consensus Aggregator - Final decision
    'Agent_E',   # Microstructure - Order book health
    'Agent_L',   # Fundamental News - Economic events
    'Agent_M',   # Market Profile - Value area
    'Agent_Q',   # Dark Pool Whale - Whale direction
    'Agent_T',   # Volume Controller - Final volume check
    'Agent_U',   # Intermarket Pro - Correlation final
    'Agent_V',   # Seasonality Pro - Time check
]

RISK_WEIGHTS = {
    'Agent_W': 1.5,   # Highest weight - Final decision maker
    'Agent_E': 0.8,
    'Agent_L': 1.2,   # High weight - News can block all
    'Agent_M': 0.7,
    'Agent_Q': 1.0,
    'Agent_T': 0.8,
    'Agent_U': 0.7,
    'Agent_V': 0.6,
}

# ============ VETO RULES ============
# Certain agents have absolute veto power
VETO_AGENTS = {
    'Agent_W': 'consensus_failed',
    'Agent_L': 'news_event_detected',
    'Agent_Q': 'whale_opposite_direction',
}

# ============ CONSENSUS THRESHOLDS ============
CONSENSUS_THRESHOLDS = {
    'strong_buy': 80,   # 80%+ for strong buy
    'buy': 65,          # 65-79% for buy
    'hold': 45,         # 45-64% for hold
    'sell': -65,        # -65% to -79% for sell
    'strong_sell': -80, # -80%+ for strong sell
}

# ============ HELPER FUNCTIONS ============
def get_voting_agents():
    """Get all agents that participate in voting"""
    return (DIRECTION_VOTING_AGENTS + 
            CONFIRMATION_VOTING_AGENTS + 
            ENTRY_VOTING_AGENTS + 
            RISK_VOTING_AGENTS)

def get_agent_weight(agent_name):
    """Get voting weight for an agent"""
    if agent_name in DIRECTION_WEIGHTS:
        return DIRECTION_WEIGHTS[agent_name]
    if agent_name in CONFIRMATION_WEIGHTS:
        return CONFIRMATION_WEIGHTS[agent_name]
    if agent_name in ENTRY_WEIGHTS:
        return ENTRY_WEIGHTS[agent_name]
    if agent_name in RISK_WEIGHTS:
        return RISK_WEIGHTS[agent_name]
    return 0.5

def get_agent_layer(agent_name):
    """Determine which layer an agent belongs to"""
    if agent_name in DIRECTION_VOTING_AGENTS:
        return 'direction'
    if agent_name in CONFIRMATION_VOTING_AGENTS:
        return 'confirmation'
    if agent_name in ENTRY_VOTING_AGENTS:
        return 'entry'
    if agent_name in RISK_VOTING_AGENTS:
        return 'risk'
    return None

def print_voting_structure():
    """Print human-readable voting structure"""
    print("\n" + "=" * 60)
    print("🗳️ LAYER-BASED VOTING STRUCTURE")
    print("=" * 60)
    
    print(f"\n🔵 LAYER 1 - DIRECTION (35% weight)")
    for agent in DIRECTION_VOTING_AGENTS:
        print(f"   {agent}: weight {DIRECTION_WEIGHTS.get(agent, 1.0)}")
    
    print(f"\n🟢 LAYER 2 - CONFIRMATION (30% weight)")
    for agent in CONFIRMATION_VOTING_AGENTS:
        print(f"   {agent}: weight {CONFIRMATION_WEIGHTS.get(agent, 1.0)}")
    
    print(f"\n🟡 LAYER 3 - ENTRY (25% weight)")
    for agent in ENTRY_VOTING_AGENTS:
        print(f"   {agent}: weight {ENTRY_WEIGHTS.get(agent, 1.0)}")
    
    print(f"\n🔴 LAYER 4 - RISK (10% weight)")
    for agent in RISK_VOTING_AGENTS:
        print(f"   {agent}: weight {RISK_WEIGHTS.get(agent, 1.0)}")
    
    print(f"\n⛔ VETO AGENTS: {', '.join(VETO_AGENTS.keys())}")
    print("=" * 60)
