# src/api/main.py - COMPLETE FIXED VERSION
"""
Trading Platform API - Main Application
"""

import asyncio
import json
import logging
import sys
import random
from pathlib import Path
from typing import Set
from fastapi import FastAPI, APIRouter, HTTPException, WebSocket, WebSocketDisconnect, Depends, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware
from datetime import datetime
from fastapi.staticfiles import StaticFiles
import uvicorn
# src/api/main.py - Add these imports
from src.api.routes.client_auth import get_current_user

from src.api.websocket_forex import read_dashboard_file, forex_ws_manager
import asyncio
# Add the project root to path
project_root = Path(__file__).resolve().parents[2]
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# ============================================================
# IMPORT CONTROLLERS (with error handling)
# ============================================================

INDICES_CONTROLLER_AVAILABLE = False
FOREX_CONTROLLER_AVAILABLE = False
SYMBOLS_TO_TRADE = []
FOREX_PAIRS = []

try:
    from trading_controller import AITradingController, SYMBOLS_TO_TRADE
    INDICES_CONTROLLER_AVAILABLE = True
    print(f"✅ Indices controller loaded: {len(SYMBOLS_TO_TRADE)} symbols")
except ImportError as e:
    print(f"⚠️ Indices controller not available: {e}")

try:
    from forex_engine.trading_controller2 import ForexTradingController, FOREX_PAIRS
    FOREX_CONTROLLER_AVAILABLE = True
    print(f"✅ Forex controller loaded: {len(FOREX_PAIRS)} pairs")
except ImportError as e:
    print(f"⚠️ Forex controller not available: {e}")

try:
    from src.core.forex_wrapper import forex_wrapper
    FOREX_CONTROLLER_AVAILABLE = forex_wrapper.is_available()
    if FOREX_CONTROLLER_AVAILABLE:
        print(f"✅ Forex controller available via wrapper")
        
        # Get pairs from the controller
        try:
            import importlib.util
            project_root = Path(__file__).resolve().parents[2]
            trading_copy = project_root / "Trading_copy"
            
            spec = importlib.util.spec_from_file_location(
                "trading_controller2",
                str(trading_copy / "trading_controller2.py")
            )
            module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)
            FOREX_PAIRS = getattr(module, 'FOREX_PAIRS', ['EURUSD', 'GBPUSD', 'USDJPY'])
            print(f"   Forex pairs: {len(FOREX_PAIRS)}")
        except:
            FOREX_PAIRS = ['EURUSD', 'GBPUSD', 'USDJPY', 'USDCHF', 'AUDUSD']
    else:
        print("⚠️ Forex controller not available")
except ImportError as e:
    print(f"⚠️ Forex wrapper not available: {e}")
    FOREX_CONTROLLER_AVAILABLE = False

# ============================================================
# CONTROLLER INSTANCES
# ============================================================

_indices_controller = None
_forex_controller = None

def get_indices_controller():
    global _indices_controller
    if _indices_controller is None and INDICES_CONTROLLER_AVAILABLE:
        _indices_controller = AITradingController()
    return _indices_controller

def get_forex_controller():
    global _forex_controller
    if _forex_controller is None and FOREX_CONTROLLER_AVAILABLE:
        config = {
            'pairs': FOREX_PAIRS[:3],
            'min_confidence': 60,
            'cycle_interval': 10,
            'rl_enabled': True,
        }
        _forex_controller = ForexTradingController(config)
    return _forex_controller

# ============================================================
# WEBSOCKET MANAGER - FIXED VERSION
# ============================================================

class WebSocketManager:
    def __init__(self):
        self.active_connections: Set[WebSocket] = set()
        self.prices = {
            'EURUSD': 1.14337,
            'GBPUSD': 1.34509,
            'USDJPY': 162.449,
            'GOLD': 3987.55,
            '#NASDAQ100': 21500.00,
            '#DJ30': 41500.00,
            '#S&P500': 5600.00,
            'SILVER': 31.25,
        }
        self._running = False
        self._task = None
        self._update_counter = 0
        self._last_prices = {}
    
    async def start(self):
        """Start the broadcast loop"""
        if self._running:
            return
        self._running = True
        self._task = asyncio.create_task(self._broadcast_loop())
        logger.info("✅ WebSocket Manager started")
        return self
    
    async def _broadcast_loop(self):
        """Broadcast REAL MT4 price updates to all connected clients"""
        import json
        import os
        from datetime import datetime
        
        DASHBOARD_FILE = "C:/Users/sifer/AppData/Roaming/MetaQuotes/Terminal/Common/Files/dashboard_data.json"
        
        # ✅ Track if we've logged the file content
        file_logged = False
        
        while self._running:
                try:
                        if self.active_connections:
                                real_prices = {}
                                
                                try:
                                        if os.path.exists(DASHBOARD_FILE):
                                                with open(DASHBOARD_FILE, 'r', encoding='utf-8') as f:
                                                        data = json.load(f)
                                                        
                                                        # ✅ DEBUG: Log file content once
                                                        if not file_logged:
                                                                logger.info(f"📄 File keys: {list(data.keys())}")
                                                                if 'data' in data:
                                                                        logger.info(f"📄 Data keys: {list(data['data'].keys())}")
                                                                file_logged = True
                                                        
                                                        # ✅ Extract prices based on your file structure
                                                        if 'data' in data and 'prices' in data['data']:
                                                                real_prices = data['data']['prices']
                                                        elif 'prices' in data:
                                                                real_prices = data['prices']
                                                        elif 'forex' in data:
                                                                for category in ['forex', 'indices', 'metals', 'energy']:
                                                                        if category in data:
                                                                                real_prices.update(data[category])
                                                        elif 'data' in data:
                                                                # Try to find prices in nested data
                                                                for key in ['forex', 'indices', 'metals', 'energy', 'prices']:
                                                                        if key in data['data']:
                                                                                real_prices.update(data['data'][key])
                                                                
                                        else:
                                                # ✅ Log if file doesn't exist (only once)
                                                if not file_logged:
                                                        logger.warning(f"❌ File not found: {DASHBOARD_FILE}")
                                                        file_logged = True
                                                        
                                except Exception as e:
                                        if not file_logged:
                                                logger.error(f"❌ Error reading file: {e}")
                                                file_logged = True
                                
                                # ✅ If we got real prices, broadcast them
                                if real_prices:
                                        changed = False
                                        for symbol, price in real_prices.items():
                                                if symbol in self.prices and self.prices[symbol] != price:
                                                        self.prices[symbol] = price
                                                        changed = True
                                                elif symbol not in self.prices:
                                                        self.prices[symbol] = price
                                                        changed = True
                                        
                                        if changed:
                                                self._update_counter += 1
                                                
                                                message = {
                                                        'type': 'price_update',
                                                        'data': self.prices.copy(),
                                                        'timestamp': datetime.now().isoformat(),
                                                        'update_id': self._update_counter
                                                }
                                                
                                                disconnected = set()
                                                for ws in self.active_connections:
                                                        try:
                                                                await ws.send_json(message)
                                                        except Exception:
                                                                disconnected.add(ws)
                                                
                                                for ws in disconnected:
                                                        self.active_connections.discard(ws)
                                                logger.info(f"📊 Broadcast update #{self._update_counter}: {len(self.prices)} prices")
                                        
                                        await asyncio.sleep(0.05)
                                else:
                                        # No real prices, wait and try again
                                        await asyncio.sleep(0.1)
                        else:
                                await asyncio.sleep(1)
                                
                except asyncio.CancelledError:
                        break
                except Exception as e:
                        logger.error(f"Broadcast error: {e}")
                        await asyncio.sleep(0.1)
    async def connect(self, websocket: WebSocket, client_id: str = "unknown"):
        """Accept and register a new WebSocket connection"""
        try:
            # Accept the connection
            await websocket.accept()
            self.active_connections.add(websocket)
            
            logger.info(f"✅ WebSocket connected: {client_id} (Total: {len(self.active_connections)})")
            
            # Send initial data
            await websocket.send_json({
                'type': 'connected',
                'client_id': client_id,
                'prices': self.prices,
                'timestamp': datetime.now().isoformat(),
                'total_connections': len(self.active_connections),
                'symbols': len(self.prices)
            })
            
            # Send a second message with connection confirmed
            await websocket.send_json({
                'type': 'connection_confirmed',
                'message': 'You are now receiving live price updates',
                'prices_received': len(self.prices),
                'timestamp': datetime.now().isoformat()
            })
            
            return True
        except Exception as e:
            logger.error(f"Connection error for {client_id}: {e}")
            return False
    
    def disconnect(self, websocket: WebSocket, client_id: str = "unknown"):
        """Remove a WebSocket connection"""
        self.active_connections.discard(websocket)
        logger.info(f"❌ WebSocket disconnected: {client_id} (Total: {len(self.active_connections)})")
    
    async def handle_message(self, websocket: WebSocket, message: str, client_id: str = "unknown"):
        """Handle incoming WebSocket messages"""
        try:
            # Ping
            if message == 'ping':
                await websocket.send_text('pong')
                return
            
            # Get prices
            if message == 'get_prices':
                await websocket.send_json({
                    'type': 'price_response',
                    'data': self.prices,
                    'timestamp': datetime.now().isoformat()
                })
                return
            
            # Get status
            if message == 'get_status':
                await websocket.send_json({
                    'type': 'status_response',
                    'connected_clients': len(self.active_connections),
                    'price_count': len(self.prices),
                    'running': self._running,
                    'update_counter': self._update_counter,
                    'timestamp': datetime.now().isoformat()
                })
                return
            
            # Get connected count
            if message == 'get_connected_count':
                await websocket.send_json({
                    'type': 'connected_count',
                    'count': len(self.active_connections)
                })
                return
            
            # Try to parse JSON
            try:
                data = json.loads(message)
                msg_type = data.get('type', '')
                
                if msg_type == 'update_prices':
                    # Update prices (for admin/testing)
                    self.prices.update(data.get('prices', {}))
                    await websocket.send_json({
                        'type': 'update_ack',
                        'status': 'ok',
                        'timestamp': datetime.now().isoformat()
                    })
                elif msg_type == 'subscribe':
                    symbols = data.get('symbols', [])
                    await websocket.send_json({
                        'type': 'subscription_response',
                        'subscribed': symbols,
                        'timestamp': datetime.now().isoformat()
                    })
            except json.JSONDecodeError:
                # Unknown text message
                await websocket.send_json({
                    'type': 'echo',
                    'message': message,
                    'timestamp': datetime.now().isoformat()
                })
                
        except Exception as e:
            logger.error(f"Message handler error for {client_id}: {e}")
            try:
                await websocket.send_json({
                    'type': 'error',
                    'message': str(e),
                    'timestamp': datetime.now().isoformat()
                })
            except:
                pass

    def stop(self):
        """Stop the broadcast loop"""
        self._running = False
        if self._task:
            self._task.cancel()
            try:
                # Wait for task to complete
                pass
            except:
                pass
        logger.info("⏹️ WebSocket Manager stopped")

# Create singleton manager
ws_manager = WebSocketManager()

# ============================================================
# CREATE FASTAPI APP
# ============================================================

app = FastAPI(
    title="Trading Platform API",
    description="Advanced Trading Platform with MT4 Integration",
    version="1.0.0"
)

# Add CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*", "http://localhost:5500", "http://127.0.0.1:5500", "http://localhost:8000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
# ============================================================
# ✅ REGISTER WEBSOCKET ROUTES BEFORE STATIC FILES
# ============================================================
# ============================================================
# MT4 CANDLE DATA ENDPOINT
# ============================================================
# src/api/main.py - Add this endpoint after your other endpoints
@app.post("/api/v1/cards/update-amount")
async def update_card_amount(
    request: Request,
    user: dict = Depends(get_current_user)
):
    """
    Update the amount column in user_auth_db.trading_cards
    """
    try:
        # Parse request
        payload = await request.json()
        card_id = str(payload.get("card_id", "")).strip()
        new_amount = float(payload.get("amount", 0))
        
        user_id_str = str(user['id'])
        
        print(f"📡 UPDATE AMOUNT: card_id='{card_id}', new_amount=${new_amount}, user={user.get('email')}")
        
        if not card_id:
            return {"success": False, "error": "Card ID required"}
        
        if new_amount < 0:
            return {"success": False, "error": "Amount cannot be negative"}
        
        from src.database.supabase_client import get_user_auth_service
        auth_db = get_user_auth_service()
        
        if not auth_db._connected or not auth_db.client:
            print("❌ Database not connected")
            return {"success": False, "error": "Database not connected"}
        
        # ✅ Find card by card_id
        result = auth_db.client.table('trading_cards')\
            .select('*')\
            .eq('card_id', card_id)\
            .execute()
        
        if not result.data:
            print(f"❌ Card not found: '{card_id}'")
            return {"success": False, "error": f"Card not found: {card_id}"}
        
        card = result.data[0]
        actual_card_id = card.get('card_id')
        current_amount = float(card.get('amount', 0))
        card_used_by = card.get('used_by')
        
        print(f"📋 Found card: '{actual_card_id}', current amount: ${current_amount}")
        
        # ✅ Check if card belongs to this user
        if card_used_by and str(card_used_by) != user_id_str:
            print(f"⚠️ Card belongs to another user: {actual_card_id}")
            return {"success": False, "error": "Card belongs to another user"}
        
        # ✅ UPDATE amount in database - REMOVED updated_at
        print(f"🔄 Updating card '{actual_card_id}' amount to ${new_amount}...")
        
        auth_db.client.table('trading_cards')\
            .update({
                'amount': new_amount
            })\
            .eq('card_id', actual_card_id)\
            .execute()
        
        # ✅ Verify the update worked
        verify_result = auth_db.client.table('trading_cards')\
            .select('*')\
            .eq('card_id', actual_card_id)\
            .execute()
        
        if verify_result.data:
            verified_amount = float(verify_result.data[0].get('amount', 0))
            print(f"✅ Verification: amount is now ${verified_amount}")
            
            return {
                "success": True,
                "message": f"Card amount updated to ${new_amount}",
                "data": {
                    "card_id": actual_card_id,
                    "amount": new_amount,
                    "verified_amount": verified_amount
                }
            }
        else:
            print(f"❌ Failed to verify update for card: {actual_card_id}")
            return {"success": False, "error": "Failed to verify update"}
        
    except Exception as e:
        print(f"❌ Update card amount error: {e}")
        import traceback
        traceback.print_exc()
        return {"success": False, "error": str(e)}    
@app.post("/api/v1/mt4/candles")
async def get_mt4_candles(request: Request):
    """Get real candle data from MT4"""
    try:
        data = await request.json()
        symbol = data.get('symbol', 'EURUSD')
        timeframe = data.get('timeframe', '5m')
        count = data.get('count', 100)
        
        # Map timeframe to minutes
        tf_map = {
            '1m': 1, '5m': 5, '15m': 15, '30m': 30,
            '1h': 60, '4h': 240, '1d': 1440
        }
        
        # ✅ Try to get real candles from MT4
        try:
            from src.mt4_gateway.mt4_bridge import MT4Bridge
            bridge = MT4Bridge()
            candles = bridge.get_candles(symbol, tf_map.get(timeframe, 5), count)
            if candles and len(candles) > 0:
                return {
                    "success": True,
                    "candles": candles,
                    "symbol": symbol,
                    "timeframe": timeframe,
                    "count": len(candles),
                    "source": "mt4_bridge"
                }
        except Exception as e:
            print(f"⚠️ MT4 bridge error: {e}")
        
        # ✅ Fallback: Read from dashboard file
        import json
        import os
        DASHBOARD_FILE = "C:/Users/sifer/AppData/Roaming/MetaQuotes/Terminal/Common/Files/dashboard_data.json"
        
        if os.path.exists(DASHBOARD_FILE):
            with open(DASHBOARD_FILE, 'r') as f:
                dashboard_data = json.load(f)
                if 'candles' in dashboard_data and symbol in dashboard_data['candles']:
                    candles = dashboard_data['candles'][symbol].get(timeframe, [])
                    if candles:
                        return {
                            "success": True,
                            "candles": candles[-count:],
                            "symbol": symbol,
                            "timeframe": timeframe,
                            "count": len(candles),
                            "source": "dashboard_file"
                        }
        
        # ✅ Use the current price to generate realistic candles
        current_price = get_current_mt4_price(symbol)
        if current_price and current_price > 0:
            candles = generate_candles_from_price(symbol, current_price, count, tf_map.get(timeframe, 5))
            return {
                "success": True,
                "candles": candles,
                "symbol": symbol,
                "timeframe": timeframe,
                "count": len(candles),
                "source": "generated_from_price"
            }
        
        # ✅ FINAL FALLBACK: Use the improved generate_sample_candles
        sample_candles = generate_sample_candles(symbol, count)
        return {
            "success": True,
            "candles": sample_candles,
            "symbol": symbol,
            "timeframe": timeframe,
            "count": len(sample_candles),
            "source": "generated"
        }
        
    except Exception as e:
        return {
            "success": False,
            "error": str(e),
            "candles": []
        }
def get_current_mt4_price(symbol):
    """Get current price from MT4"""
    try:
        from src.mt4_gateway.mt4_bridge import MT4Bridge
        bridge = MT4Bridge()
        return bridge.get_price(symbol)
    except:
        return None

def generate_candles_from_price(symbol, current_price, count, timeframe_minutes):
    """Generate candles that end at the current price"""
    import random
    from datetime import datetime, timedelta
    
    candles = []
    price = current_price * (1 - random.uniform(-0.005, 0.005))
    
    for i in range(count):
        time = datetime.now() - timedelta(minutes=(count - i) * timeframe_minutes)
        change = (random.random() - 0.5) * 0.002
        open_price = price
        close_price = open_price + change
        high = max(open_price, close_price) + random.random() * 0.001
        low = min(open_price, close_price) - random.random() * 0.001
        
        candles.append({
            'time': int(time.timestamp()),
            'open': round(open_price, 5),
            'high': round(high, 5),
            'low': round(low, 5),
            'close': round(close_price, 5),
            'volume': random.randint(100, 1000)
        })
        
        price = close_price
    
    # ✅ Make sure the last candle ends at the current price
    if candles:
        candles[-1]['close'] = current_price
        candles[-1]['high'] = max(candles[-1]['high'], current_price)
        candles[-1]['low'] = min(candles[-1]['low'], current_price)
    
    return candles

def generate_sample_candles(symbol: str, count: int = 100) -> list:
    """Generate sample candles for fallback with realistic price movement for ALL symbols"""
    import random
    from datetime import datetime, timedelta
    
    # ✅ CORRECT base prices for each symbol type
    base_prices = {
        '#NASDAQ100': 27958.24,
        '#DJ30': 52976.00,
        '#S&P500': 7468.74,
        '#RUSS2000': 2961.52,
        '#CAC40': 8475.50,
        '#DAX40': 25585.00,
        '#FTSE100': 10877.50,
        '#NIKKEI225': 62692.00,
        'EURUSD': 0.85643,
        'GBPUSD': 1.33899,
        'USDJPY': 162.449,
        'USDCHF': 0.8950,
        'AUDUSD': 0.6725,
        'USDCAD': 1.3652,
        'NZDUSD': 0.6123,
        'EURGBP': 0.8520,
        'EURJPY': 185.620,
        'EURCAD': 1.5600,
        'EURNZD': 1.8650,
        'EURCHF': 0.9540,
        'GOLD': 4034.38,
        'SILVER': 31.25,
        'BRENT_OIL': 85.40,
        'CrudeOIL': 82.02
    }
    
    base_price = base_prices.get(symbol, 100)
    
    # ✅ Determine precision and volatility based on symbol type
    if symbol.startswith('#'):
        # Indices - 2 decimals, higher volatility
        precision = 2
        volatility = 0.006
        min_move = 0.1
    elif symbol in ['GOLD', 'SILVER', 'BRENT_OIL', 'CrudeOIL']:
        # Metals & Energy - 2 decimals
        precision = 2
        volatility = 0.003
        min_move = 0.01
    elif symbol in ['USDJPY', 'EURJPY']:
        # JPY pairs - 3 decimals
        precision = 3
        volatility = 0.001
        min_move = 0.001
    else:
        # Forex - 5 decimals
        precision = 5
        volatility = 0.0005
        min_move = 0.00001
    
    candles = []
    price = base_price * 0.98  # Start slightly below
    trend_dir = 1 if random.random() > 0.5 else -1
    
    for i in range(count):
        time = datetime.now() - timedelta(minutes=(count - i) * 5)
        
        # ✅ Change trend direction occasionally
        if i % 12 == 0:
            trend_dir = 1 if random.random() > 0.5 else -1
        
        # ✅ Generate realistic price movement
        trend = trend_dir * volatility * price * 0.3
        noise = (random.random() - 0.5) * volatility * price * 0.7
        change = trend + noise
        
        open_price = price
        close_price = price + change
        
        # ✅ Proper high/low with wicks
        high = max(open_price, close_price) + abs(noise) * 0.4 + random.random() * volatility * price * 0.1
        low = min(open_price, close_price) - abs(noise) * 0.4 - random.random() * volatility * price * 0.1
        
        candles.append({
            'time': int(time.timestamp()),
            'open': round(open_price, precision),
            'high': round(high, precision),
            'low': round(low, precision),
            'close': round(close_price, precision),
            'volume': random.randint(50, 950)
        })
        
        price = close_price
    
    # ✅ Ensure last candle ends at base price
    if candles:
        last = candles[-1]
        diff = base_price - last['close']
        adjustment = diff / count
        for i, c in enumerate(candles):
            adj = adjustment * (i + 1)
            c['open'] = round(c['open'] + adj, precision)
            c['high'] = round(c['high'] + adj + random.random() * volatility * base_price * 0.05, precision)
            c['low'] = round(c['low'] + adj - random.random() * volatility * base_price * 0.05, precision)
            c['close'] = round(c['close'] + adj, precision)
        candles[-1]['close'] = round(base_price, precision)
        candles[-1]['high'] = max(candles[-1]['high'], candles[-1]['close'])
        candles[-1]['low'] = min(candles[-1]['low'], candles[-1]['close'])
    
    return candles

# In src/api/main.py
@app.get("/api/v1/mt4/prices")
async def get_mt4_prices():
    """Get real MT4 prices from dashboard file"""
    import json
    import os
    from datetime import datetime
    
    # ✅ USE THE CORRECT PATH
    DASHBOARD_FILE = "C:/Users/sifer/AppData/Roaming/MetaQuotes/Terminal/Common/Files/dashboard_data.json"
    
    try:
        if os.path.exists(DASHBOARD_FILE):
            with open(DASHBOARD_FILE, 'r', encoding='utf-8') as f:
                data = json.load(f)
                prices = {}
                
                # Try different data structures
                if 'prices' in data:
                    prices = data['prices']
                elif 'data' in data and 'prices' in data['data']:
                    prices = data['data']['prices']
                elif 'forex' in data:
                    for category in ['forex', 'indices', 'metals', 'energy']:
                        if category in data:
                            prices.update(data[category])
                
                if prices:
                    return {
                        "success": True,
                        "prices": prices,
                        "timestamp": datetime.now().isoformat()
                    }
        
        return {
            "success": False,
            "error": "Dashboard file not found or empty",
            "prices": {}
        }
    except Exception as e:
        return {
            "success": False,
            "error": str(e),
            "prices": {}
        }
@app.get("/api/v1/client/balance")
async def client_balance(request: Request):
    """Get client balance - simplified endpoint"""
    try:
        # Get token from header
        auth_header = request.headers.get('Authorization')
        if not auth_header or not auth_header.startswith('Bearer '):
            return JSONResponse(
                status_code=401,
                content={"success": False, "error": "Unauthorized"}
            )
        
        # For now, return a default balance
        # You can replace this with actual database logic
        return {
            "success": True,
            "balance": {
                "balance": 103.14,
                "equity": 103.14,
                "margin": 0,
                "free_margin": 103.14
            }
        }
    except Exception as e:
        return {
            "success": False,
            "error": str(e)
        }
# 1. WebSocket endpoint (BEFORE static files)
@app.websocket("/ws/prices/{client_id}")
async def websocket_prices(websocket: WebSocket, client_id: str):
    """WebSocket endpoint for real-time prices"""
    # Start manager if not running
    if not ws_manager._running:
        await ws_manager.start()
    
    try:
        connected = await ws_manager.connect(websocket, client_id)
        if not connected:
            return
        
        while True:
            try:
                message = await websocket.receive_text()
                await ws_manager.handle_message(websocket, message, client_id)
            except WebSocketDisconnect:
                break
            except Exception as e:
                logger.error(f"WebSocket error for {client_id}: {e}")
                break
                
    except WebSocketDisconnect:
        pass
    except Exception as e:
        logger.error(f"WebSocket connection error: {e}")
    finally:
        ws_manager.disconnect(websocket, client_id)
@app.websocket("/ws/forex/{client_id}")
async def websocket_forex(websocket: WebSocket, client_id: str):
    """WebSocket endpoint for real-time forex prices from forex_dashboard"""
    await websocket.accept()
    
    try:
        from forex_dashboard import get_all_prices, get_account_info
        
        while True:
            try:
                # Get prices from forex_dashboard
                prices = get_all_prices()
                account = get_account_info()
                
                if prices:
                    await websocket.send_json({
                        'type': 'price_update',
                        'data': prices,
                        'timestamp': datetime.now().isoformat()
                    })
                
                if account:
                    await websocket.send_json({
                        'type': 'account_update',
                        'data': account,
                        'timestamp': datetime.now().isoformat()
                    })
                
                await asyncio.sleep(1)
                
            except WebSocketDisconnect:
                break
            except Exception as e:
                logger.error(f"Forex WS error: {e}")
                await asyncio.sleep(1)
                
    except WebSocketDisconnect:
        pass
    except Exception as e:
        logger.error(f"WebSocket error: {e}")
# 2. WebSocket HTTP endpoints (BEFORE static files)
# src/api/main.py - Add this endpoint

# Then update the WebSocket endpoint
@app.websocket("/ws/forex/direct/{client_id}")
async def websocket_forex_direct(websocket: WebSocket, client_id: str):
    """Direct WebSocket endpoint for real-time forex prices from dashboard file"""
    try:
        await forex_ws_manager.connect(websocket)
        
        while True:
            try:
                message = await websocket.receive_text()
                
                if message == 'ping':
                    await websocket.send_text('pong')
                elif message == 'get_prices':
                    # ✅ Use the imported function
                    data = read_dashboard_file()
                    await websocket.send_json({
                        'type': 'price_response',
                        'data': data.get('prices', {}),
                        'account': data.get('account', {}),
                        'timestamp': datetime.now().isoformat()
                    })
                    
            except WebSocketDisconnect:
                break
            except Exception as e:
                logger.error(f"WebSocket error: {e}")
                break
                
    except WebSocketDisconnect:
        pass
    finally:
        forex_ws_manager.disconnect(websocket)
@app.get("/ws/status")
async def ws_status():
    """Get WebSocket status"""
    return {
        "success": True,
        "connected_clients": len(ws_manager.active_connections),
        "price_count": len(ws_manager.prices),
        "running": ws_manager._running,
        "update_counter": ws_manager._update_counter,
        "timestamp": datetime.now().isoformat()
    }

@app.get("/ws/test")
async def ws_test():
    """Test if WebSocket is working"""
    return {
        "success": True,
        "message": "WebSocket is working!",
        "endpoint": "/ws/prices/{client_id}",
        "status": "/ws/status",
        "prices": "/ws/prices",
        "running": ws_manager._running,
        "price_count": len(ws_manager.prices),
        "connected_clients": len(ws_manager.active_connections)
    }

@app.get("/ws/prices")
async def ws_get_prices():
    """Get current prices"""
    return {
        "success": True,
        "prices": ws_manager.prices,
        "timestamp": datetime.now().isoformat(),
        "symbols": len(ws_manager.prices)
    }

@app.post("/ws/update")
async def ws_update_prices():
    """Force update prices (for testing)"""
    import random
    for symbol in ws_manager.prices:
        if symbol in ['EURUSD', 'GBPUSD', 'USDJPY']:
            change = random.uniform(-0.001, 0.001)
            ws_manager.prices[symbol] = round(ws_manager.prices[symbol] + change, 5)
        elif symbol in ['#NASDAQ100', '#DJ30', '#S&P500']:
            change = random.uniform(-5, 5)
            ws_manager.prices[symbol] = round(ws_manager.prices[symbol] + change, 2)
        elif symbol == 'GOLD':
            change = random.uniform(-2, 2)
            ws_manager.prices[symbol] = round(ws_manager.prices[symbol] + change, 2)
        elif symbol == 'SILVER':
            change = random.uniform(-0.2, 0.2)
            ws_manager.prices[symbol] = round(ws_manager.prices[symbol] + change, 2)
    return {
        "success": True,
        "prices": ws_manager.prices,
        "timestamp": datetime.now().isoformat()
    }

# ============================================================
# CREATE API ROUTER
# ============================================================

api_router = APIRouter(prefix="/api/v1")

# ============================================================
# IMPORT ROUTERS (ONCE!)
# ============================================================

routers_loaded = {}

# 1. Auth Router
try:
    from src.api.routes.auth import router as auth_router
    routers_loaded['auth'] = auth_router
    print("✅ Auth routes loaded")
except ImportError as e:
    print(f"⚠️ Auth routes not available: {e}")
    from fastapi import APIRouter
    routers_loaded['auth'] = APIRouter()

# 2. Signals Router
try:
    from src.api.routes.signals import router as signals_router
    routers_loaded['signals'] = signals_router
    print("✅ Signals routes loaded")
except ImportError as e:
    print(f"⚠️ Signals routes not available: {e}")
    routers_loaded['signals'] = APIRouter()

# 3. Trades Router
try:
    from src.api.routes.trades import router as trades_router
    routers_loaded['trades'] = trades_router
    print("✅ Trades routes loaded")
except ImportError as e:
    print(f"⚠️ Trades routes not available: {e}")
    from fastapi import APIRouter
    routers_loaded['trades'] = APIRouter()

# 4. Dashboard Router
try:
    from src.api.routes.dashboard_bridge import router as dashboard_bridge_router
    routers_loaded['dashboard'] = dashboard_bridge_router
    print("✅ Dashboard routes loaded")
except ImportError as e:
    print(f"⚠️ Dashboard routes not available: {e}")
    from fastapi import APIRouter
    routers_loaded['dashboard'] = APIRouter()

# 5. Controllers Router
try:
    from src.api.routes.controllers import router as controllers_router
    routers_loaded['controllers'] = controllers_router
    print("✅ Controllers routes loaded")
except ImportError as e:
    print(f"⚠️ Controllers routes not available: {e}")
    from fastapi import APIRouter
    routers_loaded['controllers'] = APIRouter()

# 6. Client Auth Router
try:
    from src.api.routes.client_auth import router as client_auth_router
    routers_loaded['client_auth'] = client_auth_router
    print("✅ Client Auth routes loaded")
except ImportError as e:
    print(f"⚠️ Client Auth routes not available: {e}")
    from fastapi import APIRouter
    routers_loaded['client_auth'] = APIRouter()

# 7. Client Cards Router
try:
    from src.api.routes.cards import router as client_cards_router
    routers_loaded['client_cards'] = client_cards_router
    print("✅ Client Cards routes loaded")
except ImportError as e:
    print(f"⚠️ Client Cards routes not available: {e}")
    from fastapi import APIRouter
    routers_loaded['client_cards'] = APIRouter()

# 8. Master Auth Router
try:
    from src.api.routes.master_auth import router as master_auth_router
    routers_loaded['master_auth'] = master_auth_router
    print("✅ Master Auth routes loaded")
except ImportError as e:
    print(f"⚠️ Master Auth routes not available: {e}")
    routers_loaded['master_auth'] = APIRouter()

# 9. Client Trades Router
try:
    from src.api.routes.client_trades import router as client_trades_router
    routers_loaded['client_trades'] = client_trades_router
    print("✅ Client Trades routes loaded")
except ImportError as e:
    print(f"⚠️ Client Trades routes not available: {e}")
    from fastapi import APIRouter
    routers_loaded['client_trades'] = APIRouter()

# 10. Master Router
try:
    from src.api.routes.master import router as master_router
    routers_loaded['master'] = master_router
    print("✅ Master routes loaded")
except ImportError as e:
    print(f"⚠️ Master routes not available: {e}")
    from fastapi import APIRouter
    routers_loaded['master'] = APIRouter()

# 11. Spread Router
try:
    from src.api.routes.spread_routes import router as spread_router
    routers_loaded['spread'] = spread_router
    print("✅ Spread routes loaded")
except ImportError as e:
    print(f"⚠️ Spread routes not available: {e}")
    from fastapi import APIRouter
    routers_loaded['spread'] = APIRouter()

# 12. WebSocket Router (from external file - optional)
try:
    from src.api.websocket_manager import router as websocket_router
    routers_loaded['websocket'] = websocket_router
    print("✅ External WebSocket routes loaded")
except ImportError as e:
    print(f"⚠️ External WebSocket routes not available: {e}")
    routers_loaded['websocket'] = APIRouter()

# ============================================================
# REGISTER ROUTERS
# ============================================================

# Register all routers
api_router.include_router(routers_loaded['auth'], prefix="/auth", tags=["Authentication"])
api_router.include_router(routers_loaded['signals'], prefix="/signals", tags=["Signals"])
api_router.include_router(routers_loaded['trades'], prefix="/trades", tags=["Trades"])
api_router.include_router(routers_loaded['dashboard'], prefix="/dashboard", tags=["Dashboard"])
api_router.include_router(routers_loaded['controllers'], prefix="/controllers", tags=["Controllers"])
api_router.include_router(routers_loaded['client_auth'], prefix="/client", tags=["Client Auth"])
api_router.include_router(routers_loaded['client_cards'], prefix="/client", tags=["Client Cards"])
api_router.include_router(routers_loaded['client_trades'], prefix="/client", tags=["Client Trading"])
api_router.include_router(routers_loaded['master_auth'], prefix="/master", tags=["Master Auth"])
api_router.include_router(routers_loaded['master'], prefix="/master", tags=["Master"])
api_router.include_router(routers_loaded['spread'], prefix="/spreads", tags=["Spreads"])
# Don't register websocket_router here as we already have direct WebSocket endpoints

# Register the API router with the app
app.include_router(api_router)
app.include_router(routers_loaded['spread'], prefix="/api/v1", tags=["Spread"])

# Add compatibility mounts for the dashboard/tests that call /signals directly
try:
    signals_router = routers_loaded.get('signals')
    if signals_router:
        app.include_router(signals_router, prefix="/signals", tags=["Signals"])
        app.include_router(signals_router, prefix="/client/signals", tags=["Signals"])
        print("✅ Root signals compatibility routes registered")
except Exception as e:
    print(f"⚠️ Root signals compatibility routes not available: {e}")

# ============================================================
# STARTUP EVENT
# ============================================================
# src/api/main.py - Update these functions

@app.on_event("startup")
async def startup_event():
    """Start WebSocket managers on startup"""
    logger.info("🚀 Starting WebSocket managers...")
    await ws_manager.start()
    await forex_ws_manager.start()  # ← ADD THIS
    logger.info("✅ All WebSocket managers started")

@app.on_event("shutdown")
async def shutdown_event():
    """Stop WebSocket managers on shutdown"""
    logger.info("🛑 Stopping WebSocket managers...")
    ws_manager.stop()
    await forex_ws_manager.stop()  # ← ADD THIS
    logger.info("✅ All WebSocket managers stopped")
# ============================================================
# SERVE STATIC FILES
# ============================================================

# Try multiple possible paths for the web directory
web_paths = [
    Path(__file__).parent.parent / "web",  # src/web
    Path(__file__).parent.parent.parent / "src" / "web",  # trading_copy/src/web
    Path(__file__).parent.parent.parent / "web",  # trading_copy/web
]

web_path = None
for path in web_paths:
    if path.exists():
        web_path = path
        break

if web_path:
    # ⚠️ IMPORTANT: Static files must be mounted LAST
    # Use a different path prefix to avoid conflicts
    app.mount("/static", StaticFiles(directory=str(web_path)), name="static")
    
    # For root path, we need to handle it carefully
    # Don't mount directly on "/" as it will intercept all routes
    
    # Instead, serve index.html at root
    @app.get("/")
    async def serve_index():
        from fastapi.responses import FileResponse
        index_path = web_path / "index.html"
        if index_path.exists():
            return FileResponse(index_path)
        return {"message": "Trading Platform API", "status": "running"}
    
    # Also serve other HTML files
    @app.get("/{filename:path}")
    async def serve_static_files(filename: str):
        from fastapi.responses import FileResponse
        # Skip API routes that might be caught here
        if filename.startswith("api/") or filename.startswith("ws/"):
            raise HTTPException(status_code=404)
        
        file_path = web_path / filename
        if file_path.exists() and file_path.is_file():
            return FileResponse(file_path)
        raise HTTPException(status_code=404)
    
    print(f"✅ Serving static files from: {web_path}")
else:
    print(f"⚠️ Web directory not found. Tried: {web_paths}")
# Add middleware to disable static file caching for HTML pages
class NoCacheStaticMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request, call_next):
        response = await call_next(request)
        if request.url.path.endswith('.html'):
            response.headers['Cache-Control'] = 'no-cache, no-store, must-revalidate'
            response.headers['Pragma'] = 'no-cache'
            response.headers['Expires'] = '0'
        return response

app.add_middleware(NoCacheStaticMiddleware)

# ============================================================
# BASIC ENDPOINTS
# ============================================================

@app.get("/")
async def root():
    return {
        "name": "Trading Platform API",
        "version": "1.0.0",
        "status": "online",
        "timestamp": datetime.now().isoformat(),
        "websocket": {
            "endpoint": "/ws/prices/{client_id}",
            "status": "/ws/status",
            "prices": "/ws/prices",
            "connected_clients": len(ws_manager.active_connections)
        },
        "endpoints": {
            "health": "/health",
            "docs": "/docs",
            "client_login": "/client_login.html",
            "client_dashboard": "/client_dashboard.html",
            "master_login": "/master_login.html",
            "master_dashboard": "/master_dashboard.html"
        }
    }

@app.get("/health")
async def health_check():
    return {
        "status": "healthy",
        "message": "API is running",
        "timestamp": datetime.now().isoformat()
    }

@app.get("/ping")
async def ping():
    return {
        "pong": "API is responsive!",
        "timestamp": datetime.now().isoformat()
    }

@app.exception_handler(Exception)
async def global_exception_handler(request, exc):
    logger.error(f"Global error: {exc}")
    return JSONResponse(
        status_code=500,
        content={
            "error": "Internal Server Error",
            "detail": str(exc),
            "timestamp": datetime.now().isoformat()
        }
    )

# ============================================================
# RUN
# ============================================================

if __name__ == "__main__":
    uvicorn.run("src.api.main:app", host="127.0.0.1", port=8000, reload=True)