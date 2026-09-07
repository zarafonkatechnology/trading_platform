"""
Advanced Agent Teaching System
Teaches agents: cooperation, deception detection, dark pool strategies, and game theory
"""

import json
from datetime import datetime

class AdvancedAgentTeaching:
    """Teaches agents strategic thinking and cooperation"""
    
    # Cooperation Strategies
    COOPERATION_STRATEGIES = {
        'whale_alliance': {
            'name': 'Whale Alliance Protocol',
            'rule': 'When Agent_G (Whale Tracker) detects accumulation, Agent_P (Whisper) and Agent_Q (Dark Pool) MUST confirm before any trade.',
            'agents': ['Agent_G', 'Agent_P', 'Agent_Q'],
            'logic': 'IF Whale Tracker sees accumulation AND Whisper confirms dark pool activity THEN increase confidence to 95%'
        },
        'volume_ichimoku_sync': {
            'name': 'Volume-Ichimoku Synchronization',
            'rule': 'Agent_J (Volume) and Agent_K (Ichimoku) must agree on breakout direction.',
            'agents': ['Agent_J', 'Agent_K'],
            'logic': 'IF Ichimoku says breakout AND Volume confirms surge THEN execute; ELSE HOLD'
        },
        'sentiment_contrarian': {
            'name': 'Contrarian Consensus',
            'rule': 'When Agent_I (Sentiment) shows extreme readings, other agents must vote opposite.',
            'agents': ['Agent_I', 'Agent_A', 'Agent_B', 'Agent_C'],
            'logic': 'IF Sentiment > 80 (extreme greed) THEN all technical agents vote SELL'
        }
    }
    
    # Deception Detection Strategies
    DECEPTION_STRATEGIES = {
        'spoof_detection': {
            'name': 'Spoofing Detection Protocol',
            'rule': 'Large orders appearing then disappearing within 2 seconds = DECEPTION',
            'action': 'IGNORE the move, do NOT follow',
            'teaching': 'When you see a large wall that vanishes instantly, it is a trap. Wait 30 seconds for real direction.'
        },
        'bull_trap_avoidance': {
            'name': 'Bull Trap Avoidance',
            'rule': 'Price breaks resistance but volume is decreasing = TRAP',
            'action': 'DO NOT BUY, wait for volume confirmation',
            'teaching': 'Institutions create fake breakouts to trap retail. Always check volume confirmation.'
        },
        'bear_trap_avoidance': {
            'name': 'Bear Trap Avoidance',
            'rule': 'Price breaks support but volume is low = TRAP',
            'action': 'DO NOT SELL, wait for volume surge',
            'teaching': 'Smart money stops hunting. Low volume breakdowns are often reversals.'
        },
        'dark_pool_hidden_accumulation': {
            'name': 'Dark Pool Hidden Accumulation',
            'rule': 'Price flat but dark pool volume increasing = WHALES BUYING',
            'action': 'BUY before price moves',
            'teaching': 'Institutions accumulate in dark pools before marking up price. Be early.'
        },
        'dark_pool_hidden_distribution': {
            'name': 'Dark Pool Hidden Distribution',
            'rule': 'Price flat but dark pool selling increasing = WHALES SELLING',
            'action': 'SELL before price drops',
            'teaching': 'Whales distribute in dark pools before marking down price. Exit early.'
        }
    }
    
    # Dark Pool Strategies
    DARK_POOL_STRATEGIES = {
        'iceberg_detection': {
            'name': 'Iceberg Order Detection',
            'rule': 'Repeated same size trades at same price = HIDDEN ORDER',
            'action': 'Trade in same direction as the hidden order',
            'teaching': 'Whales use iceberg orders to hide size. Follow the repeat pattern.'
        },
        'dark_liquidity_hunting': {
            'name': 'Dark Liquidity Hunting',
            'rule': 'Price approaches known dark pool levels = LIQUIDITY AVAILABLE',
            'action': 'Place orders at dark pool levels',
            'teaching': 'Dark pools have hidden liquidity at key levels. Use them for better fills.'
        },
        'whale_footprint_following': {
            'name': 'Whale Footprint Following',
            'rule': 'Large dark pool trade at Fibonacci level = WHALE SIGNAL',
            'action': 'Follow whale direction',
            'teaching': 'When whales show their hand at key levels, follow them.'
        }
    }
    
    @staticmethod
    def generate_cooperation_lesson(agent_name, all_agents):
        """Generate a lesson about agent cooperation"""
        
        if agent_name == 'Agent_G' or agent_name == 'Agent_P' or agent_name == 'Agent_Q':
            return {
                'lesson': f"""🤝 WHALE ALLIANCE PROTOCOL for {agent_name}:

You are part of the Whale Detection Team. Your job:
1. Agent_G detects whale accumulation in COT/futures
2. Agent_P listens for dark pool whispers
3. Agent_Q confirms FINRA TRF dark trades

Cooperation Rule: When any of you sees whale activity, alert the others.
Confidence Multiplier: If 2 of you agree → 80% confidence. If all 3 agree → 95% confidence.

Deception Warning: Sometimes whales create fake signals. Always wait for 2 confirmations.""",
                'xp': 50,
                'type': 'cooperation'
            }
        
        elif agent_name == 'Agent_J' or agent_name == 'Agent_K':
            return {
                'lesson': f"""📊 VOLUME-ICHIMOKU SYNC for {agent_name}:

Your cooperation rule:
- Agent_J (Volume) detects volume surges
- Agent_K (Ichimoku) detects cloud breakouts

The Golden Rule: NEVER trade a breakout unless BOTH of you agree.
If Ichimoku says BUY but volume is low → HOLD (fake breakout)
If volume surges but price is in cloud → WAIT (no confirmation)

This prevents bull traps and bear traps.""",
                'xp': 45,
                'type': 'cooperation'
            }
        
        elif agent_name == 'Agent_I':
            return {
                'lesson': f"""📰 CONTRARIAN MASTER for {agent_name}:

You are the sentiment expert. Your special power:
When you detect EXTREME sentiment (>80 or <20), you have VETO power.

Cooperation Rule: 
- Tell Agent_A, Agent_B, Agent_C to vote OPPOSITE to sentiment
- Example: Extreme greed (90%) → tell them to SELL
- Example: Extreme fear (15%) → tell them to BUY

This is how smart money profits - by trading against the crowd.""",
                'xp': 55,
                'type': 'cooperation'
            }
        
        return None
    
    @staticmethod
    def generate_deception_lesson(agent_name):
        """Generate a lesson about detecting market deception"""
        
        lessons = {
            'Agent_A': {
                'lesson': """🎭 DECEPTION DETECTION for Trend Follower:

The Fake Trend Trap: Institutions create beautiful trends to trap retail.
How to detect: Check volume. If volume is DECREASING while price is trending, it's a DECEPTION.

Your Rule: Only trust trends with INCREASING volume.
If volume drops for 3 consecutive candles while price rises → EXIT or DON'T ENTER.

Remember: Real trends have participation. Fake trends are just painting the tape.""",
                'xp': 40
            },
            'Agent_B': {
                'lesson': """🎭 DECEPTION DETECTION for Mean Reversion:

The RSI Trap: RSI can stay oversold/overbought for weeks.
How to detect: Wait for CANDLE CONFIRMATION, not just RSI.

Your Rule: RSI < 30 + BULLISH ENGULFING candle = BUY signal
RSI > 70 + BEARISH ENGULFING candle = SELL signal

Never trust RSI alone. Always wait for price action confirmation.""",
                'xp': 40
            },
            'Agent_G': {
                'lesson': """🐋 DECEPTION DETECTION for Whale Tracker:

The Whale Fakeout: Sometimes whales create fake accumulation to trap followers.
How to detect: Check if multiple whales are moving together or just one.

Your Rule: Look for COORDINATED whale activity across multiple instruments.
If only one whale is moving while others are silent → SUSPECT DECEPTION.

Real whale moves involve multiple institutions. Single whale = possible trap.""",
                'xp': 50
            },
            'Agent_P': {
                'lesson': """🕵️ DECEPTION DETECTION for Whisper Analyst:

The Fake Whisper: Not all dark pool activity is real accumulation.
How to detect: Check if dark trades are happening at MID PRICE or at extremes.

Your Rule: 
- Dark trades at mid-price = REAL (institutions hiding)
- Dark trades at bid/ask extremes = POSSIBLE DECEPTION (painting tape)

Real whales trade at mid-price to hide. Fake whales trade at extremes to be seen.""",
                'xp': 45
            }
        }
        
        return lessons.get(agent_name, None)
    
    @staticmethod
    def generate_dark_pool_lesson(agent_name):
        """Generate a lesson about dark pool strategies"""
        
        if agent_name in ['Agent_P', 'Agent_Q', 'Agent_G']:
            return {
                'lesson': f"""🌑 DARK POOL MASTERY for {agent_name}:

How Dark Pools Work:
1. Institutions hide orders in dark pools to avoid slippage
2. Their footprints appear in FINRA TRF data AFTER execution
3. They often trade at FIBONACCI levels and SUPPORT/RESISTANCE

Your Strategy:
- Track dark pool volume percentage (>40% = significant)
- Watch for repeat trades at same price (iceberg orders)
- Alert other whales when you detect accumulation

The Golden Rule: When dark pool volume spikes at a key level, FOLLOW IT.
Whales are smarter than retail. Their hidden footprints show the real direction.

Deception Alert: Sometimes dark pool activity is just hedging. Look for CONSISTENCY over multiple days.""",
                'xp': 60,
                'type': 'dark_pool'
            }
        
        return None


def teach_all_agents_advanced():
    """Teach all agents advanced strategies"""
    
    teacher = AdvancedAgentTeaching()
    all_agents = ['Agent_A', 'Agent_B', 'Agent_C', 'Agent_D', 'Agent_E',
                  'Agent_F', 'Agent_G', 'Agent_H', 'Agent_I', 'Agent_J',
                  'Agent_K', 'Agent_L', 'Agent_M', 'Agent_N', 'Agent_O',
                  'Agent_P', 'Agent_Q', 'Agent_R', 'Agent_S', 'Agent_T',
                  'Agent_U', 'Agent_V']
    
    results = []
    
    for agent in all_agents:
        # Try each teaching type
        lesson = None
        xp = 0
        
        coop = teacher.generate_cooperation_lesson(agent, all_agents)
        if coop:
            lesson = coop['lesson']
            xp = coop['xp']
        
        if not lesson:
            deception = teacher.generate_deception_lesson(agent)
            if deception:
                lesson = deception['lesson']
                xp = deception['xp']
        
        if not lesson:
            dark = teacher.generate_dark_pool_lesson(agent)
            if dark:
                lesson = dark['lesson']
                xp = dark['xp']
        
        if lesson:
            results.append({
                'agent': agent,
                'lesson': lesson,
                'xp_awarded': xp
            })
    
    return results
