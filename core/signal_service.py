"""Unified Signal Service - Manage signals from all sources"""

import json
import os
from datetime import datetime, timedelta
from typing import Dict, List
import logging

logger = logging.getLogger(__name__)

class SignalService:
    """Centralized signal management"""
    
    def __init__(self):
        self.signals = []
        self.max_signals = 1000
        self.signal_file = 'signals.json'
        self._load_signals()
        logger.info("SignalService initialized")
    
    def _load_signals(self):
        """Load signals from file"""
        try:
            if os.path.exists(self.signal_file):
                with open(self.signal_file, 'r') as f:
                    self.signals = json.load(f)
        except Exception:
            pass
    
    def _save_signals(self):
        """Save signals to file"""
        try:
            with open(self.signal_file, 'w') as f:
                json.dump(self.signals[-self.max_signals:], f, indent=2, default=str)
        except Exception:
            pass
    
    def add_signal(self, symbol: str, signal_type: str, confidence: float,
                   price: float, z_score: float = 0, reasoning: str = '',
                   source: str = 'MANUAL', sl: float = 0, tp: float = 0) -> Dict:
        """Add a new trading signal"""
        signal = {
            'id': f"SIG-{datetime.now().strftime('%Y%m%d%H%M%S')}-{symbol}",
            'symbol': symbol,
            'signal_type': signal_type,
            'confidence': int(confidence),
            'entry_price': price,
            'z_score': round(z_score, 3),
            'reasoning': reasoning or f"{source}: {signal_type}",
            'source': source,
            'sl': sl,
            'tp': tp,
            'status': 'PENDING',
            'created_at': datetime.now().isoformat(),
            'expires_at': (datetime.now() + timedelta(minutes=5)).isoformat()
        }
        self.signals.append(signal)
        if len(self.signals) > self.max_signals:
            self.signals = self.signals[-self.max_signals:]
        self._save_signals()
        logger.info(f"Signal added: {symbol} {signal_type} ({confidence:.0f}%)")
        return signal
    
    def update_signal_status(self, signal_id: str, status: str, position_id: str = None):
        """Update signal status"""
        for signal in self.signals:
            if signal.get('id') == signal_id:
                signal['status'] = status
                if position_id:
                    signal['position_id'] = position_id
                signal['updated_at'] = datetime.now().isoformat()
                self._save_signals()
                return True
        return False
    
    def get_pending_signals(self) -> List[Dict]:
        """Get all pending signals"""
        now = datetime.now()
        pending = []
        for signal in self.signals:
            if signal['status'] == 'PENDING':
                try:
                    if now < datetime.fromisoformat(signal['expires_at']):
                        pending.append(signal)
                except Exception:
                    pass
        return pending
    
    def get_recent_signals(self, limit: int = 50) -> List[Dict]:
        """Get recent signals filtered for validity"""
        # Get all signals
        signals = self.signals[-limit:]
        
        # Filter: Only show signals with confidence >= 60 and not expired
        valid_signals = []
        now = datetime.now()
        
        for s in signals:
            # Check if signal is still valid (not expired)
            if s.get('status') == 'PENDING':
                try:
                    expires_at = datetime.fromisoformat(s['expires_at'])
                    if now < expires_at:
                        valid_signals.append(s)
                except:
                    valid_signals.append(s)
            elif s.get('status') == 'EXECUTED':
                valid_signals.append(s)
    
        return valid_signals[-limit:]
    def get_stats(self) -> Dict:
        """Get signal statistics"""
        signals = self.signals
        stats = {
            'total_signals': len(signals),
            'pending': len([s for s in signals if s['status'] == 'PENDING']),
            'executed': len([s for s in signals if s['status'] == 'EXECUTED']),
            'expired': len([s for s in signals if s['status'] == 'EXPIRED']),
            'by_source': {}
        }
        for signal in signals:
            source = signal.get('source', 'UNKNOWN')
            stats['by_source'][source] = stats['by_source'].get(source, 0) + 1
        return stats

# Global instance
signal_service = SignalService()