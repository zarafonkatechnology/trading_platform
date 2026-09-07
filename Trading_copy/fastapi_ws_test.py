# fastapi_ws_test.py
"""
Simple FastAPI with WebSocket - Test on port 8001
"""

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
import json
import asyncio
import random
from typing import Set
from datetime import datetime
import uvicorn

# ============================================================
# WEBSOCKET MANAGER
# ============================================================

class WSManager:
    def __init__(self):
        self.connections: Set[WebSocket] = set()
        self.prices = {
            'EURUSD': 1.14337,
            'GBPUSD': 1.34509,
            'USDJPY': 162.449,
            'GOLD': 3987.55,
            '#NASDAQ100': 21500.00,
        }
        self._running = False
    
    async def start(self):
        if self._running:
            return
        self._running = True
        asyncio.create_task(self._broadcast())
        print("✅ WebSocket manager started")
    
    async def _broadcast(self):
        last_prices = {}
        while self._running:
            try:
                # Update prices
                for symbol in self.prices:
                    if symbol in ['EURUSD', 'GBPUSD']:
                        change = random.uniform(-0.0003, 0.0003)
                        self.prices[symbol] = round(self.prices[symbol] + change, 5)
                    elif symbol == 'GOLD':
                        change = random.uniform(-0.5, 0.5)
                        self.prices[symbol] = round(self.prices[symbol] + change, 2)
                    elif symbol == '#NASDAQ100':
                        change = random.uniform(-2, 2)
                        self.prices[symbol] = round(self.prices[symbol] + change, 2)
                
                if self.prices != last_prices and self.connections:
                    last_prices = self.prices.copy()
                    message = {
                        'type': 'price_update',
                        'data': self.prices,
                        'timestamp': datetime.now().isoformat()
                    }
                    disconnected = set()
                    for ws in self.connections:
                        try:
                            await ws.send_json(message)
                        except:
                            disconnected.add(ws)
                    for ws in disconnected:
                        self.connections.discard(ws)
                
                await asyncio.sleep(1)
            except:
                pass
    
    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.connections.add(websocket)
        await websocket.send_json({
            'type': 'connected',
            'prices': self.prices,
            'timestamp': datetime.now().isoformat()
        })
        print(f"✅ Connected (Total: {len(self.connections)})")
    
    def disconnect(self, websocket: WebSocket):
        self.connections.discard(websocket)
        print(f"❌ Disconnected (Total: {len(self.connections)})")
    
    async def handle(self, websocket: WebSocket, message: str):
        if message == 'ping':
            await websocket.send_text('pong')
        elif message == 'get_prices':
            await websocket.send_json({
                'type': 'price_response',
                'data': self.prices
            })
        elif message == 'get_status':
            await websocket.send_json({
                'type': 'status_response',
                'connected': len(self.connections)
            })

# ============================================================
# CREATE APP
# ============================================================

app = FastAPI(title="WebSocket Test")

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

manager = WSManager()

# ============================================================
# WEBSOCKET ENDPOINT
# ============================================================

@app.websocket("/ws/prices/{client_id}")
async def websocket_endpoint(websocket: WebSocket, client_id: str):
    await manager.start()
    
    try:
        await manager.connect(websocket)
        
        while True:
            try:
                message = await websocket.receive_text()
                await manager.handle(websocket, message)
            except WebSocketDisconnect:
                break
    except Exception as e:
        print(f"Error: {e}")
    finally:
        manager.disconnect(websocket)

# ============================================================
# HTTP ENDPOINTS
# ============================================================

@app.get("/")
async def root():
    return {
        "name": "WebSocket Test Server",
        "status": "running",
        "websocket": "/ws/prices/{client_id}",
        "connected": len(manager.connections)
    }

@app.get("/ws/test")
async def test():
    return {
        "success": True,
        "message": "WebSocket is working!",
        "endpoint": "/ws/prices/{client_id}",
        "connected": len(manager.connections)
    }

@app.get("/ws/status")
async def status():
    return {
        "success": True,
        "connected": len(manager.connections),
        "prices": len(manager.prices),
        "running": manager._running
    }

@app.get("/ws/prices")
async def get_prices():
    return {
        "success": True,
        "prices": manager.prices,
        "timestamp": datetime.now().isoformat()
    }

# ============================================================
# STARTUP
# ============================================================

@app.on_event("startup")
async def startup():
    print("🚀 Starting WebSocket test server on port 8001...")
    await manager.start()
    print("✅ Server ready!")

# ============================================================
# RUN
# ============================================================

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8001)