
from typing import Dict

import psycopg2
import psycopg2.extras
import os
from price_helper import get_price_with_fallback, get_multiple_prices
from dotenv import load_dotenv
from backend.agents.agent_a_trend import AgentATrend
from backend.agents.agent_b_mean_reversion import AgentBMeanReversion
from backend.agents.agent_c_momentum import AgentCMomentum
from backend.agents.agent_d_volatility import AgentDVolatility
from backend.agents.agent_e_microstructure import AgentEMicrostructure
from backend.agents.agent_f_candlestick import AgentFCandlestick
from backend.agents.agent_g_whale import AgentGWhale
from backend.agents.agent_h_fibonacci import AgentHFibonacci
from backend.agents.base_agent import BaseAgent
from backend.services.deepseek_learning import get_deepseek
from config.granularity_config import AGENT_GRANULARITY, Granularity, get_timeframes_for_cycle
from .agent_i_sentiment import SentimentMaster
from mt4_price_provider import get_mt4_prices
from .agent_j_volume import VolumeMaster
from .agent_k_ichimoku import IchimokuExpert
from .agent_l_economic import EconomicCalendarMaster
from .agent_m_marketprofile import MarketProfileMaster  # NEW
from .agent_n_intermarket import IntermarketMaster    # NEW
from .agent_o_seasonality import SeasonalityExpert
from .agent_r_supply_demand import SupplyDemandExpert
from .agent_q_darkpool import DarkPoolWhaleAgent
from .agent_s_skeptic import SkepticAgent
from .agent_t_confluence import ConfluenceAgent
from .agent_u_liquidity import LiquidityAgent
from .agent_v_neutral import NeutralPsychologyAgent
from .agent_p_whisper import WhisperAnalyst
load_dotenv()
DB_HOST = os.getenv('DB_HOST', 'localhost')
DB_PORT = os.getenv('DB_PORT', '5432')
DB_NAME = os.getenv('DB_NAME', 'trading_platform')
DB_USER = os.getenv('DB_USER', 'postgres')
DB_PASSWORD = os.getenv('DB_PASSWORD', 'lama')

def get_db():
    import psycopg2
    import psycopg2.extras
    conn = psycopg2.connect(
        host="localhost",
        port=5432,
        database="trading_platform",
        user="postgres",
        password="lama"
    )
    # This makes cursors return dictionaries
    conn.cursor_factory = psycopg2.extras.RealDictCursor
    return conn

class AgentManager:
    def __init__(self):
        self.agents = []
        self.agent_dict = {}
        self.deepseek = get_deepseek()
        self._load_from_db()
    
    def _load_from_db(self):
        """Load all agents from database"""
        self.agents = []
        self.agent_dict = {}
        
        conn = get_db()
        cur = conn.cursor()
        cur.execute("""
            SELECT agent_name, agent_type, specialization, xp_points, token_balance,
                   trust_weight, total_votes, correct_votes, vote_accuracy,
                   knowledge_shared_count
            FROM core_agents ORDER BY agent_name
        """)
        rows = cur.fetchall()
        cur.close()
        conn.close()
        
        for row in rows:
            name = row['agent_name']
            atype = row['agent_type']
            spec = row['specialization']
            
            # Create specialized agents
            if name == 'Agent_A':
                agent = AgentATrend()
            elif name == 'Agent_B':
                agent = AgentBMeanReversion()
            elif name == 'Agent_C':
                agent = AgentCMomentum()
            elif name == 'Agent_D':
                agent = AgentDVolatility()
            elif name == 'Agent_E':
                agent = AgentEMicrostructure()
            elif name == 'Agent_F':
                agent = AgentFCandlestick()
            elif name == 'Agent_G':
                agent = AgentGWhale()
            elif name == 'Agent_H':
                agent = AgentHFibonacci()
            elif name == 'Agent_I':
                agent = SentimentMaster()
            elif name == 'Agent_J':
                agent = VolumeMaster()
            elif name == 'Agent_K':
                agent = IchimokuExpert()
            elif name == 'Agent_L':
                agent = EconomicCalendarMaster()
            elif name == 'Agent_M':
                agent = MarketProfileMaster()
            elif name == 'Agent_N':
                agent = IntermarketMaster()
            elif name == 'Agent_Q':
                agent =  DarkPoolWhaleAgent()
            elif name == 'Agent_R':
                agent = SupplyDemandExpert()
            elif name == 'Agent_S':
                agent = SkepticAgent()
            elif name == 'Agent_T':
                agent = ConfluenceAgent()
            elif name == 'Agent_U':
                agent = LiquidityAgent()
            elif name == 'Agent_V':
                agent =  NeutralPsychologyAgent()
            elif name == 'Agent_P':
                agent = WhisperAnalyst()
            else:
                agent = BaseAgent(name, atype, spec)
            
            agent.xp_points = row['xp_points']
            agent.token_balance = row['token_balance']
            agent.trust_weight = row['trust_weight']
            agent.total_votes = row['total_votes']
            agent.correct_votes = row['correct_votes']
            agent.vote_accuracy = row['vote_accuracy']
            agent.knowledge_shared_count = row['knowledge_shared_count']
            
            self.agents.append(agent)
            self.agent_dict[name] = agent
            print(f"✅ Loaded agent: {name}")
        
        print(f"📊 Total agents loaded: {len(self.agents)}")
    def learn_from_deepseek(self, agent_name: str, concept: str) -> Dict:
        """Agent learns a concept from DeepSeek"""
        agent = self.get_agent(agent_name)
        if not agent:
            return {'success': False, 'error': 'Agent not found'}
        
        if not self.deepseek.enabled:
            return {'success': False, 'error': 'DeepSeek not configured'}
        
        # Get lesson from DeepSeek
        lesson = self.deepseek.learn_trading_concept(agent_name, concept, agent.agent_type)
        
        if lesson:
            # Award XP for learning
            agent.xp_points += 30
            agent.knowledge_shared_count += 1
            self.save_to_db()
            
            return {
                'success': True,
                'concept': concept,
                'lesson': lesson,
                'xp_gained': 30,
                'agent': agent_name
            }
        
        return {'success': False, 'error': 'Failed to get lesson from DeepSeek'}
    # ========== GETTER METHODS ==========
    
    def get_all_agents(self):
        """Return all agents"""
        return self.agents
    
    def get_agents(self):
        """Alias for get_all_agents"""
        return self.agents
    
    def get_all(self):
        """Alias for get_all_agents"""
        return self.agents
    
    def get_agent(self, name):
        """Get agent by name"""
        return self.agent_dict.get(name)
    
    def get_by_name(self, name):
        """Alias for get_agent"""
        return self.get_agent(name)
    
    def get_all_status(self):
        """Get status of all agents"""
        return [agent.get_status() for agent in self.agents]
    
    # ========== VOTING METHODS ==========
    def get_price_for_agent(self, agent_name: str, symbol: str) -> float:
        """Helper method for agents to get prices"""
        return get_price_with_fallback(symbol, agent_name)
    
    def get_prices_for_agents(self, agent_name: str, symbols: list) -> dict:
        """Get multiple prices for an agent"""
        return get_multiple_prices(symbols, agent_name)
    def collect_votes(self, signal_data, market_features):
        """Collect votes from all agents"""
        votes = {}
        for agent in self.agents:
            votes[agent.name] = agent.vote(signal_data, market_features)
        return votes
    
    # ========== REWARD METHODS ==========
    
    def update_agent_rewards(self, agent_name, was_correct, xp_gained=0, xp_lost=0, asset=None, timeframe=None):
        """Update agent based on trade outcome"""
        agent = self.get_agent(agent_name)
        if agent:
            return agent.update_from_reward(was_correct, xp_gained, xp_lost, asset, timeframe)
        return None
    
    # ========== SAVE METHODS ==========
    def save_to_db(self):
        """Save all agents to database"""
        conn = get_db()
        cur = conn.cursor()
        for agent in self.agents:
            cur.execute("""
                UPDATE core_agents 
                SET xp_points = %s, token_balance = %s, trust_weight = %s,
                    total_votes = %s, correct_votes = %s, vote_accuracy = %s,
                    knowledge_shared_count = %s
                WHERE agent_name = %s
            """, (
                agent.xp_points, agent.token_balance, agent.trust_weight,
                agent.total_votes, agent.correct_votes, agent.vote_accuracy,
                agent.knowledge_shared_count, agent.name
            ))
    def _assign_timeframes(self):
        """Assign granularity to each agent based on role"""
        for name, agent in self.agents.items():
            if name in AGENT_GRANULARITY:
                agent.timeframe = AGENT_GRANULARITY[name]['timeframe']
                agent.role = AGENT_GRANULARITY[name]['role']
            else:
                # Fallback for unknown agents
                agent.timeframe = Granularity.M15
                agent.role = "General Analyst"
    
    def run_trading_cycle(self, pair="EURUSD"):
        """Run complete cycle fetching correct granularity for each agent"""
        from backend.utils.indicator_cache import indicator_cache
        # from oanda_bridge import get_oanda_bridge
        
        # bridge = get_oanda_bridge()
        from mt4_price_provider import get_mt4_prices
        mt4 = get_mt4_prices()
        indicator_cache.start_new_cycle()
        
        # Get unique timeframes needed for this cycle
        timeframes = get_timeframes_for_cycle()
        
        # Pre-fetch indicators for ALL timeframes at once
        indicators_by_timeframe = {}
        for tf in timeframes:
            print(f"📡 Fetching {tf.value} data for {pair}...")
            indicators = indicator_cache.get_indicators_for_pair(
                pair, tf.value, bridge
            )
            indicators_by_timeframe[tf] = indicators
        
        # Now each agent gets its specific timeframe indicators
        results = {}
        for name, agent in self.agents.items():
            agent_tf = getattr(agent, 'timeframe', Granularity.M15)
            
            # Get indicators for this agent's timeframe
            if agent_tf in indicators_by_timeframe:
                agent.set_indicators(indicators_by_timeframe[agent_tf])
            else:
                # Fallback for REAL_TIME or ALL agents
                agent.set_indicators(None)
            
            # Let agent analyze
            results[name] = agent.analyze_signal()
        
        return results
        conn.commit()
        cur.close()
        conn.close()
        print("💾 Agents saved to database")
        
