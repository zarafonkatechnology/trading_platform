"""
Multi-Timeframe Strategy Framework
Supports: 5min (Scalping), 15min (Day Trading), 1hour (Swing), Daily (Position)
"""

from typing import Dict, Tuple, Optional
import logging

logger = logging.getLogger(__name__)

class StrategyFramework:
    """
    Supports 5-min, 15-min, 1-hour, and custom timeframes.
    Each strategy has its own voting rules and risk parameters.
    """
    
    STRATEGIES = {
        5: {   # 5-minute (Scalping)
            'name': 'SCALPING',
            'description': 'Very short-term trades, high frequency',
            'min_confidence': 70,
            'required_consensus': 60,      # 60% agreement needed
            'max_slippage_bps': 10,
            'position_size': 'small',
            'stoploss_multiplier': 1.0,
            'takeprofit_multiplier': 1.5,
            'max_holding_periods': 6,      # 30 minutes max
            'max_daily_trades': 20,
            'risk_per_trade': 0.5          # 0.5% risk per trade
        },
        15: {  # 15-minute (Day Trading)
            'name': 'DAY_TRADE',
            'description': 'Intraday trades, medium frequency',
            'min_confidence': 75,
            'required_consensus': 60,
            'max_slippage_bps': 15,
            'position_size': 'medium',
            'stoploss_multiplier': 1.5,
            'takeprofit_multiplier': 2.0,
            'max_holding_periods': 12,     # 3 hours max
            'max_daily_trades': 10,
            'risk_per_trade': 1.0
        },
        60: {  # 1-hour (Swing Trading)
            'name': 'SWING',
            'description': 'Hold for hours to days',
            'min_confidence': 80,
            'required_consensus': 66,      # 2/3 agreement
            'max_slippage_bps': 20,
            'position_size': 'large',
            'stoploss_multiplier': 2.0,
            'takeprofit_multiplier': 3.0,
            'max_holding_periods': 24,     # 1 day max
            'max_daily_trades': 5,
            'risk_per_trade': 2.0
        },
        1440: { # Daily (Position Trading)
            'name': 'POSITION',
            'description': 'Long-term position trading',
            'min_confidence': 85,
            'required_consensus': 75,
            'max_slippage_bps': 30,
            'position_size': 'full',
            'stoploss_multiplier': 3.0,
            'takeprofit_multiplier': 5.0,
            'max_holding_periods': 30,     # 1 month max
            'max_daily_trades': 2,
            'risk_per_trade': 3.0
        }
    }
    
    def __init__(self, db_connection=None):
        self.db = db_connection
        self._init_db()
    
    def _init_db(self):
        """Initialize strategy table in database"""
        if self.db:
            try:
                cursor = self.db.cursor()
                for minutes, strategy in self.STRATEGIES.items():
                    cursor.execute("""
                        INSERT INTO strategies (strategy_name, timeframe_minutes, min_confidence, 
                            required_consensus, max_slippage_bps, position_size, 
                            stoploss_multiplier, takeprofit_multiplier, max_holding_periods)
                        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
                        ON CONFLICT (timeframe_minutes) DO UPDATE SET
                            min_confidence = EXCLUDED.min_confidence,
                            required_consensus = EXCLUDED.required_consensus
                    """, (
                        strategy['name'], minutes, strategy['min_confidence'],
                        strategy['required_consensus'], strategy['max_slippage_bps'],
                        strategy['position_size'], strategy['stoploss_multiplier'],
                        strategy['takeprofit_multiplier'], strategy['max_holding_periods']
                    ))
                self.db.commit()
            except Exception as e:
                logger.warning(f"Could not init strategy table: {e}")
    
    def get_strategy(self, timeframe_minutes: int) -> Dict:
        """Get strategy parameters for given timeframe"""
        # Find closest matching timeframe
        available = sorted(self.STRATEGIES.keys())
        closest = min(available, key=lambda x: abs(x - timeframe_minutes))
        
        strategy = self.STRATEGIES[closest].copy()
        strategy['timeframe_minutes'] = closest
        strategy['requested_timeframe'] = timeframe_minutes
        
        return strategy
    
    def calculate_position_size(self, strategy: Dict, confidence: float, 
                                 volatility: float, account_balance: float = 100000) -> int:
        """
        Calculate position size based on strategy and market conditions
        
        Formula: base_size * confidence_factor * volatility_factor * balance_factor
        """
        base_sizes = {
            'small': 1000,
            'medium': 5000,
            'large': 10000,
            'full': 25000
        }
        
        base = base_sizes.get(strategy['position_size'], 1000)
        
        # Adjust for confidence (70% confidence = 70% of base)
        confidence_factor = confidence / 100
        
        # Adjust for volatility (higher volatility = smaller position)
        volatility_factor = max(0.3, min(1.5, 1.0 - (volatility / 100)))
        
        # Adjust for account balance (max 2x for larger accounts)
        balance_factor = min(2.0, account_balance / 50000)
        
        quantity = int(base * confidence_factor * volatility_factor * balance_factor)
        
        return max(100, quantity)  # Minimum 100 units
    
    def calculate_stoploss(self, strategy: Dict, entry_price: float, 
                           atr: Optional[float] = None) -> float:
        """Calculate stop loss based on strategy"""
        if atr:
            # Use ATR-based stop
            stop_distance = atr * strategy['stoploss_multiplier']
            return entry_price - stop_distance
        else:
            # Use percentage-based stop
            stop_percent = 0.01 * strategy['stoploss_multiplier']
            return entry_price * (1 - stop_percent)
    
    def calculate_takeprofit(self, strategy: Dict, entry_price: float,
                              stoploss: float) -> float:
        """Calculate take profit based on risk-reward ratio"""
        risk = abs(entry_price - stoploss)
        reward = risk * strategy['takeprofit_multiplier']
        return entry_price + reward
    
    def get_required_votes(self, strategy: Dict, total_agents: int) -> Dict:
        """Calculate required votes for consensus"""
        required_consensus_percent = strategy['required_consensus']
        
        required_votes = {
            'buy': 0,
            'sell': 0,
            'total_needed': int(total_agents * required_consensus_percent / 100)
        }
        
        return required_votes
    
    def get_all_strategies(self) -> Dict:
        """Get all available strategies"""
        return self.STRATEGIES
    
    def get_strategy_by_name(self, name: str) -> Optional[Dict]:
        """Get strategy by name"""
        for minutes, strategy in self.STRATEGIES.items():
            if strategy['name'] == name.upper():
                return strategy
        return None
