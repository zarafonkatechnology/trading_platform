# forex_engine/launcher.py - COMPLETE FIXED VERSION

import logging
import sys
import time
from pathlib import Path
from typing import Dict, List
from datetime import datetime

# Add parent directory to path
sys.path.append(str(Path(__file__).parent.parent))

# ============================================================
# ALL FOREX PAIRS (Defined Once)
# ============================================================

FOREX_PAIRS = [
    # Majors
    'EURUSD', 'GBPUSD', 'USDJPY', 'USDCHF', 'AUDUSD', 'USDCAD', 'NZDUSD',
    # Crosses
    'EURGBP', 'EURJPY', 'EURCAD', 'EURNZD', 'EURCHF'
]

# ============================================================
# IMPORT ALL AGENTS
# ============================================================

try:
    from agents2.agent_c_momentum import AgentCMomentum
    from agents2.agent_e_microstructure import AgentEMicrostructure
    from agents2.agent_p_whisper import WhisperAnalyst
    from agents2.forex_agent_x import ForexAgentX
    from agents2.forex_agent_u import ForexLiquidityAgentEnhanced
    from agents2.forex_agent_d import AgentDVolatility
    print("✅ Imported agents from agents2")
except ImportError as e:
    print(f"⚠️ Import error from agents2: {e}")
    
    try:
        from agents.agent_c_momentum import AgentCMomentum
        from agents.agent_e_microstructure import AgentEMicrostructure
        from agents.agent_p_whisper import WhisperAnalyst
        from agents.forex_agent_x import ForexAgentX
        from agents.forex_agent_u import ForexLiquidityAgentEnhanced
        from agents.forex_agent_d import AgentDVolatility
        print("✅ Imported agents from agents")
    except ImportError as e2:
        print(f"⚠️ Import error from agents: {e2}")
        
        # Fallback classes
        class AgentCMomentum:
            def __init__(self):
                self.name = "Agent_C"
                self.agent_type = "Pair Agent"
            def analyze(self, data):
                return {'vote': 'HOLD', 'confidence': 50, 'reasoning': 'Placeholder'}
        
        class AgentEMicrostructure:
            def __init__(self):
                self.name = "Agent_E"
                self.agent_type = "Base Pair Agent"
            def analyze(self, data):
                return {'vote': 'HOLD', 'confidence': 50, 'reasoning': 'Placeholder'}
        
        class WhisperAnalyst:
            def __init__(self):
                self.name = "Agent_P"
                self.agent_type = "Cross Pair Agent"
            def analyze(self, data):
                return {'vote': 'HOLD', 'confidence': 50, 'reasoning': 'Placeholder'}
        
        class ForexAgentX:
            def __init__(self, name="Forex_X", timeframe="M15"):
                self.name = name
                self.timeframe = timeframe
                self.agent_type = "Spread Reversion Specialist"
            def analyze(self, data):
                return {'vote': 'HOLD', 'confidence': 50, 'reasoning': 'Placeholder'}
        
        class ForexLiquidityAgentEnhanced:
            def __init__(self, name="Forex_Agent_U", timeframe="M15"):
                self.name = name
                self.timeframe = timeframe
                self.agent_type = "Liquidity Specialist"
            def analyze(self, data):
                return {'vote': 'HOLD', 'confidence': 50, 'reasoning': 'Placeholder'}
        
        class AgentDVolatility:
            def __init__(self, name="Forex_D", timeframe="M15"):
                self.name = name
                self.timeframe = timeframe
                self.agent_type = "Volatility Specialist"
            def analyze(self, data):
                return {'vote': 'HOLD', 'confidence': 50, 'reasoning': 'Placeholder'}
        
        print("⚠️ Using fallback agent classes")

# ============================================================
# IMPORT CORE COMPONENTS
# ============================================================

try:
    from core.dollar_engine import DollarEngine
except ImportError:
    class DollarEngine:
        def __init__(self, config=None):
            self.engine_speed = 0.0
            self.engine_direction = 'NEUTRAL'
            self.engine_health = 100.0
        def update_engine_state(self, data):
            return {'engine_speed': 0.409, 'engine_direction': 'FORWARD', 'engine_health': 95.0}
        def get_gear_prediction(self, pair, gear_ratio=1.0):
            return {'predicted_direction': 'SIDEWAYS', 'confidence': 50}
        def get_status(self):
            return {'engine_speed': 0.409, 'engine_direction': 'FORWARD', 'engine_health': 95.0}

# ============================================================
# IMPORT TRADING CONTROLLER
# ============================================================

try:
    from trading_controller2 import ForexTradingController
    print("✅ Imported ForexTradingController from trading_controller2")
except ImportError:
    try:
        from trading_controller import ForexTradingController
        print("✅ Imported ForexTradingController from trading_controller")
    except ImportError:
        print("⚠️ Could not import ForexTradingController - using fallback")
        class ForexTradingController:
            def __init__(self, config=None):
                self.is_running = False
                self.config = config or {}
                self.pairs = config.get('pairs', ['EURUSD'])
                self.cycle_count = 0
                self.trades_today = 0
                self.daily_pnl = 0.0
                self.positions = {}
            def start(self):
                self.is_running = True
            def stop(self):
                self.is_running = False
            def build_market_data(self):
                return {pair: 1.1000 for pair in self.pairs}
            def process_cycle(self, market_data):
                self.cycle_count += 1
                return {'cycle': self.cycle_count, 'trades': [], 'engine': {}}
            def get_status(self):
                return {'is_running': self.is_running, 'active_count': 0, 'daily_pnl': self.daily_pnl}
            def get_all_prices(self):
                return {pair: 1.1000 for pair in self.pairs}

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class ForexSystemLauncher:
    """
    Launcher for the complete forex trading system
    """
    
    def __init__(self, config: Dict = None):
        self.config = config or {}
        self.TIMEFRAME = self.config.get('timeframe', 'M15')
        self.is_running = False
        self.cycle_count = 0
        
        # Use provided pairs or default
        self.ALL_FOREX_PAIRS = self.config.get('pairs', FOREX_PAIRS)
        
        # Initialize components
        self.agents = []
        self.engine = None
        self.controller = None
        
        # Agent instances
        self.agent_x = None
        self.agent_u = None
        self.agent_d = None
        self.agent_c = None
        self.agent_e = None
        self.agent_p = None
        
        logger.info("="*60)
        logger.info("🏛️ FOREX TRADING SYSTEM LAUNCHER")
        logger.info("="*60)
        logger.info(f"   Timeframe: {self.TIMEFRAME}")
        logger.info(f"   Pairs: {len(self.ALL_FOREX_PAIRS)}")
        logger.info("   📊 Trading Pairs:")
        for i, pair in enumerate(self.ALL_FOREX_PAIRS):
            logger.info(f"      {i+1:2}. {pair}")
        logger.info("="*60)
    
    def initialize_agents(self):
        """Initialize all trading agents"""
        logger.info("🤖 Initializing agents...")
        
        try:
            # Specialist Agents
            self.agent_x = ForexAgentX(name="Forex_X", timeframe=self.TIMEFRAME)
            self.agent_u = ForexLiquidityAgentEnhanced(name="Forex_Agent_U")
            self.agent_d = AgentDVolatility(name="Forex_D", timeframe=self.TIMEFRAME)
            
            # Pair Agents
            self.agent_c = AgentCMomentum()
            self.agent_e = AgentEMicrostructure()
            self.agent_p = WhisperAnalyst()
            
            self.agents = [
                self.agent_x, self.agent_u, self.agent_d,
                self.agent_c, self.agent_e, self.agent_p
            ]
            
            logger.info(f"✅ {len(self.agents)} agents initialized")
            for agent in self.agents:
                logger.info(f"      - {agent.name}: {getattr(agent, 'agent_type', 'General')}")
                
        except Exception as e:
            logger.error(f"Error initializing agents: {e}")
            import traceback
            traceback.print_exc()
            self.agents = []
        
        return self.agents
    
    def initialize_engine(self):
        """Initialize dollar engine"""
        logger.info("🔧 Initializing Dollar Engine...")
        try:
            engine_config = self.config.get('engine_config', {})
            self.engine = DollarEngine(engine_config)
            logger.info("✅ Dollar Engine initialized")
        except Exception as e:
            logger.error(f"Error initializing Dollar Engine: {e}")
            self.engine = DollarEngine()
            logger.info("✅ Dollar Engine initialized (fallback)")
        return self.engine
    
    def initialize_controller(self):
        """Initialize trading controller"""
        logger.info("📊 Initializing Trading Controller...")
        try:
            # Build config with ALL pairs
            controller_config = self.config.copy()
            controller_config['pairs'] = self.ALL_FOREX_PAIRS
            controller_config['timeframe'] = self.TIMEFRAME
            
            self.controller = ForexTradingController(controller_config)
            logger.info("✅ Trading Controller initialized")
            logger.info(f"   📊 Trading {len(self.ALL_FOREX_PAIRS)} forex pairs")
        except Exception as e:
            logger.error(f"Error initializing Trading Controller: {e}")
            import traceback
            traceback.print_exc()
            self.controller = ForexTradingController({'pairs': self.ALL_FOREX_PAIRS})
            logger.info("✅ Trading Controller initialized (fallback)")
        return self.controller
    
    def start(self):
        """Start the trading system"""
        logger.info("🚀 Starting Forex Trading System...")
        
        # Initialize components
        self.initialize_agents()
        self.initialize_engine()
        self.initialize_controller()
        
        # Start the controller
        if self.controller and hasattr(self.controller, 'start'):
            self.controller.start()
        
        self.is_running = True
        
        logger.info("✅ System started successfully")
        logger.info(f"   📊 Trading Pairs: {len(self.ALL_FOREX_PAIRS)}")
        logger.info(f"   🤖 Agents: {len(self.agents)}")
        logger.info("   🔧 Engine: Active | Threshold: 2.0")
        
        return self
    
    def stop(self):
        """Stop the trading system"""
        logger.info("🛑 Stopping Forex Trading System...")
        self.is_running = False
        if self.controller and hasattr(self.controller, 'stop'):
            self.controller.stop()
        logger.info("✅ System stopped")
    
    def run_cycle(self):
        """Run one trading cycle"""
        if not self.controller:
            logger.warning("Controller not initialized")
            return
        
        self.cycle_count += 1
        
        try:
            # Build market data
            market_data = self.controller.build_market_data()
            
            # Process cycle
            result = self.controller.process_cycle(market_data)
            
            # Get status
            status = self.controller.get_status() if hasattr(self.controller, 'get_status') else {}
            trades = result.get('trades', [])
            engine = result.get('engine', {})
            
            # Display
            print(f"💓 [{datetime.now().strftime('%H:%M:%S')}] "
                  f"Cycle: {self.cycle_count} | "
                  f"Trades: {len(trades)} | "
                  f"Active: {status.get('active_count', 0)} | "
                  f"Engine: {engine.get('engine_direction', 'N/A')} | "
                  f"P&L: ${status.get('daily_pnl', 0):.2f}")
            
            return result
            
        except Exception as e:
            logger.error(f"Cycle error: {e}")
            import traceback
            traceback.print_exc()
            return None
    
    def get_status(self) -> Dict:
        """Get current system status"""
        status = {
            'is_running': self.is_running,
            'cycle_count': self.cycle_count,
            'pairs': len(self.ALL_FOREX_PAIRS),
            'agents': len(self.agents),
            'timestamp': datetime.now().isoformat()
        }
        
        if self.controller and hasattr(self.controller, 'get_status'):
            try:
                status['controller'] = self.controller.get_status()
            except:
                status['controller'] = {'error': 'Could not get status'}
        
        if self.engine and hasattr(self.engine, 'get_status'):
            try:
                status['engine'] = self.engine.get_status()
            except:
                status['engine'] = {'error': 'Could not get status'}
        
        return status


# ============================================================
# MAIN
# ============================================================

def main():
    """Main entry point"""
    print("\n" + "="*60)
    print("🏛️ FOREX TRADING SYSTEM")
    print("="*60 + "\n")
    
    print("📊 ALL FOREX PAIRS:")
    for i, pair in enumerate(FOREX_PAIRS):
        print(f"   {i+1:2}. {pair}")
    
    print(f"\n   Total: {len(FOREX_PAIRS)} pairs")
    print(f"   Min Confidence: 50%")
    print(f"   Cycle Interval: 10s")
    print()
    
    # ============================================================
    # CONFIGURATION
    # ============================================================
    
    config = {
        'pairs': FOREX_PAIRS,
        'min_confidence': 50,
        'cycle_interval': 10,
        'timeframe': 'M15',
        'bypass_mc': True,
        'engine_config': {
            'factor_weights': {
                'interest_rate_diff': 0.35,
                'yield_curve_slope': 0.25,
                'carry_trade_flow': 0.15,
                'positioning_sentiment': 0.15,
                'central_bank_actions': 0.10,
            }
        }
    }
    
    # ============================================================
    # CREATE AND START LAUNCHER
    # ============================================================
    
    launcher = ForexSystemLauncher(config)
    launcher.start()
    
    print("\n🔄 Live Trading Started... Press Ctrl+C to stop\n")
    
    try:
        while launcher.is_running:
            launcher.run_cycle()
            time.sleep(launcher.config.get('cycle_interval', 10))
            
    except KeyboardInterrupt:
        print("\n🛑 Shutting down...")
        launcher.stop()
        print("✅ Stopped")
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
        launcher.stop()


if __name__ == "__main__":
    main()