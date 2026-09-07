import logging
import asyncio
import uuid
from datetime import datetime
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field
from enum import Enum

logger = logging.getLogger(__name__)

@dataclass
class CopyClient:
    client_id: str
    name: str
    balance: float
    equity: float
    mt4_account: str
    mt4_password: str
    mt4_server: str
    risk_per_trade: float = 0.02  # 2% risk per trade
    max_volume: float = 10.0
    is_active: bool = True
    created_at: datetime = field(default_factory=datetime.now)

@dataclass
class CopyTrade:
    trade_id: str
    signal_id: str
    client_id: str
    symbol: str
    order_type: str
    volume: float
    entry_price: float
    stop_loss: float
    take_profit: float
    status: str = "PENDING"
    executed_at: Optional[datetime] = None
    profit: float = 0.0
    closed_at: Optional[datetime] = None

class CopyEngine:
    """Copy trading engine that replicates trades to client accounts"""
    
    def __init__(self):
        self.clients: Dict[str, CopyClient] = {}
        self.trades: Dict[str, CopyTrade] = {}
        self._running = False
        self._workers = 10
        
    async def start(self):
        """Start the copy engine"""
        self._running = True
        logger.info("Copy engine started")
        asyncio.create_task(self._process_queue())
        
    async def stop(self):
        """Stop the copy engine"""
        self._running = False
        logger.info("Copy engine stopped")
        
    async def add_client(self, client: CopyClient) -> str:
        """Add a new client for copy trading"""
        client.client_id = f"CLIENT-{uuid.uuid4().hex[:8]}"
        self.clients[client.client_id] = client
        logger.info(f"Client {client.client_id} added for copy trading")
        return client.client_id
    
    async def remove_client(self, client_id: str) -> bool:
        """Remove a client from copy trading"""
        if client_id in self.clients:
            del self.clients[client_id]
            logger.info(f"Client {client_id} removed")
            return True
        return False
    
    async def execute_copy_trade(self, signal: Dict[str, Any]) -> List[CopyTrade]:
        """Execute a trade for all active clients"""
        trades = []
        
        for client_id, client in self.clients.items():
            if not client.is_active:
                continue
                
            # Calculate volume based on client's risk
            volume = await self._calculate_volume(client, signal)
            if volume <= 0:
                continue
            
            # Create copy trade
            trade = CopyTrade(
                trade_id=f"COPY-{uuid.uuid4().hex[:8]}",
                signal_id=signal.get('signal_id', ''),
                client_id=client_id,
                symbol=signal.get('symbol', ''),
                order_type=signal.get('order_type', ''),
                volume=volume,
                entry_price=signal.get('entry_price', 0),
                stop_loss=signal.get('stop_loss', 0),
                take_profit=signal.get('take_profit', 0),
                status="PENDING"
            )
            
            # Execute the trade
            success = await self._execute_trade(client, trade)
            if success:
                trades.append(trade)
                logger.info(f"Copy trade {trade.trade_id} executed for client {client_id}")
            else:
                logger.warning(f"Copy trade failed for client {client_id}")
        
        return trades
    
    async def _calculate_volume(self, client: CopyClient, signal: Dict[str, Any]) -> float:
        """Calculate trade volume based on client's risk parameters"""
        base_volume = signal.get('volume', 0.01)
        risk_adjusted = base_volume * client.risk_per_trade / 0.02  # Normalize to 2% risk
        
        # Apply client limits
        return min(max(risk_adjusted, 0.01), client.max_volume)
    
    async def _execute_trade(self, client: CopyClient, trade: CopyTrade) -> bool:
        """Execute a trade for a client"""
        try:
            # Here we would send the trade to MT4
            # For now, just simulate execution
            trade.executed_at = datetime.now()
            trade.status = "EXECUTED"
            return True
        except Exception as e:
            logger.error(f"Error executing trade for client {client.client_id}: {e}")
            trade.status = "FAILED"
            return False
    
    async def _process_queue(self):
        """Process pending trades"""
        while self._running:
            # Process pending trades
            pending_trades = [t for t in self.trades.values() if t.status == "PENDING"]
            
            for trade in pending_trades[:self._workers]:
                # Execute trade
                await self._execute_trade(
                    self.clients.get(trade.client_id),
                    trade
                )
            
            await asyncio.sleep(1)
    
    def get_client(self, client_id: str) -> Optional[CopyClient]:
        """Get client by ID"""
        return self.clients.get(client_id)
    
    def get_client_trades(self, client_id: str) -> List[CopyTrade]:
        """Get all trades for a client"""
        return [t for t in self.trades.values() if t.client_id == client_id]
    
    def get_active_trades(self) -> List[CopyTrade]:
        """Get all active trades"""
        return [t for t in self.trades.values() if t.status == "EXECUTED"]
    
    def get_client_count(self) -> int:
        """Get number of active clients"""
        return len([c for c in self.clients.values() if c.is_active])
    
    def get_client_stats(self, client_id: str) -> Dict[str, Any]:
        """Get statistics for a client"""
        client_trades = self.get_client_trades(client_id)
        
        if not client_trades:
            return {
                'total_trades': 0,
                'win_rate': 0,
                'total_profit': 0,
                'average_volume': 0
            }
        
        total_trades = len(client_trades)
        winning_trades = [t for t in client_trades if t.profit > 0]
        total_profit = sum(t.profit for t in client_trades)
        
        return {
            'total_trades': total_trades,
            'win_rate': len(winning_trades) / total_trades if total_trades > 0 else 0,
            'total_profit': total_profit,
            'average_volume': sum(t.volume for t in client_trades) / total_trades if total_trades > 0 else 0
        }