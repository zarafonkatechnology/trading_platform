"""
Base Agent Class - Hybrid Approach with Asset and Timeframe Awareness
"""

import logging
from abc import ABC, abstractmethod
from datetime import datetime

# Add at the top with other imports
from backend.utils.market_hours import MarketHours

# Add this method to the BaseAgent class
def check_market_hours(self):
    """Check if markets are open before trading"""
    market_status = MarketHours.should_trade()
    
    if not market_status['can_trade']:
        self.last_error = market_status['reason']
        return {
            'can_trade': False,
            'vote': 'HOLD',
            'confidence': 100,
            'reasoning': market_status['message'],
            'market_closed': True
        }
    
    return {
        'can_trade': True,
        'market_closed': False,
        'session': market_status.get('session', 'UNKNOWN')
    }

# Also modify the analyze method to check market hours first
def analyze_safe(self, signal_data):
    """Safe analysis that checks market hours first"""
    market_check = self.check_market_hours()
    
    if not market_check['can_trade']:
        return {
            'agent': self.name,
            'type': self.agent_type,
            'vote': 'HOLD',
            'confidence': 100,
            'reasoning': market_check['reasoning'],
            'market_closed': True,
            'timestamp': datetime.now().isoformat()
        }
    
    # If market is open, proceed with normal analysis
    return self.analyze(signal_data)
logger = logging.getLogger(__name__)

# Agent level configuration
AGENT_LEVELS = {
    1: ('Novice', 0, '🔰'),
    2: ('Apprentice', 100, '📘'),
    3: ('Scholar', 300, '📚'),
    4: ('Expert', 600, '⭐'),
    5: ('Master', 1000, '🏆'),
    6: ('Grandmaster', 1500, '👑'),
    7: ('Legend', 2100, '🌟'),
    8: ('Mythic', 2800, '💫'),
    9: ('Transcendent', 3600, '✨'),
    10: ('Omniscient', 5000, '🔮'),
}

def get_agent_level(xp):
    """Get agent level based on XP"""
    for level, (name, required, icon) in AGENT_LEVELS.items():
        if xp < required:
            if level == 1:
                return 1, 'Novice', '🔰'
            return level - 1, AGENT_LEVELS[level - 1][0], AGENT_LEVELS[level - 1][2]
    return 10, 'Omniscient', '🔮'

class BaseAgent(ABC):
    
    """Base class for all trading agents - supports multi-asset, multi-timeframe"""
    def __init__(self, name):
        self.name = name
        self.price_helper = get_price_with_fallback
    
    def get_price(self, symbol: str) -> float:
        """Get price using the central helper"""
        return get_price_with_fallback(symbol, self.name)
    
    def get_price_details(self, symbol: str) -> dict:
        """Get price details"""
        return get_price_with_details(symbol, self.name)
    def __init__(self, name, agent_type, specialization):
        self.name = name
        self.agent_type = agent_type
        self.specialization = specialization
        self.xp_points = 0
        self.token_balance = 1000
        self.trust_weight = 0.2
        self.total_votes = 0
        self.correct_votes = 0
        self.vote_accuracy = 0
        self.knowledge_shared_count = 0
        self.achievements_count = 0
        
        # Track performance by asset and timeframe
        self.performance_by_asset = {}
        self.performance_by_timeframe = {}
    
    def predict(self, signal_data, market_features):
        """
        Predict market direction.
        Override in specialized agents.
        Returns: (action, confidence)
        """
        # Default implementation - can be overridden
        confidence = signal_data.get('confidence_percent', 70)
        timeframe = market_features.get('timeframe', 15)
        
        # Adjust threshold based on timeframe
        if timeframe <= 5:
            threshold = 70
        elif timeframe <= 15:
            threshold = 75
        elif timeframe <= 60:
            threshold = 80
        else:
            threshold = 85
        
        if confidence > threshold:
            return 'BUY', confidence
        elif confidence < threshold - 20:
            return 'SELL', confidence - 10
        return 'HOLD', 50
    
    def vote(self, signal_data, market_features):
        """
        Cast a vote with asset and timeframe context
        """
        try:
            action, confidence = self.predict(signal_data, market_features)
            
            # Adjust confidence based on agent's experience
            experience_factor = min(1.5, 1 + (self.xp_points / 10000))
            adjusted_confidence = min(100, confidence * experience_factor)
            
            # Store context
            asset = signal_data.get('asset_type', 'UNKNOWN')
            timeframe = market_features.get('timeframe', 15)
            
            self.total_votes += 1
            
            # Update performance tracking
            self._update_performance_tracking(asset, timeframe, action)
            
            logger.info(f"{self.name} voted {action} on {asset} ({timeframe}min) with {adjusted_confidence:.1f}% confidence")
            
            return {
                'agent_name': self.name,
                'vote': action,
                'confidence': round(adjusted_confidence, 2),
                'asset': asset,
                'timeframe': timeframe,
                'timestamp': datetime.now().isoformat()
            }
        except Exception as e:
            logger.error(f"{self.name} vote error: {e}")
            return {
                'agent_name': self.name,
                'vote': 'HOLD',
                'confidence': 50,
                'asset': signal_data.get('asset_type', 'UNKNOWN'),
                'timeframe': market_features.get('timeframe', 15),
                'timestamp': datetime.now().isoformat()
            }
    
    def _update_performance_tracking(self, asset, timeframe, action):
        """Track agent performance by asset and timeframe"""
        # By asset
        if asset not in self.performance_by_asset:
            self.performance_by_asset[asset] = {'total': 0, 'correct': 0}
        self.performance_by_asset[asset]['total'] += 1
        
        # By timeframe
        if timeframe not in self.performance_by_timeframe:
            self.performance_by_timeframe[timeframe] = {'total': 0, 'correct': 0}
        self.performance_by_timeframe[timeframe]['total'] += 1
    
    def update_from_reward(self, was_correct, xp_gained=0, xp_lost=0, asset=None, timeframe=None):
        """
        Update agent based on reward/penalty with asset and timeframe context
        """
        self.total_votes += 1
        
        if was_correct:
            self.correct_votes += 1
            self.xp_points += xp_gained
            self.token_balance += xp_gained // 2
            
            # Update performance tracking for correct votes
            if asset and asset in self.performance_by_asset:
                self.performance_by_asset[asset]['correct'] += 1
            if timeframe and timeframe in self.performance_by_timeframe:
                self.performance_by_timeframe[timeframe]['correct'] += 1
        else:
            self.xp_points = max(0, self.xp_points - xp_lost)
        
        # Recalculate accuracy
        if self.total_votes > 0:
            self.vote_accuracy = (self.correct_votes / self.total_votes) * 100
            self.trust_weight = 0.1 + (self.vote_accuracy / 100) * 0.3
            self.trust_weight = min(0.4, max(0.05, self.trust_weight))
        
        logger.info(f"{self.name} updated: XP={self.xp_points}, Accuracy={self.vote_accuracy:.1f}%, Weight={self.trust_weight:.3f}")
        
        return {
            'xp_points': self.xp_points,
            'token_balance': self.token_balance,
            'vote_accuracy': self.vote_accuracy,
            'trust_weight': self.trust_weight
        }
    
    def get_performance_by_asset(self):
        """Get agent performance broken down by asset"""
        result = {}
        for asset, data in self.performance_by_asset.items():
            accuracy = (data['correct'] / data['total'] * 100) if data['total'] > 0 else 0
            result[asset] = {
                'total_votes': data['total'],
                'correct_votes': data['correct'],
                'accuracy': round(accuracy, 1)
            }
        return result
    
    def get_performance_by_timeframe(self):
        """Get agent performance broken down by timeframe"""
        result = {}
        for tf, data in self.performance_by_timeframe.items():
            accuracy = (data['correct'] / data['total'] * 100) if data['total'] > 0 else 0
            result[tf] = {
                'total_votes': data['total'],
                'correct_votes': data['correct'],
                'accuracy': round(accuracy, 1)
            }
        return result
    
    # Import level function (will be defined in app_code.py, so use lazy import)
    def _get_level(xp):
       try:
        from app_code import get_agent_level
        return get_agent_level(xp)
       except:
        return (1, 'Novice', '🔰')
    def get_status(self):
      level_num, level_name, level_icon = get_agent_level(self.xp_points)
      return {
        'name': self.name,
        'type': self.agent_type,
        'specialization': self.specialization,
        'xp_points': self.xp_points,
        'token_balance': self.token_balance,
        'trust_weight': round(self.trust_weight, 4),
        'total_votes': self.total_votes,
        'correct_votes': self.correct_votes,
        'vote_accuracy': round(self.vote_accuracy, 2),
        'knowledge_shared_count': self.knowledge_shared_count,
        'achievements_count': self.achievements_count,
        'level': level_num,
        'level_name': level_name,
        'level_icon': level_icon,
        'is_active': True
    }
    def set_indicators(self, indicators):
        """Receive precomputed indicators from cache"""
        self.indicators = indicators
    
    def get_indicator(self, name, default=None):
        """Get a specific indicator value"""
        if self.indicators:
            return self.indicators.get(name, default)
        return default
    
    def analyze_signal(self):
        """Analyze using precomputed indicators - NO recalc needed"""
        price = get_price_with_fallback(symbol, self.name)
    
        if price <= 0:
            return {'decision': 'HOLD', 'reason': 'No price available'}
        # Child classes use self.get_indicator() instead of calculating
        raise NotImplementedError
