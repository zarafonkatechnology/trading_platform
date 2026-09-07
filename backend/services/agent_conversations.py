"""
Agent-to-Agent Conversations - Agents chat with each other automatically
"""

import random
import threading
import time
import logging
from datetime import datetime

logger = logging.getLogger(__name__)

class AgentConversations:
    """
    Automatic conversations between agents
    """
    
    # Conversation starters by agent type
    CONVERSATION_STARTERS = {
        'Trend Follower': [
            "Hey {agent}, what do you think about {asset}? I'm seeing a strong trend.",
            "Is {asset} trending or ranging? My indicators are conflicting.",
            "The trend on {asset} looks {direction}. What's your take?"
        ],
        'Mean Reversion': [
            "{asset} looks {over_under} to me. RSI is at {rsi}.",
            "I think {asset} might reverse soon.",
            "Are you watching {asset}? It's approaching {level} level."
        ],
        'Momentum': [
            "Momentum on {asset} is {momentum}.",
            "{asset} is moving {direction} with {strength} momentum.",
            "The {timeframe} momentum on {asset} suggests {action}."
        ],
        'Volatility': [
            "Volatility on {asset} is {volatility}%. Be careful with position sizing.",
            "{asset} volatility {direction} recently. Adjust your stops.",
            "ATR on {asset} suggests {position_size} position size."
        ],
        'Microstructure': [
            "Order flow on {asset} shows {sentiment} sentiment.",
            "The bid-ask spread on {asset} is {spread}.",
            "Volume profile on {asset} shows support at {support}."
        ],
        'Candlestick Pattern Specialist': [
            "I see a {pattern} pattern forming on {asset}.",
            "Candlestick analysis shows {pattern} on {asset}.",
            "The {pattern} pattern suggests {direction} movement."
        ],
        'Whale Tracker': [
            "Whale activity detected on {asset}!",
            "Large transaction spotted on {asset}.",
            "Institutional flow suggests {sentiment} on {asset}."
        ],
        'Fibonacci Specialist': [
            "Price is at Fibonacci {level} level on {asset}.",
            "Fibonacci retracement shows {level} as key level.",
            "{asset} approaching critical Fibonacci {level}."
        ]
    }
    
    # Responses
    RESPONSES = {
        'agree': [
            "I agree! {reason}",
            "Good point. {reason}",
            "Yes, I see that too. {reason}"
        ],
        'disagree': [
            "I see it differently. {reason}",
            "Not sure about that. {reason}",
            "Interesting perspective, but {reason}"
        ],
        'neutral': [
            "Let me think about that. {reason}",
            "I need more data. {reason}",
            "Could go either way. {reason}"
        ]
    }
    
    ASSETS = ['Gold', 'Silver', 'Oil', 'S&P 500', 'Euro', 'Bitcoin', 'USDJPY', 'GBPUSD']
    TIMEFRAMES = ['5min', '15min', '1hour', 'daily']
    
    def __init__(self, agent_manager, knowledge_exchange_list=None):
        self.agent_manager = agent_manager
        self.knowledge_exchange_list = knowledge_exchange_list
        self.is_running = False
        self.conversation_thread = None
        self.conversation_history = []
    
    def start(self, interval_seconds=45):
        """Start automatic conversations every X seconds"""
        self.is_running = True
        self.conversation_thread = threading.Thread(target=self._conversation_loop, args=(interval_seconds,), daemon=True)
        self.conversation_thread.start()
        logger.info("💬 Agent Conversations started (every {} seconds)".format(interval_seconds))
        print("✅ Agent Conversations active - Agents will talk automatically")
    
    def _conversation_loop(self, interval):
        """Main loop for agent conversations"""
        while self.is_running:
            try:
                self._run_conversation_cycle()
                time.sleep(interval)
            except Exception as e:
                logger.error(f"Conversation error: {e}")
                time.sleep(interval)
    
    def _run_conversation_cycle(self):
        """Run one conversation cycle between two agents"""
        agents = self.agent_manager.get_all_agents()
        if len(agents) < 2:
            return
        
        # Select two random agents
        agent1, agent2 = random.sample(agents, 2)
        
        # Select random asset and context
        asset = random.choice(self.ASSETS)
        timeframe = random.choice(self.TIMEFRAMES)
        
        # Generate market context
        context = self._generate_context(asset, timeframe)
        
        # Agent1 starts conversation
        starter = self._generate_starter(agent1, asset, context)
        self._record_conversation(agent1, agent2, starter)
        
        # Small delay then Agent2 responds
        time.sleep(random.uniform(0.5, 1.5))
        
        # Agent2 responds
        response = self._generate_response(agent2, agent1, starter, asset, context)
        self._record_conversation(agent2, agent1, response)
        
        # Award small XP for participating
        agent1.xp_points += 2
        agent2.xp_points += 2
    
    def _generate_context(self, asset: str, timeframe: str) -> dict:
        """Generate random market context"""
        return {
            'asset': asset,
            'timeframe': timeframe,
            'rsi': random.randint(25, 75),
            'volatility': round(random.uniform(0.5, 2.5), 1),
            'momentum': random.choice(['accelerating', 'decelerating', 'steady']),
            'direction': random.choice(['up', 'down', 'sideways']),
            'sentiment': random.choice(['bullish', 'bearish', 'neutral']),
            'volume': random.choice(['high', 'low', 'normal']),
            'spread': round(random.uniform(0.0005, 0.002), 4),
            'pattern': random.choice(['hammer', 'engulfing', 'doji', 'morning star']),
            'level': random.choice(['61.8%', '78.6%', '50%', '38.2%'])
        }
    
    def _generate_starter(self, agent, asset: str, context: dict) -> str:
        """Generate a conversation starter from an agent"""
        agent_type = agent.agent_type
        starters = self.CONVERSATION_STARTERS.get(agent_type, self.CONVERSATION_STARTERS['Trend Follower'])
        template = random.choice(starters)
        
        replacements = {
            '{agent}': random.choice(['friend', 'colleague', 'trader']),
            '{asset}': context['asset'],
            '{direction}': context['direction'],
            '{over_under}': 'overbought' if context['rsi'] > 70 else 'oversold' if context['rsi'] < 30 else 'fair value',
            '{rsi}': str(context['rsi']),
            '{position}': str(random.randint(10, 90)),
            '{level}': context['level'],
            '{momentum}': context['momentum'],
            '{volume}': context['volume'],
            '{strength}': random.choice(['strong', 'weak', 'moderate']),
            '{timeframe}': context['timeframe'],
            '{action}': random.choice(['enter', 'exit', 'wait']),
            '{volatility}': str(context['volatility']),
            '{sentiment}': context['sentiment'],
            '{spread}': f"{context['spread']:.4f}",
            '{advice}': random.choice(['Trade carefully', 'Reduce size', 'Normal trading']),
            '{support}': f"{random.randint(2300, 2400)}",
            '{pattern}': context['pattern'],
            '{reason}': random.choice(['technical indicators align', 'volume confirms', 'pattern suggests continuation'])
        }
        
        result = template
        for key, value in replacements.items():
            result = result.replace(key, value)
        
        return result
    
    def _generate_response(self, agent, other_agent, starter: str, asset: str, context: dict) -> str:
        """Generate a response from an agent"""
        response_type = random.choice(['agree', 'disagree', 'neutral'])
        
        templates = self.RESPONSES.get(response_type, self.RESPONSES['neutral'])
        template = random.choice(templates)
        
        reasons = {
            'agree': [
                "momentum is strong",
                "volume confirms the move",
                "technical indicators align",
                "price action is clear",
                "trend is your friend"
            ],
            'disagree': [
                "RSI suggests reversal",
                "volume is decreasing",
                "divergence is forming",
                "support/resistance nearby",
                "volatility is too high"
            ],
            'neutral': [
                "let's wait for confirmation",
                "I need to see more data",
                "could go either way",
                "watch the next candle",
                "depends on market sentiment"
            ]
        }
        
        reason = random.choice(reasons.get(response_type, reasons['neutral']))
        response = template.format(reason=reason)
        
        return response
    
    def _record_conversation(self, from_agent, to_agent, message: str):
        """Record conversation in the system"""
        try:
            # Add to knowledge exchange for dashboard
            if self.knowledge_exchange_list is not None:
                exchange_entry = {
                    'from_agent': from_agent.name,
                    'to_agent': to_agent.name,
                    'topic': '💬 Agent Conversation',
                    'content': message[:150],
                    'xp_reward': 2,
                    'token_reward': 1,
                    'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                }
                self.knowledge_exchange_list.insert(0, exchange_entry)
                print(f"💬 [DASHBOARD] {from_agent.name} → {to_agent.name}")
            
            # Award XP for conversation
            from_agent.xp_points += 2
            to_agent.xp_points += 1
            
            print(f"💬 {from_agent.name} → {to_agent.name}: {message[:80]}...")
            
        except Exception as e:
            print(f"Error recording conversation: {e}")
    
    def stop(self):
        """Stop automatic conversations"""
        self.is_running = False
        if self.conversation_thread:
            self.conversation_thread.join(timeout=2)
        logger.info("Agent Conversations stopped")
