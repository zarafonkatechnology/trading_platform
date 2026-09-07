# src/api/websocket.py
"""
WebSocket server for real-time signals and market data
"""

from fastapi import WebSocket, WebSocketDisconnect, APIRouter, Depends
from typing import Dict, List, Set
import json
import asyncio
import logging
from datetime import datetime

from src.services.signal_service import signal_service

logger = logging.getLogger(__name__)

router = APIRouter()

# ============================================================
# CONNECTION MANAGER
# ============================================================

class ConnectionManager:
    """Manage WebSocket connections"""
    
    def __init__(self):
        self.active_connections: Dict[str, WebSocket] = {}
        self.connection_symbols: Dict[str, Set[str]] = {}
        self.connection_clients: Dict[str, str] = {}
        self.signal_broadcast_task = None
        self.is_running = False
    
    async def connect(self, websocket: WebSocket, client_id: str):
        """Accept a new connection"""
        await websocket.accept()
        self.active_connections[client_id] = websocket
        self.connection_symbols[client_id] = set()
        self.connection_clients[websocket] = client_id
        logger.info(f"✅ WebSocket connected: {client_id}")

        # Do not replay historical signals on reconnect. Consumers such as MT4
        # may treat every received signal as an execution request.
    
    def disconnect(self, websocket: WebSocket):
        """Remove a disconnected client"""
        client_id = self.connection_clients.get(websocket)
        if client_id:
            if client_id in self.active_connections:
                del self.active_connections[client_id]
            if client_id in self.connection_symbols:
                del self.connection_symbols[client_id]
            if websocket in self.connection_clients:
                del self.connection_clients[websocket]
            logger.info(f"❌ WebSocket disconnected: {client_id}")
    
    async def send_initial_signals(self, client_id: str):
        """Send initial signals to a new client"""
        try:
            signals = signal_service.get_signals_for_client(client_id)
            await self.send_personal_message({
                'type': 'initial_signals',
                'data': {
                    'signals': signals,
                    'count': len(signals),
                    'timestamp': datetime.now().isoformat()
                }
            }, client_id)
        except Exception as e:
            logger.error(f"Error sending initial signals: {e}")
    
    async def send_personal_message(self, message: dict, client_id: str):
        """Send a message to a specific client"""
        if client_id in self.active_connections:
            try:
                await self.active_connections[client_id].send_json(message)
            except Exception as e:
                logger.error(f"Error sending to {client_id}: {e}")
    
    async def broadcast_signal(self, signal: dict):
        """Broadcast a new signal to all connected clients"""
        message = {
            'type': 'new_signal',
            'data': signal,
            'timestamp': datetime.now().isoformat()
        }
        
        for client_id, websocket in self.active_connections.items():
            try:
                # Check if client is subscribed to this symbol
                subscribed = self.connection_symbols.get(client_id, set())
                if not subscribed or signal.get('symbol') in subscribed:
                    await websocket.send_json(message)
            except Exception as e:
                logger.error(f"Error broadcasting to {client_id}: {e}")
    
    async def broadcast(self, message: dict):
        """Broadcast a message to all connected clients"""
        for client_id, websocket in self.active_connections.items():
            try:
                await websocket.send_json(message)
            except Exception as e:
                logger.error(f"Error broadcasting to {client_id}: {e}")
    
    async def handle_subscription(self, client_id: str, symbols: List[str]):
        """Handle client subscription to symbols"""
        if client_id in self.connection_symbols:
            self.connection_symbols[client_id].update(symbols)
            
            # Also update signal service subscription
            signal_service.subscribe_client(client_id, list(self.connection_symbols[client_id]))
            
            logger.info(f"📋 {client_id} subscribed to {len(symbols)} symbols")
    
    async def handle_unsubscription(self, client_id: str):
        """Handle client unsubscription"""
        if client_id in self.connection_symbols:
            self.connection_symbols[client_id] = set()
            signal_service.unsubscribe_client(client_id)
            logger.info(f"📋 {client_id} unsubscribed from all symbols")

# Global connection manager
manager = ConnectionManager()

# ============================================================
# WEBSOCKET ENDPOINT
# ============================================================

@router.websocket("/ws/signals/{client_id}")
async def websocket_signals(websocket: WebSocket, client_id: str):
    """WebSocket endpoint for real-time signals"""
    await manager.connect(websocket, client_id)
    
    try:
        while True:
            # Receive messages from client
            data = await websocket.receive_text()
            try:
                message = json.loads(data)
                msg_type = message.get('type')
                
                if msg_type == 'subscribe':
                    symbols = message.get('symbols', [])
                    await manager.handle_subscription(client_id, symbols)
                    await manager.send_personal_message({
                        'type': 'subscribed',
                        'data': {'symbols': symbols},
                        'timestamp': datetime.now().isoformat()
                    }, client_id)
                
                elif msg_type == 'unsubscribe':
                    await manager.handle_unsubscription(client_id)
                    await manager.send_personal_message({
                        'type': 'unsubscribed',
                        'timestamp': datetime.now().isoformat()
                    }, client_id)
                
                elif msg_type == 'ping':
                    await manager.send_personal_message({
                        'type': 'pong',
                        'timestamp': datetime.now().isoformat()
                    }, client_id)
                    
            except json.JSONDecodeError:
                logger.warning(f"Invalid JSON from {client_id}")
                
    except WebSocketDisconnect:
        manager.disconnect(websocket)
    except Exception as e:
        logger.error(f"WebSocket error: {e}")
        manager.disconnect(websocket)

# ============================================================
# BACKGROUND TASK: BROADCAST SIGNALS
# ============================================================

async def broadcast_signals_task():
    """Background task to broadcast signals to connected clients"""
    manager.is_running = True
    last_signals = []
    
    while manager.is_running:
        try:
            # Get current signals
            current_signals = signal_service.get_all_signals()
            
            # Check for new signals
            if current_signals:
                # Find new signals (not in last batch)
                current_ids = {s.get('signal_id') for s in current_signals}
                last_ids = {s.get('signal_id') for s in last_signals}
                new_ids = current_ids - last_ids
                
                for signal in current_signals:
                    if signal.get('signal_id') in new_ids:
                        # Broadcast new signal
                        await manager.broadcast_signal(signal)
                
                last_signals = current_signals
            
            await asyncio.sleep(5)  # Check every 5 seconds
            
        except Exception as e:
            logger.error(f"Signal broadcast error: {e}")
            await asyncio.sleep(10)

# Start the broadcast task
broadcast_task = None

def start_broadcast_task():
    """Start the background broadcast task"""
    global broadcast_task
    if broadcast_task is None:
        broadcast_task = asyncio.create_task(broadcast_signals_task())
        logger.info("✅ Signal broadcast task started")