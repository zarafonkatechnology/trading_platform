# backend/websocket/account_stream.py

import asyncio
import json
import logging
from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Depends
from typing import Dict, Set, Optional
from datetime import datetime
import random

logger = logging.getLogger(__name__)

router = APIRouter()

# ============================================================
# WEBSOCKET MANAGER
# ============================================================

class AccountWebSocketManager:
    """Real-time account state streaming"""
    
    def __init__(self):
        self.active_connections: Dict[str, Set[WebSocket]] = {}
        self.update_interval = 1  # 1 second updates
        
    async def connect(self, websocket: WebSocket, account_id: str):
        await websocket.accept()
        if account_id not in self.active_connections:
            self.active_connections[account_id] = set()
        self.active_connections[account_id].add(websocket)
        logger.info(f"✅ Client connected: {account_id}")
        
    def disconnect(self, websocket: WebSocket, account_id: str):
        if account_id in self.active_connections:
            self.active_connections[account_id].discard(websocket)
            if not self.active_connections[account_id]:
                del self.active_connections[account_id]
        logger.info(f"❌ Client disconnected: {account_id}")
    
    async def broadcast_account_state(self, account_id: str, account_data: dict):
        """Send real-time account updates"""
        if account_id not in self.active_connections:
            return
        
        message = {
            'type': 'account_state',
            'data': account_data,
            'timestamp': datetime.now().isoformat()
        }
        
        disconnected = []
        for websocket in self.active_connections[account_id]:
            try:
                await websocket.send_json(message)
            except Exception as e:
                logger.error(f"Error sending to client: {e}")
                disconnected.append(websocket)
        
        # Clean up disconnected sockets
        for ws in disconnected:
            self.active_connections[account_id].discard(ws)

# ============================================================
# ACCOUNT STATE CALCULATOR (MOCK FOR TESTING)
# ============================================================

async def get_account_state(account_id: str) -> dict:
    """Calculate complete account state"""
    
    # In production, this would query your database
    # For now, return mock data
    
    # Mock data - simulates real-time changes
    mock_data = {
        'balance': 997911.08,
        'equity': 997773.08 + random.uniform(-5, 5),  # Small random changes
        'used_margin': 6659.80,
        'free_margin': 991113.28 + random.uniform(-5, 5),
        'margin_level': 14982.0 + random.uniform(-10, 10),
        'unrealized_pnl': -138.00 + random.uniform(-5, 5),
        'total_swap': 0,
        'total_commission': 0,
        'position_count': 1,
        'stop_out_level': 50.0,
        'is_margin_call': False,
        'is_stop_out': False,
        'positions': [
            {
                'id': 'pos_1',
                'symbol': 'GBPUSD',
                'type': 'BUY',
                'volume': 1.0,
                'entry': 1.3319,
                'current': 1.3319 + random.uniform(-0.0005, 0.0005),
                'gross_pnl': -138.00 + random.uniform(-5, 5),
                'swap': 0,
                'commission': 0,
                'net_pnl': -138.00 + random.uniform(-5, 5)
            }
        ]
    }
    
    return mock_data

# ============================================================
# WEBSOCKET ENDPOINT
# ============================================================

@router.websocket("/ws/account/{account_id}")
async def websocket_account_stream(websocket: WebSocket, account_id: str):
    manager = AccountWebSocketManager()
    await manager.connect(websocket, account_id)
    
    try:
        # Start streaming
        while True:
            account_data = await get_account_state(account_id)
            await manager.broadcast_account_state(account_id, account_data)
            await asyncio.sleep(1)  # 1 second updates
            
    except WebSocketDisconnect:
        manager.disconnect(websocket, account_id)
    except Exception as e:
        logger.error(f"WebSocket error: {e}")
        manager.disconnect(websocket, account_id)

# ============================================================
# HTTP ENDPOINTS (For testing without WebSocket)
# ============================================================

@router.get("/account/{account_id}")
async def get_account_state_http(account_id: str):
    """Get account state via HTTP (for testing)"""
    try:
        account_data = await get_account_state(account_id)
        return {
            'success': True,
            'account_id': account_id,
            'data': account_data,
            'timestamp': datetime.now().isoformat()
        }
    except Exception as e:
        logger.error(f"Error getting account state: {e}")
        return {
            'success': False,
            'error': str(e)
        }

# ============================================================
# MAIN (For running as standalone)
# ============================================================

if __name__ == "__main__":
    import uvicorn
    from fastapi import FastAPI
    
    app = FastAPI()
    app.include_router(router)
    
    print("🚀 Starting WebSocket server on http://localhost:8000")
    print("📡 WebSocket endpoint: ws://localhost:8000/ws/account/{account_id}")
    print("🔍 HTTP test endpoint: http://localhost:8000/account/test_account")
    
    uvicorn.run(app, host="127.0.0.1", port=8001)