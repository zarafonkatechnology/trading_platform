"""
Teaching Content Generator
What DeepSeek teaches each agent type
"""

# Teaching templates for different agent types
TEACHING_CATEGORIES = {
    'Agent_A': {
        'type': 'Trend Follower',
        'strategies': [
            'Moving Average Crossovers',
            'Trend Strength Confirmation',
            'Pullback Entry Techniques'
        ],
        'key_rules': [
            'Never trade against the 200-period MA',
            'Wait for pullback to 20-EMA before entering',
            'Exit when trend shows divergence'
        ],
        'cooperation': 'Share trend signals with Agent_B for confirmation'
    },
    'Agent_B': {
        'type': 'Mean Reversion',
        'strategies': [
            'RSI Divergence Trading',
            'Bollinger Band Fades',
            'Support/Resistance Reversals'
        ],
        'key_rules': [
            'RSI must be <30 for BUY, >70 for SELL',
            'Wait for candle confirmation, not just RSI',
            'Use volume to confirm reversal'
        ],
        'cooperation': 'Get volume confirmation from Agent_J before trading'
    },
    'Agent_C': {
        'type': 'Momentum',
        'strategies': [
            'Breakout Momentum Trading',
            'Gap and Go',
            'Continuation Patterns'
        ],
        'key_rules': [
            'Volume must confirm momentum',
            'Exit when momentum indicators diverge',
            'Trail stops aggressively'
        ],
        'cooperation': 'Confirm breakouts with Agent_K (Ichimoku)'
    },
    'Agent_G': {
        'type': 'Whale Tracker',
        'strategies': [
            'COT Report Analysis',
            'Open Interest Tracking',
            'Commercial Hedging Patterns'
        ],
        'key_rules': [
            'Follow commercials, not speculators',
            'Extreme COT readings signal reversals',
            'Watch for record net positions'
        ],
        'cooperation': 'Alert Agent_P and Agent_Q of whale activity'
    },
    'Agent_P': {
        'type': 'Whisper Analyst',
        'strategies': [
            'Dark Pool Detection',
            'FINRA TRF Scanning',
            'Iceberg Order Recognition'
        ],
        'key_rules': [
            'Trades > $1M at mid-price = DARK POOL',
            'Repeated same size = ICEBERG ORDER',
            'Dark pool volume > 40% = SIGNIFICANT'
        ],
        'cooperation': 'Share dark pool findings with Agent_G and Agent_Q'
    },
    'Agent_Q': {
        'type': 'Dark Pool Whale',
        'strategies': [
            'Whale Footprint Following',
            'Dark Pool Accumulation Trading',
            'Institutional Order Flow'
        ],
        'key_rules': [
            'Follow consistent dark pool direction',
            'Multiple dark trades at same level = STRONG SIGNAL',
            'Exit when dark pool activity reverses'
        ],
        'cooperation': 'Confirm whale signals with Agent_G'
    }
}

# Deception patterns to teach
DECEPTION_PATTERNS = {
    'bull_trap': {
        'name': 'Bull Trap',
        'description': 'Price breaks above resistance but quickly reverses down',
        'detection_rules': [
            'Volume DECREASING during breakout',
            'RSI > 80 (overbought)',
            'Price closes below breakout level within 3 candles'
        ],
        'action': 'DO NOT BUY - Wait for retest and confirmation'
    },
    'bear_trap': {
        'name': 'Bear Trap',
        'description': 'Price breaks below support but quickly reverses up',
        'detection_rules': [
            'Volume DECREASING during breakdown',
            'RSI < 20 (oversold)',
            'Price closes above breakdown level within 3 candles'
        ],
        'action': 'DO NOT SELL - Wait for retest and confirmation'
    },
    'spoofing': {
        'name': 'Order Book Spoofing',
        'description': 'Large orders placed then cancelled to manipulate price',
        'detection_rules': [
            'Large bid/ask wall appears suddenly',
            'Wall disappears within 2 seconds',
            'Price moves opposite to wall direction'
        ],
        'action': 'IGNORE the move - Wait 30 seconds for real direction'
    }
}

# Cooperation protocols
COOPERATION_PROTOCOLS = {
    'whale_team': {
        'agents': ['Agent_G', 'Agent_P', 'Agent_Q'],
        'protocol': """
        WHALE TEAM COOPERATION RULES:
        1. Agent_G (Whale Tracker) detects COT/futures whale activity → SHARE with P and Q
        2. Agent_P (Whisper) detects dark pool trades → CONFIRM with G
        3. Agent_Q (Dark Pool) detects FINRA TRF prints → ALERT G and P
        4. When 2 of 3 agree → 80% confidence
        5. When 3 of 3 agree → 95% confidence - EXECUTE
        """
    },
    'technical_team': {
        'agents': ['Agent_A', 'Agent_B', 'Agent_C', 'Agent_D'],
        'protocol': """
        TECHNICAL TEAM COOPERATION RULES:
        1. Agent_A (Trend) sets direction
        2. Agent_B (Mean Reversion) identifies extremes
        3. Agent_C (Momentum) confirms strength
        4. Agent_D (Volatility) sets stop levels
        5. Trade only when 3 of 4 agree
        """
    }
}
