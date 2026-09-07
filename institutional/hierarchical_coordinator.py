# ============================================================
# hierarchical_coordinator.py - Conductor Model
# ============================================================
# Event-driven, specialist-based coordination
# ============================================================

from typing import Dict, List, Optional
from datetime import datetime
import logging

logger = logging.getLogger(__name__)


class HierarchicalCoordinator:
    """
    Hierarchical Coordinator (Conductor Model).
    
    Features:
    - Specialized authority for each agent
    - Event-driven activation
    - Fast execution
    - No democratic voting bottleneck
    """
    
    def __init__(self):
        # ===== HIERARCHY LEVELS =====
        self.levels = {
            'CRITICAL': 1,      # Market crash, liquidity event
            'EXECUTION': 2,     # Ready to trade
            'ANALYSIS': 3,      # Normal analysis
            'MONITORING': 4     # Background monitoring
        }
        
        self.current_level = 'MONITORING'
        self.current_mode = 'NORMAL'
        
        # ===== SPECIALISTS =====
        self.specialists = {
            'LIQUIDITY': {
                'active': False,
                'weight': 0,
                'last_activation': None
            },
            'VOLATILITY': {
                'active': False,
                'weight': 0,
                'last_activation': None
            },
            'TREND': {
                'active': False,
                'weight': 0,
                'last_activation': None
            },
            'MEAN_REVERSION': {
                'active': False,
                'weight': 0,
                'last_activation': None
            },
            'SENTIMENT': {
                'active': False,
                'weight': 0,
                'last_activation': None
            }
        }
        
        # ===== EVENT TRACKING =====
        self.event_log = []
        self.execution_queue = []
        
        logger.info("✅ HierarchicalCoordinator initialized")
    
    def update_market_state(self, market_data: Dict):
        """
        Update market state and activate/deactivate specialists.
        """
        liquidity_score = market_data.get('liquidity_score', 0.7)
        volatility = market_data.get('volatility', 0.02)
        trend_strength = market_data.get('trend_strength', 0.3)
        mean_reversion_score = market_data.get('mean_reversion_score', 0.5)
        sentiment = market_data.get('sentiment', 0)
        
        # ===== LIQUIDITY EVENT =====
        if liquidity_score < 0.3:
            self._activate_specialist('LIQUIDITY', 0.5)
            self.current_level = 'CRITICAL'
            self.current_mode = 'LIQUIDITY_CRISIS'
            logger.warning("🔴 LIQUIDITY CRISIS - Critical mode")
        
        # ===== VOLATILITY SPIKE =====
        elif volatility > 0.05:
            self._activate_specialist('VOLATILITY', 0.4)
            self._deactivate_specialist('MEAN_REVERSION')
            self.current_level = 'EXECUTION'
            self.current_mode = 'VOLATILE'
            logger.info("⚡ Volatility spike - Volatility specialist activated")
        
        # ===== STRONG TREND =====
        elif trend_strength > 0.7:
            self._activate_specialist('TREND', 0.4)
            self._deactivate_specialist('MEAN_REVERSION')
            self.current_level = 'EXECUTION'
            self.current_mode = 'TRENDING'
            direction = 'UP' if market_data.get('price_direction', 0) > 0 else 'DOWN'
            logger.info(f"📈 Strong {direction} trend - Trend specialist activated")
        
        # ===== MEAN REVERSION (Ranging Market) =====
        elif mean_reversion_score > 0.6 and volatility < 0.03:
            self._activate_specialist('MEAN_REVERSION', 0.4)
            self._deactivate_specialist('TREND')
            self.current_level = 'ANALYSIS'
            self.current_mode = 'RANGING'
            logger.info("📊 Ranging market - Mean reversion specialist activated")
        
        # ===== SENTIMENT EVENT =====
        elif abs(sentiment) > 0.7:
            self._activate_specialist('SENTIMENT', 0.3)
            self.current_level = 'EXECUTION'
            self.current_mode = 'SENTIMENT_DRIVEN'
            direction = 'BULLISH' if sentiment > 0 else 'BEARISH'
            logger.info(f"📰 Strong sentiment ({direction}) - Sentiment specialist activated")
        
        # ===== NORMAL MARKET =====
        else:
            self._deactivate_all()
            self.current_level = 'MONITORING'
            self.current_mode = 'NORMAL'
    
    def _activate_specialist(self, name: str, weight: float):
        """Activate a specialist."""
        self.specialists[name]['active'] = True
        self.specialists[name]['weight'] = weight
        self.specialists[name]['last_activation'] = datetime.now()
        
        self.event_log.append({
            'timestamp': datetime.now(),
            'event': 'ACTIVATE',
            'specialist': name,
            'weight': weight
        })
    
    def _deactivate_specialist(self, name: str):
        """Deactivate a specialist."""
        if name in self.specialists:
            self.specialists[name]['active'] = False
            self.specialists[name]['weight'] = 0
    
    def _deactivate_all(self):
        """Deactivate all specialists."""
        for name in self.specialists:
            self.specialists[name]['active'] = False
            self.specialists[name]['weight'] = 0
    
    def get_weighted_decision(self, agent_signals: Dict) -> Dict:
        """
        Get weighted decision from active specialists only.
        """
        if self.current_level == 'CRITICAL':
            # In critical mode, only liquidity specialist decides
            if self.specialists['LIQUIDITY']['active']:
                return {
                    'action': 'HOLD',
                    'confidence': 100,
                    'reason': 'Critical mode - Holding',
                    'specialists_active': ['LIQUIDITY'],
                    'mode': self.current_mode
                }
        
        votes = {'BUY': 0, 'SELL': 0, 'HOLD': 0}
        active_specialists = []
        
        for agent_name, signal in agent_signals.items():
            agent_key = self._map_agent_to_specialist(agent_name)
            
            if agent_key in self.specialists:
                if self.specialists[agent_key]['active']:
                    weight = self.specialists[agent_key]['weight']
                    vote = signal.get('vote', 'HOLD')
                    confidence = signal.get('confidence', 50)
                    
                    votes[vote] += confidence * weight
                    active_specialists.append(agent_key)
        
        # If no specialists active, return HOLD
        if not active_specialists:
            return {
                'action': 'HOLD',
                'confidence': 0,
                'reason': 'No active specialists',
                'specialists_active': [],
                'mode': self.current_mode
            }
        
        # Determine action
        action = max(votes, key=votes.get)
        total_votes = sum(votes.values())
        
        if total_votes > 0:
            confidence = (votes[action] / total_votes) * 100
        else:
            confidence = 0
        
        return {
            'action': action,
            'confidence': round(confidence, 1),
            'reason': f'Specialists: {", ".join(active_specialists)}',
            'specialists_active': active_specialists,
            'mode': self.current_mode,
            'level': self.current_level,
            'votes': votes
        }
    
    def _map_agent_to_specialist(self, agent_name: str) -> str:
        """Map agent name to specialist type."""
        mapping = {
            'X': 'MEAN_REVERSION',
            'I': 'SENTIMENT',
            'Q': 'LIQUIDITY',
            'D': 'VOLATILITY',
            'R': 'TREND',
            'G': 'LIQUIDITY',
            'W': 'SENTIMENT'
        }
        return mapping.get(agent_name, agent_name)
    
    def add_to_execution_queue(self, signal: Dict):
        """Add signal to execution queue for fast execution."""
        self.execution_queue.append({
            'signal': signal,
            'timestamp': datetime.now(),
            'status': 'PENDING'
        })
        
        # Keep queue manageable
        if len(self.execution_queue) > 100:
            self.execution_queue = self.execution_queue[-100:]
    
    def get_execution_queue(self) -> List[Dict]:
        """Get and clear execution queue."""
        queue = self.execution_queue.copy()
        self.execution_queue = [item for item in self.execution_queue if item['status'] != 'PENDING']
        return queue
    
    def get_status(self) -> Dict:
        """Get current status."""
        return {
            'current_level': self.current_level,
            'current_mode': self.current_mode,
            'active_specialists': [
                name for name, data in self.specialists.items() if data['active']
            ],
            'specialist_weights': {
                name: data['weight'] for name, data in self.specialists.items()
            },
            'execution_queue_length': len(self.execution_queue),
            'event_log_length': len(self.event_log)
        }