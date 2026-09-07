# src/api/websocket_forex.py - NO FALLBACK, ONLY REAL DATA

import asyncio
import json
import os
import time
from datetime import datetime
from fastapi import WebSocket, WebSocketDisconnect
import logging

logger = logging.getLogger(__name__)

# ============ FILE PATHS ============
COMMON_FILES = "C:/Users/sifer/AppData/Roaming/MetaQuotes/Terminal/Common/Files/"
MT4_FILES_PATH = "C:/Users/sifer/AppData/Roaming/MetaQuotes/Terminal/50CA3DFB510CC5A8F28B48D1BF2A5702/MQL4/Files/"

DASHBOARD_FILE_PATHS = [
    os.path.join(COMMON_FILES, "dashboard_data.json"),
    os.path.join(MT4_FILES_PATH, "dashboard_data.json")
]

# Forex pairs only
FOREX_PAIRS = [
    'EURUSD', 'GBPUSD', 'USDJPY', 'USDCHF', 'AUDUSD', 'USDCAD', 'NZDUSD',
    'EURGBP', 'EURJPY', 'EURCAD', 'EURNZD', 'EURCHF'
]

# Cache - start empty, NO FALLBACK
last_file_content = {
    'prices': {},
    'account': {'balance': 0, 'equity': 0, 'margin': 0, 'free_margin': 0},
    'stats': {}
}
last_file_mtime = 0
last_read_time = 0
min_read_interval = 0.5  # 500ms


def read_dashboard_file():
    """Read dashboard file - NO FALLBACK, only real data"""
    global last_file_content, last_file_mtime, last_read_time
    
    now = time.time()
    
    # Rate limit
    if now - last_read_time < min_read_interval:
        return last_file_content
    
    for file_path in DASHBOARD_FILE_PATHS:
        if os.path.exists(file_path):
            try:
                # Check if file changed
                mtime = os.path.getmtime(file_path)
                if mtime == last_file_mtime and last_file_content:
                    last_read_time = now
                    return last_file_content
                
                with open(file_path, 'r') as f:
                    data = json.load(f)
                
                prices = {}
                
                # ONLY get prices from 'prices' key - NO FALLBACK
                if 'prices' in data and data['prices']:
                    for symbol, price in data['prices'].items():
                        if isinstance(price, dict):
                            price = price.get('price', 0)
                        if price and float(price) > 0:
                            prices[symbol] = float(price)
                
                # Also check direct keys for forex pairs (but ONLY if they exist)
                for pair in FOREX_PAIRS:
                    if pair not in prices and pair in data:
                        price = data[pair]
                        if isinstance(price, dict):
                            price = price.get('price', 0)
                        if price and float(price) > 0:
                            prices[pair] = float(price)
                
                # Get account info - ONLY from file, NO FALLBACK
                account = {}
                if 'balance' in data:
                    account['balance'] = float(data.get('balance', 0))
                if 'equity' in data:
                    account['equity'] = float(data.get('equity', 0))
                if 'margin' in data:
                    account['margin'] = float(data.get('margin', 0))
                if 'free_margin' in data:
                    account['free_margin'] = float(data.get('free_margin', 0))
                
                # Get stats - ONLY from file
                stats = {}
                if 'total_trades' in data:
                    stats['total_trades'] = int(data.get('total_trades', 0))
                if 'win_rate' in data:
                    stats['win_rate'] = float(data.get('win_rate', 0))
                if 'total_pnl' in data:
                    stats['total_pnl'] = float(data.get('total_pnl', 0))
                if 'profit_factor' in data:
                    stats['profit_factor'] = float(data.get('profit_factor', 0))
                
                # Only update if we actually found prices
                if prices:
                    last_file_content = {
                        'prices': prices,
                        'account': account,
                        'stats': stats,
                        'timestamp': datetime.now().isoformat(),
                        'file_path': file_path,
                        'file_mtime': mtime,
                        'has_data': True
                    }
                    last_file_mtime = mtime
                    last_read_time = now
                    
                    logger.debug(f"✅ Read {len(prices)} prices from file")
                    return last_file_content
                else:
                    # File exists but no prices - return empty (NO FALLBACK)
                    logger.warning(f"⚠️ No prices found in {file_path}")
                    return {
                        'prices': {},
                        'account': {},
                        'stats': {},
                        'timestamp': datetime.now().isoformat(),
                        'has_data': False
                    }
                
            except Exception as e:
                logger.error(f"Error reading dashboard file: {e}")
                continue
    
    # NO FALLBACK - return empty dict
    logger.warning("⚠️ No dashboard file found - returning empty data")
    return {
        'prices': {},
        'account': {},
        'stats': {},
        'timestamp': datetime.now().isoformat(),
        'has_data': False
    }


class ForexWebSocketManager:
    def __init__(self):
        self.active_connections = []
        self.is_running = False
        self.broadcast_task = None
        
    async def start(self):
        if self.is_running:
            return
        self.is_running = True
        self.broadcast_task = asyncio.create_task(self._broadcast_loop())
        logger.info("✅ Forex WebSocket started")
    
    async def stop(self):
        self.is_running = False
        if self.broadcast_task:
            self.broadcast_task.cancel()
        logger.info("⏹️ Forex WebSocket stopped")
    
    async def _broadcast_loop(self):
        """Broadcast price updates every 500ms"""
        while self.is_running:
            try:
                if self.active_connections:
                    data = read_dashboard_file()
                    
                    # Only send if we have data
                    if data and data.get('prices'):
                        message = {
                            'type': 'price_update',
                            'data': data['prices'],
                            'account': data.get('account', {}),
                            'stats': data.get('stats', {}),
                            'timestamp': data.get('timestamp', datetime.now().isoformat()),
                            'has_data': True
                        }
                        
                        # Broadcast to all clients
                        disconnected = []
                        for ws in self.active_connections:
                            try:
                                await ws.send_json(message)
                            except:
                                disconnected.append(ws)
                        
                        for ws in disconnected:
                            if ws in self.active_connections:
                                self.active_connections.remove(ws)
                
                await asyncio.sleep(0.5)
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Broadcast error: {e}")
                await asyncio.sleep(1)
    
    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)
        logger.info(f"✅ Forex WebSocket connected (Total: {len(self.active_connections)})")
        
        # Send initial data - NO FALLBACK
        data = read_dashboard_file()
        await websocket.send_json({
            'type': 'connected',
            'data': data.get('prices', {}),
            'account': data.get('account', {}),
            'stats': data.get('stats', {}),
            'timestamp': datetime.now().isoformat(),
            'has_data': data.get('has_data', False)
        })
        
        return len(self.active_connections)
    
    def disconnect(self, websocket: WebSocket):
        if websocket in self.active_connections:
            self.active_connections.remove(websocket)
        logger.info(f"❌ Forex WebSocket disconnected (Total: {len(self.active_connections)})")


# Singleton
forex_ws_manager = ForexWebSocketManager()