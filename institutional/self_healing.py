# ============================================================
# self_healing.py - Automatic Performance Recovery
# ============================================================
# Detects performance degradation and automatically adjusts
# ============================================================

import numpy as np
from typing import Dict, List, Optional
from datetime import datetime, timedelta
import threading
import logging

logger = logging.getLogger(__name__)


class SelfHealingSystem:
    """
    Self-Healing System.
    
    Automatically adjusts parameters when performance degrades.
    Actions:
    - Reduce position size
    - Increase Z-threshold
    - Pause trading (cooldown)
    - Change strategy weight
    """
    
    def __init__(self):
        self.performance_window = 50
        self.history = []
        self.healing_actions = []
        self.is_paused = False
        self.pause_until = None
        
        self.position_size_multiplier = 1.0
        self.z_threshold = 2.5
        self.strategy_weights = {}
        
        self.consecutive_losses = 0
        self.last_healing_time = None
        
        logger.info("✅ SelfHealingSystem initialized")
    
    def monitor(self, trade_result: Dict):
        """
        Monitor each trade for performance degradation.
        """
        pnl = trade_result.get('pnl', 0)
        z_score = trade_result.get('z_score', 0)
        
        self.history.append({
            'pnl': pnl,
            'z_score': z_score,
            'timestamp': datetime.now(),
            'action': trade_result.get('action', 'HOLD')
        })
        
        # Keep history limited
        if len(self.history) > self.performance_window * 3:
            self.history = self.history[-self.performance_window * 3:]
        
        # Update consecutive losses
        if pnl < 0:
            self.consecutive_losses += 1
        else:
            self.consecutive_losses = 0
        
        # Check if healing is needed
        if len(self.history) >= 20:
            self._check_and_heal()
    
    def _check_and_heal(self):
        """Check if performance is degrading and apply healing."""
        if self.is_paused:
            return
        
        recent = self.history[-20:]
        older = self.history[-40:-20] if len(self.history) >= 40 else []
        
        if not older:
            return
        
        recent_avg = sum(t['pnl'] for t in recent) / len(recent)
        older_avg = sum(t['pnl'] for t in older) / len(older)
        
        # If recent performance is significantly worse
        if older_avg > 0:
            degradation = (recent_avg / older_avg) if older_avg > 0 else 0
        else:
            degradation = 0
        
        # ===== HEALING CONDITIONS =====
        actions = []
        
        # 1. Negative performance
        if recent_avg < 0:
            actions.append({
                'type': 'REDUCE_POSITION',
                'message': f'Negative performance (avg: ${recent_avg:.2f})',
                'action': lambda: self._reduce_position(),
                'priority': 1
            })
        
        # 2. Severe degradation (>50% drop)
        elif degradation < 0.5:
            actions.append({
                'type': 'INCREASE_THRESHOLD',
                'message': f'Performance degradation: {degradation*100:.0f}% of previous',
                'action': lambda: self._increase_threshold(),
                'priority': 2
            })
        
        # 3. Consecutive losses
        elif self.consecutive_losses >= 5:
            actions.append({
                'type': 'PAUSE',
                'message': f'{self.consecutive_losses} consecutive losses',
                'action': lambda: self._pause_trading(3600),
                'priority': 3
            })
        
        # 4. High volatility (if available)
        z_scores = [t['z_score'] for t in recent if t['z_score'] != 0]
        if z_scores and np.std(z_scores) > 2:
            actions.append({
                'type': 'REDUCE_POSITION',
                'message': f'High Z-score volatility: {np.std(z_scores):.2f}',
                'action': lambda: self._reduce_position(),
                'priority': 4
            })
        
        # Apply healing actions
        if actions:
            # Sort by priority
            actions.sort(key=lambda x: x['priority'])
            action = actions[0]  # Apply highest priority only
            
            logger.warning(f"🔧 HEALING: {action['type']} - {action['message']}")
            action['action']()
            
            self.healing_actions.append({
                'timestamp': datetime.now(),
                'type': action['type'],
                'message': action['message'],
                'position_size_multiplier': self.position_size_multiplier,
                'z_threshold': self.z_threshold
            })
            
            self.last_healing_time = datetime.now()
    
    def _reduce_position(self):
        """Reduce position size by 50%."""
        self.position_size_multiplier *= 0.5
        self.position_size_multiplier = max(0.1, self.position_size_multiplier)
        logger.info(f"   Position size reduced to {self.position_size_multiplier*100:.0f}%")
    
    def _increase_threshold(self):
        """Increase Z-threshold by 0.3."""
        self.z_threshold += 0.3
        self.z_threshold = min(4.0, self.z_threshold)
        logger.info(f"   Z-threshold increased to {self.z_threshold:.2f}")
    
    def _pause_trading(self, duration_seconds: int):
        """Pause trading for the specified duration."""
        self.is_paused = True
        self.pause_until = datetime.now() + timedelta(seconds=duration_seconds)
        logger.info(f"   Trading paused for {duration_seconds//60} minutes")
        
        # Auto-resume
        threading.Timer(duration_seconds, self._resume_trading).start()
    
    def _resume_trading(self):
        """Resume trading after pause."""
        self.is_paused = False
        self.pause_until = None
        logger.info("   Trading resumed")
    
    def heal_thresholds(self):
        """Gradually restore thresholds after healing."""
        if self.position_size_multiplier < 0.5:
            self.position_size_multiplier *= 1.1
            self.position_size_multiplier = min(1.0, self.position_size_multiplier)
        
        if self.z_threshold > 2.8:
            self.z_threshold -= 0.1
            self.z_threshold = max(2.5, self.z_threshold)
    
    def can_trade(self) -> Dict:
        """Check if system can trade."""
        if self.is_paused:
            if self.pause_until and datetime.now() < self.pause_until:
                remaining = int((self.pause_until - datetime.now()).seconds / 60)
                return {
                    'can_trade': False,
                    'reason': f'Healing pause ({remaining} min remaining)'
                }
            else:
                self.is_paused = False
                self.pause_until = None
        
        return {
            'can_trade': True,
            'position_multiplier': self.position_size_multiplier,
            'z_threshold': self.z_threshold
        }
    
    def get_status(self) -> Dict:
        """Get current status."""
        return {
            'is_paused': self.is_paused,
            'pause_until': self.pause_until.isoformat() if self.pause_until else None,
            'position_size_multiplier': self.position_size_multiplier,
            'z_threshold': self.z_threshold,
            'consecutive_losses': self.consecutive_losses,
            'healing_actions_count': len(self.healing_actions),
            'last_healing_time': self.last_healing_time.isoformat() if self.last_healing_time else None
        }