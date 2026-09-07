"""
Granularity Mapping for Multi-Agent Trading System
Maps each agent role to OANDA candle timeframe
"""

from enum import Enum

class Granularity(Enum):
    """OANDA granularity levels"""
    M1 = "M1"      # 1 minute
    M5 = "M5"      # 5 minutes
    M15 = "M15"    # 15 minutes
    M30 = "M30"    # 30 minutes
    H1 = "H1"      # 1 hour
    H4 = "H4"      # 4 hours
    D = "D"        # 1 day
    W = "W"        # 1 week

# ============ AGENT TIME FRAME MAPPING ============
# Layer 1: Direction (Higher Timeframes)
DIRECTION_AGENTS = {
    'Agent_K': {'timeframe': Granularity.H4, 'role': 'Ichimoku Direction'},
    'Agent_A': {'timeframe': Granularity.H1, 'role': 'Trend Direction'},
    'Agent_O': {'timeframe': Granularity.D, 'role': 'Seasonality'},
    'Agent_N': {'timeframe': Granularity.H4, 'role': 'Intermarket'},
}

# Layer 2: Confirmation (Medium Timeframes)
CONFIRMATION_AGENTS = {
    'Agent_F': {'timeframe': Granularity.M15, 'role': 'Pattern Recognition'},
    'Agent_I': {'timeframe': Granularity.M15, 'role': 'Sentiment & Volume'},
    'Agent_G': {'timeframe': Granularity.M15, 'role': 'Whale Tracker'},
    'Agent_P': {'timeframe': Granularity.M15, 'role': 'Whisper Dark Pool'},
}

# Layer 3: Timing & Entry (Lower Timeframes)
ENTRY_AGENTS = {
    'Agent_R': {'timeframe': Granularity.M5, 'role': 'Supply/Demand'},
    'Agent_H': {'timeframe': Granularity.M5, 'role': 'Fibonacci'},
    'Agent_B': {'timeframe': Granularity.M5, 'role': 'Mean Reversion'},
    'Agent_C': {'timeframe': Granularity.M5, 'role': 'Momentum'},
    'Agent_D': {'timeframe': Granularity.M5, 'role': 'Volatility ATR'},
    'Agent_J': {'timeframe': Granularity.M5, 'role': 'Volume Master'},
}

# Layer 4: Risk & Execution (Real-time / All)
RISK_AGENTS = {
    'Agent_W': {'timeframe': 'ALL', 'role': 'Consensus Aggregator'},
    'Agent_E': {'timeframe': Granularity.M1, 'role': 'Microstructure'},
    'Agent_L': {'timeframe': 'REAL_TIME', 'role': 'Fundamental News'},
    'Agent_M': {'timeframe': Granularity.M5, 'role': 'Market Profile'},
    'Agent_Q': {'timeframe': Granularity.M15, 'role': 'Dark Pool Whale'},
    'Agent_T': {'timeframe': Granularity.M15, 'role': 'Volume Controller'},
    'Agent_U': {'timeframe': Granularity.M15, 'role': 'Intermarket Pro'},
    'Agent_V': {'timeframe': Granularity.M5, 'role': 'Seasonality Pro'},
}

# Complete mapping for all 23 agents
AGENT_GRANULARITY = {}
AGENT_GRANULARITY.update(DIRECTION_AGENTS)
AGENT_GRANULARITY.update(CONFIRMATION_AGENTS)
AGENT_GRANULARITY.update(ENTRY_AGENTS)
AGENT_GRANULARITY.update(RISK_AGENTS)

# ============ CANDLE COUNT PER TIMEFRAME ============
CANDLE_COUNTS = {
    Granularity.M1: 100,    # 100 minutes
    Granularity.M5: 100,    # ~8 hours
    Granularity.M15: 100,   # 25 hours
    Granularity.M30: 100,   # 50 hours
    Granularity.H1: 100,    # 4 days
    Granularity.H4: 100,    # ~16 days
    Granularity.D: 100,     # 100 days
    Granularity.W: 52,      # 1 year
}

# ============ TTL CACHE PER TIMEFRAME ============
# How long to cache candles for each timeframe (seconds)
CACHE_TTL_SECONDS = {
    Granularity.M1: 30,     # 30 seconds - price changes fast
    Granularity.M5: 60,     # 1 minute
    Granularity.M15: 120,   # 2 minutes
    Granularity.M30: 180,   # 3 minutes
    Granularity.H1: 300,    # 5 minutes
    Granularity.H4: 900,    # 15 minutes
    Granularity.D: 3600,    # 1 hour
    Granularity.W: 86400,   # 24 hours
}

# ============ INDICATOR PARAMETERS BY TIMEFRAME ============
INDICATOR_PARAMS = {
    Granularity.M5: {
        'rsi_period': 7,
        'ma_fast': 10,
        'ma_slow': 30,
        'bb_period': 14,
        'atr_period': 7,
    },
    Granularity.M15: {
        'rsi_period': 9,
        'ma_fast': 20,
        'ma_slow': 50,
        'bb_period': 20,
        'atr_period': 14,
    },
    Granularity.H1: {
        'rsi_period': 14,
        'ma_fast': 20,
        'ma_slow': 50,
        'bb_period': 20,
        'atr_period': 14,
    },
    Granularity.H4: {
        'rsi_period': 14,
        'ma_fast': 20,
        'ma_slow': 50,
        'bb_period': 20,
        'atr_period': 14,
    },
    Granularity.D: {
        'rsi_period': 14,
        'ma_fast': 20,
        'ma_slow': 200,
        'bb_period': 20,
        'atr_period': 14,
    },
}

# ============ HELPER FUNCTIONS ============
def get_agent_timeframe(agent_name):
    """Get granularity for a specific agent"""
    return AGENT_GRANULARITY.get(agent_name, {}).get('timeframe', Granularity.M15)

def get_agent_role(agent_name):
    """Get role description for a specific agent"""
    return AGENT_GRANULARITY.get(agent_name, {}).get('role', 'Unknown')

def get_candle_count(granularity):
    """Get number of candles to fetch for a timeframe"""
    return CANDLE_COUNTS.get(granularity, 100)

def get_cache_ttl(granularity):
    """Get cache TTL for a timeframe"""
    return CACHE_TTL_SECONDS.get(granularity, 120)

def get_indicator_params(granularity):
    """Get indicator parameters for a timeframe"""
    return INDICATOR_PARAMS.get(granularity, INDICATOR_PARAMS[Granularity.M15])

def get_timeframes_for_cycle():
    """Get all timeframes needed for a complete trading cycle"""
    timeframes = set()
    for agent, config in AGENT_GRANULARITY.items():
        tf = config.get('timeframe')
        if tf != 'ALL' and tf != 'REAL_TIME':
            timeframes.add(tf)
    return sorted(list(timeframes), key=lambda x: x.value if hasattr(x, 'value') else str(x))

def print_granularity_map():
    """Print human-readable granularity mapping"""
    print("\n" + "=" * 60)
    print("📊 AGENT GRANULARITY MAPPING")
    print("=" * 60)
    
    print("\n🔵 LAYER 1 - DIRECTION (Higher Timeframes)")
    for agent, config in DIRECTION_AGENTS.items():
        tf = config['timeframe'].value if hasattr(config['timeframe'], 'value') else str(config['timeframe'])
        print(f"   {agent}: {tf} - {config['role']}")
    
    print("\n🟢 LAYER 2 - CONFIRMATION (15 Minutes)")
    for agent, config in CONFIRMATION_AGENTS.items():
        tf = config['timeframe'].value if hasattr(config['timeframe'], 'value') else str(config['timeframe'])
        print(f"   {agent}: {tf} - {config['role']}")
    
    print("\n🟡 LAYER 3 - TIMING & ENTRY (5 Minutes)")
    for agent, config in ENTRY_AGENTS.items():
        tf = config['timeframe'].value if hasattr(config['timeframe'], 'value') else str(config['timeframe'])
        print(f"   {agent}: {tf} - {config['role']}")
    
    print("\n🔴 LAYER 4 - RISK & EXECUTION")
    for agent, config in RISK_AGENTS.items():
        tf = config['timeframe'].value if hasattr(config['timeframe'], 'value') else str(config['timeframe'])
        print(f"   {agent}: {tf} - {config['role']}")
    
    print("\n" + "=" * 60)
