# src/core/signal_generator.py
"""
Signal Generator for trading platform
"""

import logging
import uuid
from datetime import datetime
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field
from enum import Enum

logger = logging.getLogger(__name__)

class SignalType(Enum):
    BUY = "BUY"
    SELL = "SELL"
    CLOSE = "CLOSE"

class SignalStrength(Enum):
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"

@dataclass
class TradeSignal:
    signal_id: str
    symbol: str
    signal_type: SignalType
    entry_price: float
    stop_loss: float
    take_profit: float
    volume: float
    strength: SignalStrength
    timestamp: datetime = field(default_factory=datetime.now)
    source: str = "AI_Agent"
    confidence: float = 0.7
    description: str = ""
    expiry_time: Optional[datetime] = None
    is_executed: bool = False

class SignalGenerator:
    """Generates trading signals from AI agents and brokers"""
    
    def __init__(self):
        self.signals: Dict[str, TradeSignal] = {}
        self._agent_scores: Dict[str, float] = {}
        self._signal_counter = 0
        
    async def generate_signal(self, 
                            symbol: str, 
                            signal_type: SignalType,
                            entry_price: float,
                            stop_loss: float,
                            take_profit: float,
                            volume: float,
                            agent_name: str = "AI_Agent",
                            confidence: float = 0.7,
                            description: str = "") -> TradeSignal:
        """Generate a new trading signal"""
        
        signal = TradeSignal(
            signal_id=f"SIG-{uuid.uuid4().hex[:8]}",
            symbol=symbol,
            signal_type=signal_type,
            entry_price=entry_price,
            stop_loss=stop_loss,
            take_profit=take_profit,
            volume=volume,
            strength=self._calculate_signal_strength(confidence),
            source=agent_name,
            confidence=confidence,
            description=description
        )
        
        self.signals[signal.signal_id] = signal
        logger.info(f"Signal {signal.signal_id} generated: {signal_type} {symbol} at {entry_price}")
        
        return signal
    
    def generate_signal_sync(self, 
                            symbol: str, 
                            signal_type: str,
                            entry_price: float,
                            stop_loss: float,
                            take_profit: float,
                            volume: float,
                            agent_name: str = "AI_Agent",
                            confidence: float = 0.7,
                            description: str = "") -> TradeSignal:
        """Generate a signal synchronously (for non-async contexts)"""
        
        signal = TradeSignal(
            signal_id=f"SIG-{uuid.uuid4().hex[:8]}",
            symbol=symbol,
            signal_type=SignalType(signal_type.upper()),
            entry_price=entry_price,
            stop_loss=stop_loss,
            take_profit=take_profit,
            volume=volume,
            strength=self._calculate_signal_strength(confidence),
            source=agent_name,
            confidence=confidence,
            description=description
        )
        
        self.signals[signal.signal_id] = signal
        logger.info(f"Signal {signal.signal_id} generated: {signal_type} {symbol} at {entry_price}")
        
        return signal
    
    def _calculate_signal_strength(self, confidence: float) -> SignalStrength:
        """Calculate signal strength based on confidence"""
        if confidence >= 0.8:
            return SignalStrength.HIGH
        elif confidence >= 0.6:
            return SignalStrength.MEDIUM
        else:
            return SignalStrength.LOW
    
    def get_signal(self, signal_id: str) -> Optional[TradeSignal]:
        """Get signal by ID"""
        return self.signals.get(signal_id)
    
    def get_active_signals(self) -> List[TradeSignal]:
        """Get all active signals"""
        now = datetime.now()
        return [
            signal for signal in self.signals.values()
            if (signal.expiry_time is None or signal.expiry_time > now) 
            and not signal.is_executed
        ]
    
    def get_signals_by_symbol(self, symbol: str) -> List[TradeSignal]:
        """Get all signals for a specific symbol"""
        return [s for s in self.signals.values() if s.symbol == symbol]
    
    def expire_signal(self, signal_id: str) -> bool:
        """Expire a signal"""
        if signal_id in self.signals:
            self.signals[signal_id].expiry_time = datetime.now()
            return True
        return False
    
    async def mark_executed(self, signal_id: str) -> bool:
        """Mark signal as executed"""
        if signal_id in self.signals:
            self.signals[signal_id].is_executed = True
            return True
        return False
    
    def mark_executed_sync(self, signal_id: str) -> bool:
        """Mark signal as executed (sync version)"""
        if signal_id in self.signals:
            self.signals[signal_id].is_executed = True
            return True
        return False
    
    def clear_expired(self) -> int:
        """Clear expired signals and return count"""
        expired = [s for s in self.signals.values() if s.expiry_time and s.expiry_time < datetime.now()]
        for s in expired:
            del self.signals[s.signal_id]
        return len(expired)
    
    def get_stats(self) -> Dict[str, Any]:
        """Get signal statistics"""
        total = len(self.signals)
        active = len(self.get_active_signals())
        executed = sum(1 for s in self.signals.values() if s.is_executed)
        
        return {
            'total_signals': total,
            'active_signals': active,
            'executed_signals': executed,
            'pending_signals': total - active - executed
        }