# ============================================================
# shadow_trading.py - Simulation Comparison
# ============================================================
# Runs shadow system in parallel, compares performance
# ============================================================

import copy
import numpy as np
from typing import Dict, List, Optional
from datetime import datetime
import logging

logger = logging.getLogger(__name__)


class ShadowTradingSystem:
    """
    Shadow Trading System.
    
    Runs a shadow copy of the live system with modified parameters.
    Compares performance and suggests improvements.
    """
    
    def __init__(self, live_system):
        self.live_system = live_system
        self.shadow_system = None
        self.comparison = []
        self.suggestions = []
        
        self.parameters_to_test = {
            'z_threshold': 1.1,      # 10% higher threshold
            'position_size': 0.8,    # 20% smaller positions
            'confidence': 0.9,       # 10% lower confidence requirement
            'stop_loss': 1.2,        # 20% wider stop loss
        }
        
        self.shadow_enabled = True
        
        logger.info("✅ ShadowTradingSystem initialized")
    
    def create_shadow(self):
        """Create a shadow system with modified parameters."""
        if self.live_system is None:
            return None
        
        # Deep copy the live system
        try:
            self.shadow_system = copy.deepcopy(self.live_system)
            
            # Apply parameter modifications
            if hasattr(self.shadow_system, 'z_threshold'):
                self.shadow_system.z_threshold = self.shadow_system.z_threshold * self.parameters_to_test['z_threshold']
            
            if hasattr(self.shadow_system, 'position_size_multiplier'):
                self.shadow_system.position_size_multiplier = self.parameters_to_test['position_size']
            
            logger.info("   Shadow system created with modified parameters")
            
        except Exception as e:
            logger.warning(f"   Shadow creation failed: {e}")
            self.shadow_system = None
        
        return self.shadow_system
    
    def run_cycle(self, market_data: Dict, live_result: Dict):
        """
        Run both systems simultaneously and compare.
        """
        if not self.shadow_enabled:
            return
        
        if self.shadow_system is None:
            self.create_shadow()
        
        if self.shadow_system is None:
            return
        
        # Live system already ran
        # Run shadow system
        try:
            if hasattr(self.shadow_system, 'analyze'):
                shadow_result = self.shadow_system.analyze(market_data)
                self._compare(live_result, shadow_result)
        except Exception as e:
            logger.warning(f"Shadow analysis error: {e}")
    
    def _compare(self, live: Dict, shadow: Dict):
        """
        Compare live and shadow results.
        """
        live_action = live.get('action', 'HOLD')
        shadow_action = shadow.get('action', 'HOLD')
        live_conf = live.get('confidence', 0)
        shadow_conf = shadow.get('confidence', 0)
        
        self.comparison.append({
            'timestamp': datetime.now(),
            'live': {'action': live_action, 'confidence': live_conf},
            'shadow': {'action': shadow_action, 'confidence': shadow_conf},
            'agreement': live_action == shadow_action
        })
        
        # Keep history manageable
        if len(self.comparison) > 500:
            self.comparison = self.comparison[-500:]
    
    def add_trade_result(self, trade: Dict):
        """
        Add trade result to both systems.
        """
        if hasattr(self.live_system, 'add_trade_result'):
            self.live_system.add_trade_result(trade)
        
        if self.shadow_system and hasattr(self.shadow_system, 'add_trade_result'):
            self.shadow_system.add_trade_result(trade)
    
    def analyze_performance(self) -> Dict:
        """
        Analyze performance difference between live and shadow.
        """
        if len(self.comparison) < 20:
            return {'status': 'INSUFFICIENT_DATA'}
        
        # Count agreements
        agreements = sum(1 for c in self.comparison if c['agreement'])
        agreement_rate = agreements / len(self.comparison)
        
        # Get performance metrics from both systems
        live_pnls = []
        shadow_pnls = []
        
        for c in self.comparison:
            if hasattr(self.live_system, 'performance'):
                # This would need to be implemented
                pass
        
        # Analyze if shadow is outperforming
        if agreement_rate < 0.5:
            suggestion = {
                'type': 'INCREASE_THRESHOLD',
                'message': f'Shadow agrees on {agreement_rate*100:.0f}% - Consider increasing Z-threshold',
                'priority': 'MEDIUM'
            }
            self.suggestions.append(suggestion)
        
        return {
            'agreement_rate': round(agreement_rate * 100, 1),
            'comparison_count': len(self.comparison),
            'suggestions': self.suggestions[-5:],
            'shadow_enabled': self.shadow_enabled
        }
    
    def get_status(self) -> Dict:
        """Get shadow trading status."""
        return {
            'shadow_enabled': self.shadow_enabled,
            'comparison_count': len(self.comparison),
            'suggestions_count': len(self.suggestions),
            'parameters': self.parameters_to_test
        }