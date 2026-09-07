"""
Agent Activation by Market Regime
- Dynamically enables/disables agents based on market conditions
"""

import json
import os
from datetime import datetime
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass, field
from enum import Enum


class MarketRegime(Enum):
    """Market regime types"""
    STRONG_TRENDING = "strong_trending"
    TRENDING = "trending"
    WEAK_TRENDING = "weak_trending"
    RANGING = "ranging"
    VOLATILE = "volatile"
    CHOPPY = "choppy"
    BREAKOUT = "breakout"
    REVERSAL = "reversal"


@dataclass
class AgentProfile:
    """Agent's preferred market conditions"""
    name: str
    agent_type: str
    preferred_regimes: List[MarketRegime]
    avoided_regimes: List[MarketRegime]
    base_activation: bool = True
    current_activation: bool = True
    performance_in_regime: Dict[str, float] = field(default_factory=dict)


class AgentActivationManager:
    """Manages agent activation based on market regime."""
    
    # Agent profiles defining their strengths
    AGENT_PROFILES = {
        # Trend Following Agents
        'Agent_A': AgentProfile(
            name='Agent_A',
            agent_type='Trend Follower',
            preferred_regimes=[MarketRegime.STRONG_TRENDING, MarketRegime.TRENDING, MarketRegime.BREAKOUT],
            avoided_regimes=[MarketRegime.RANGING, MarketRegime.CHOPPY]
        ),
        'Agent_K': AgentProfile(
            name='Agent_K',
            agent_type='Ichimoku Expert',
            preferred_regimes=[MarketRegime.TRENDING, MarketRegime.STRONG_TRENDING, MarketRegime.BREAKOUT],
            avoided_regimes=[MarketRegime.CHOPPY, MarketRegime.RANGING]
        ),
        'Agent_C': AgentProfile(
            name='Agent_C',
            agent_type='Momentum',
            preferred_regimes=[MarketRegime.STRONG_TRENDING, MarketRegime.BREAKOUT, MarketRegime.VOLATILE],
            avoided_regimes=[MarketRegime.RANGING, MarketRegime.CHOPPY]
        ),
        
        # Mean Reversion Agents
        'Agent_B': AgentProfile(
            name='Agent_B',
            agent_type='Mean Reversion',
            preferred_regimes=[MarketRegime.RANGING, MarketRegime.REVERSAL],
            avoided_regimes=[MarketRegime.STRONG_TRENDING, MarketRegime.BREAKOUT]
        ),
        'Agent_R': AgentProfile(
            name='Agent_R',
            agent_type='Supply/Demand',
            preferred_regimes=[MarketRegime.RANGING, MarketRegime.WEAK_TRENDING, MarketRegime.REVERSAL],
            avoided_regimes=[MarketRegime.CHOPPY, MarketRegime.VOLATILE]
        ),
        'Agent_H': AgentProfile(
            name='Agent_H',
            agent_type='Fibonacci',
            preferred_regimes=[MarketRegime.RANGING, MarketRegime.REVERSAL],
            avoided_regimes=[MarketRegime.STRONG_TRENDING]
        ),
        
        # Volatility Agents
        'Agent_D': AgentProfile(
            name='Agent_D',
            agent_type='Volatility',
            preferred_regimes=[MarketRegime.VOLATILE, MarketRegime.BREAKOUT],
            avoided_regimes=[MarketRegime.CHOPPY, MarketRegime.RANGING]
        ),
        'Agent_J': AgentProfile(
            name='Agent_J',
            agent_type='Volume Master',
            preferred_regimes=[MarketRegime.BREAKOUT, MarketRegime.VOLATILE, MarketRegime.STRONG_TRENDING],
            avoided_regimes=[MarketRegime.CHOPPY]
        ),
        
        # Dark Pool / Whale Agents
        'Agent_G': AgentProfile(
            name='Agent_G',
            agent_type='Whale Tracker',
            preferred_regimes=[MarketRegime.VOLATILE, MarketRegime.BREAKOUT],
            avoided_regimes=[MarketRegime.CHOPPY]
        ),
        'Agent_P': AgentProfile(
            name='Agent_P',
            agent_type='Whisper Analyst',
            preferred_regimes=[MarketRegime.VOLATILE, MarketRegime.BREAKOUT],
            avoided_regimes=[MarketRegime.CHOPPY, MarketRegime.RANGING]
        ),
        'Agent_Q': AgentProfile(
            name='Agent_Q',
            agent_type='Dark Pool Whale',
            preferred_regimes=[MarketRegime.VOLATILE, MarketRegime.TRENDING],
            avoided_regimes=[MarketRegime.CHOPPY]
        ),
        
        # Fundamental Agents
        'Agent_I': AgentProfile(
            name='Agent_I',
            agent_type='Sentiment Master',
            preferred_regimes=[MarketRegime.VOLATILE, MarketRegime.BREAKOUT, MarketRegime.REVERSAL],
            avoided_regimes=[MarketRegime.CHOPPY]
        ),
        'Agent_L': AgentProfile(
            name='Agent_L',
            agent_type='Fundamental Master',
            preferred_regimes=[MarketRegime.TRENDING, MarketRegime.BREAKOUT],
            avoided_regimes=[]
        ),
        
        # Pattern Recognition
        'Agent_F': AgentProfile(
            name='Agent_F',
            agent_type='Candlestick',
            preferred_regimes=[MarketRegime.RANGING, MarketRegime.WEAK_TRENDING, MarketRegime.REVERSAL],
            avoided_regimes=[MarketRegime.CHOPPY, MarketRegime.VOLATILE]
        ),
        
        # Always Active Agents
        'Agent_W': AgentProfile(
            name='Agent_W',
            agent_type='Consensus Agent',
            preferred_regimes=[],
            avoided_regimes=[]
        ),
        'Agent_E': AgentProfile(
            name='Agent_E',
            agent_type='Microstructure',
            preferred_regimes=[],
            avoided_regimes=[]
        ),
        'Agent_T': AgentProfile(
            name='Agent_T',
            agent_type='Volume Controller',
            preferred_regimes=[],
            avoided_regimes=[]
        ),
    }
    
    def __init__(self):
        self.current_regime: Optional[MarketRegime] = None
        self.regime_confidence: float = 0.0
        self.regime_history: List[Tuple[MarketRegime, datetime]] = []
        self.agent_profiles = self.AGENT_PROFILES.copy()
        self.activation_history: List[Dict] = []
        self.history_file = "agent_activation_history.json"
        self._load_history()
        
        # Register any missing agents with default profile
        self._register_default_profiles()
    
    def _register_default_profiles(self):
        """Register default profiles for agents not in AGENT_PROFILES"""
        default_agents = ['Agent_M', 'Agent_N', 'Agent_O', 'Agent_S', 
                         'Agent_U', 'Agent_V', 'Agent_X']
        
        for agent in default_agents:
            if agent not in self.agent_profiles:
                self.agent_profiles[agent] = AgentProfile(
                    name=agent,
                    agent_type='General',
                    preferred_regimes=[MarketRegime.TRENDING, MarketRegime.RANGING],
                    avoided_regimes=[MarketRegime.CHOPPY]
                )
    
    def _load_history(self):
        """Load activation history from disk"""
        if os.path.exists(self.history_file):
            try:
                with open(self.history_file, 'r') as f:
                    data = json.load(f)
                    self.regime_history = [
                        (MarketRegime(r[0]), datetime.fromisoformat(r[1]))
                        for r in data.get('regime_history', [])
                    ]
            except Exception as e:
                print(f"Failed to load activation history: {e}")
    
    def _save_history(self):
        """Save activation history to disk"""
        try:
            data = {
                'timestamp': datetime.now().isoformat(),
                'current_regime': self.current_regime.value if self.current_regime else None,
                'regime_confidence': self.regime_confidence,
                'regime_history': [
                    [r.value, dt.isoformat()] for r, dt in self.regime_history[-100:]
                ],
                'activation_history': self.activation_history[-50:]
            }
            with open(self.history_file, 'w') as f:
                json.dump(data, f, indent=2)
        except Exception as e:
            print(f"Failed to save activation history: {e}")
    
    def detect_regime(self, market_data: Dict) -> Tuple[MarketRegime, float]:
        """Detect current market regime from market data."""
        adx = market_data.get('adx', 25)
        volatility = market_data.get('volatility', 0.01)
        trend_strength = market_data.get('trend_strength', 50)
        rsi = market_data.get('rsi', 50)
        volume_ratio = market_data.get('volume_ratio', 1.0)
        price_position = market_data.get('price_position', 0)
        
        if adx > 40 and trend_strength > 70:
            regime = MarketRegime.STRONG_TRENDING
            confidence = min(95, 60 + (adx - 40) * 1.5)
        elif adx > 25 and trend_strength > 55:
            regime = MarketRegime.TRENDING
            confidence = min(85, 55 + (adx - 25))
        elif adx > 20 and trend_strength > 45:
            regime = MarketRegime.WEAK_TRENDING
            confidence = 50 + (adx - 20) * 3
        elif volatility > 0.02 and adx < 25:
            regime = MarketRegime.VOLATILE
            confidence = 60 + min(30, volatility * 1000)
        elif adx < 20 and abs(price_position) < 0.01:
            regime = MarketRegime.RANGING
            confidence = 60 + (20 - adx) * 2
        elif adx < 20 and volatility > 0.015:
            regime = MarketRegime.CHOPPY
            confidence = 50 + (20 - adx) * 2
        elif volume_ratio > 1.5 and adx > 25:
            regime = MarketRegime.BREAKOUT
            confidence = 70 + min(25, (volume_ratio - 1) * 25)
        elif rsi > 70 or rsi < 30:
            regime = MarketRegime.REVERSAL
            confidence = 60 + min(30, abs(rsi - 50) / 1.5)
        else:
            regime = MarketRegime.MIXED
            confidence = 40
        
        # Store history
        self.current_regime = regime
        self.regime_confidence = confidence
        self.regime_history.append((regime, datetime.now()))
        
        if len(self.regime_history) > 1000:
            self.regime_history = self.regime_history[-1000:]
        
        self._save_history()
        
        return regime, confidence
    
    def get_active_agents(self, regime: MarketRegime = None) -> List[str]:
        """Get list of agents that should be active in current regime."""
        if regime is None:
            regime = self.current_regime
        
        if regime is None:
            return list(self.agent_profiles.keys())
        
        active_agents = []
        
        for agent_name, profile in self.agent_profiles.items():
            if not profile.preferred_regimes and not profile.avoided_regimes:
                active_agents.append(agent_name)
                profile.current_activation = True
                continue
            
            in_preferred = regime in profile.preferred_regimes
            in_avoided = regime in profile.avoided_regimes
            
            if in_preferred and not in_avoided:
                active_agents.append(agent_name)
                profile.current_activation = True
            elif not in_preferred and not in_avoided:
                active_agents.append(agent_name)
                profile.current_activation = True
            else:
                profile.current_activation = False
        
        return active_agents
    
    def get_inactive_agents(self) -> List[str]:
        """Get list of agents that are currently inactive"""
        return [name for name, profile in self.agent_profiles.items() 
                if not profile.current_activation]
    
    def get_agent_weight(self, agent_name: str) -> float:
        """Get weight multiplier for an agent based on current regime."""
        if not self.current_regime:
            return 1.0
        
        profile = self.agent_profiles.get(agent_name)
        if not profile:
            return 1.0
        
        if not profile.current_activation:
            return 0.0
        
        weight = 1.0
        
        if self.current_regime in profile.preferred_regimes:
            boost = 0.3 if self.current_regime == MarketRegime.STRONG_TRENDING else 0.2
            weight += boost
        
        if self.current_regime in profile.avoided_regimes:
            weight -= 0.5
        
        return max(0.0, min(2.0, weight))
    
    def get_regime_summary(self) -> Dict:
        """Get current regime summary"""
        if not self.current_regime:
            return {'status': 'No regime detected'}
        
        active = self.get_active_agents()
        inactive = self.get_inactive_agents()
        
        return {
            'regime': self.current_regime.value,
            'confidence': round(self.regime_confidence, 1),
            'active_agents': len(active),
            'inactive_agents': len(inactive),
            'active_list': active[:10],
            'inactive_list': inactive[:5] if inactive else [],
            'agent_weights': {
                name: self.get_agent_weight(name)
                for name in active[:15]
            }
        }
    
    def update_regime_from_data(self, market_data: Dict) -> Dict:
        """Update regime based on market data and return activation changes."""
        old_regime = self.current_regime
        old_active = self.get_active_agents() if old_regime else []
        
        new_regime, confidence = self.detect_regime(market_data)
        self.regime_confidence = confidence
        
        new_active = self.get_active_agents(new_regime)
        
        activated = [a for a in new_active if a not in old_active]
        deactivated = [a for a in old_active if a not in new_active]
        
        if activated or deactivated:
            self.activation_history.append({
                'timestamp': datetime.now().isoformat(),
                'old_regime': old_regime.value if old_regime else None,
                'new_regime': new_regime.value,
                'activated': activated,
                'deactivated': deactivated
            })
            self._save_history()
        
        return {
            'regime': new_regime.value,
            'confidence': confidence,
            'activated': activated,
            'deactivated': deactivated,
            'active_count': len(new_active),
            'inactive_count': len(self.agent_profiles) - len(new_active)
        }


class RegimeActivationIntegration:
    """Integrates regime-based activation with your trading system"""
    
    def __init__(self):
        self.activation_manager = AgentActivationManager()
        self.telegram_bot = None
    
    def set_telegram_bot(self, bot):
        self.telegram_bot = bot
    
    def update_regime(self, market_data: Dict) -> Dict:
        """Update regime and return activation changes"""
        result = self.activation_manager.update_regime_from_data(market_data)
        
        if result['activated'] or result['deactivated']:
            message = f"🔄 Market regime changed: {result.get('old_regime', 'None')} → {result['new_regime']}\n"
            if result['activated']:
                message += f"✅ Activated: {', '.join(result['activated'][:5])}\n"
            if result['deactivated']:
                message += f"❌ Deactivated: {', '.join(result['deactivated'][:5])}"
            
            if self.telegram_bot:
                self.telegram_bot.send_message(message)
        
        return result
    
    def get_active_agent_weights(self) -> Dict[str, float]:
        """Get current weights for all agents"""
        weights = {}
        for agent in self.activation_manager.agent_profiles.keys():
            weight = self.activation_manager.get_agent_weight(agent)
            if weight > 0:
                weights[agent] = weight
        return weights
    
    def filter_agent_votes(self, agent_votes: Dict) -> Dict:
        """Filter votes based on active agents and apply regime weights"""
        active_weights = self.get_active_agent_weights()
        
        filtered_votes = {}
        for agent_name, vote_data in agent_votes.items():
            if agent_name in active_weights:
                weight = active_weights[agent_name]
                adjusted_confidence = min(95, vote_data.get('confidence', 50) * weight)
                filtered_votes[agent_name] = {
                    'vote': vote_data.get('vote', 'HOLD'),
                    'confidence': adjusted_confidence,
                    'original_confidence': vote_data.get('confidence', 50),
                    'regime_weight': weight
                }
        
        return filtered_votes
    
    def get_status_message(self) -> str:
        """Get formatted status message for Telegram"""
        summary = self.activation_manager.get_regime_summary()
        
        message = f"""
📊 *MARKET REGIME STATUS*

🎯 *Current Regime:* {summary.get('regime', 'N/A')}
📈 *Confidence:* {summary.get('confidence', 0)}%

🤖 *Agents Status:*
   • Active: {summary.get('active_agents', 0)} agents
   • Inactive: {summary.get('inactive_agents', 0)} agents
"""
        return message


# ============================================================
# Global Instance (MUST BE AFTER CLASS DEFINITIONS)
# ============================================================

regime_activation = RegimeActivationIntegration()
