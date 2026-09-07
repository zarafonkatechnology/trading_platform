# src/api/websocket_manager.py
"""
WebSocket Manager - MINIMAL WORKING VERSION
"""

import json
import asyncio
import logging
from typing import Dict, Set
from fastapi import WebSocket, WebSocketDisconnect, APIRouter
from datetime import datetime

logger = logging.getLogger(__name__)

# ============================================================
# ROUTER - Create this first
# ============================================================

router = APIRouter()

# ============================================================
# PRICE CACHE (Simple in-memory)
# ============================================================

_prices = {
    'EURUSD': 1.14337,
    'GBPUSD': 1.34509,
    'USDJPY': 162.449,
    'GOLD': 3987.55,
    '#NASDAQ100': 21500.00,
}

def get_prices():
    return _prices.copy()

def update_prices(prices):
    global _prices
    if prices:
        _prices.update(prices)

# ============================================================
# CONNECTION MANAGER
# ============================================================

class ConnectionManager:
    def __init__(self):
        self.active_connections: Set[WebSocket] = set()
        self._running = False
        self._task = None
    
    async def start(self):
        if self._running:
            return
        self._running = True
        self._task = asyncio.create_task(self._broadcast_loop())
        logger.info("✅ WebSocket Manager started")
    
    async def _broadcast_loop(self):
        last_prices = {}
        while self._running:
            try:
                current_prices = get_prices()
                if current_prices != last_prices and self.active_connections:
                    last_prices = current_prices.copy()
                    message = {
                        'type': 'price_update',
                        'data': current_prices,
                        'timestamp': datetime.now().isoformat()
                    }
                    await self.broadcast(message)
                await asyncio.sleep(1)
            except Exception as e:
                logger.error(f"Broadcast error: {e}")
                await asyncio.sleep(1)
    
    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.add(websocket)
        logger.info(f"✅ WebSocket connected (Total: {len(self.active_connections)})")
        
        # Send initial prices
        await websocket.send_json({
            'type': 'initial_prices',
            'data': get_prices(),
            'timestamp': datetime.now().isoformat()
        })
    
    def disconnect(self, websocket: WebSocket):
        self.active_connections.discard(websocket)
        logger.info(f"❌ WebSocket disconnected (Total: {len(self.active_connections)})")
    
    async def broadcast(self, message: dict):
        disconnected = set()
        for websocket in self.active_connections:
            try:
                await websocket.send_json(message)
            except:
                disconnected.add(websocket)
        
        for websocket in disconnected:
            self.disconnect(websocket)
    
    async def handle_message(self, websocket: WebSocket, message: str):
        try:
            if message == 'ping':
                await websocket.send_text('pong')
            elif message == 'get_prices':
                await websocket.send_json({
                    'type': 'price_response',
                    'data': get_prices()
                })
            else:
                # Try JSON
                try:
                    data = json.loads(message)
                    if data.get('type') == 'update_prices':
                        update_prices(data.get('prices', {}))
                        await websocket.send_json({
                            'type': 'update_ack',
                            'status': 'ok'
                        })
                except:
                    pass
        except Exception as e:
            logger.error(f"Message handler error: {e}")

# ============================================================
# SINGLETON
# ============================================================

manager = ConnectionManager()

# ============================================================
# ✅ WEBSOCKET ENDPOINT
# ============================================================

@router.websocket("/ws/prices/{client_id}")
async def websocket_prices(websocket: WebSocket, client_id: str):
    """WebSocket endpoint for real-time prices"""
    await manager.start()
    
    try:
        await manager.connect(websocket)
        
        while True:
            try:
                data = await websocket.receive_text()
                await manager.handle_message(websocket, data)
            except WebSocketDisconnect:
                break
            except Exception as e:
                logger.error(f"Error: {e}")
                break
                
    except Exception as e:
        logger.error(f"WebSocket error: {e}")
    finally:
        manager.disconnect(websocket)

# ============================================================
# HTTP ENDPOINTS FOR TESTING
# ============================================================

@router.get("/ws/status")
async def ws_status():
    return {
        "connected": len(manager.active_connections),
        "prices": len(get_prices()),
        "running": manager._running
    }

@router.get("/ws/test")
async def ws_test():
    return {
        "message": "WebSocket router is working!",
        "websocket_endpoint": "/api/v1/ws/prices/{client_id}",
        "status_endpoint": "/api/v1/ws/status"
    }