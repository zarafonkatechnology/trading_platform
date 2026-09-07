"""
UNIFIED TRADING CONTROLLER - WebSocket Real-Time Version
"""

import sys
import os
import logging
import time
import json
import threading
from datetime import datetime
from typing import Dict
import socketio

# Add current directory to path
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

# Import core modules
from core.price_service import price_service
from core.risk_manager import RiskManager
from core.signal_service import signal_service

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class WebSocketClient:
    """WebSocket client to receive real-time prices"""
    
    def __init__(self, url='http://localhost:5002'):
        self.url = url
        self.sio = socketio.Client()
        self.prices = {}
        self.balance = 0
        self.equity = 0
        self.timestamp = ''
        self.connected = False
        self._setup_handlers()
    
    def _setup_handlers(self):
        @self.sio.event
        def connect():
            self.connected = True
            logger.info('✅ Connected to WebSocket server')
        
        @self.sio.event
        def disconnect():
            self.connected = False
            logger.warning('⚠️ Disconnected from WebSocket server')
        
        @self.sio.event
        def price_update(data):
            self.prices = data.get('prices', {})
            self.balance = data.get('balance', 0)
            self.equity = data.get('equity', 0)
            self.timestamp = data.get('timestamp', '')
            
            # Also update price_service
            for symbol, price in self.prices.items():
                if price > 0:
                    # Update the internal cache
                    price_service._prices[symbol] = price
    
    def connect(self):
        try:
            self.sio.connect(self.url)
            return True
        except Exception as e:
            logger.error(f'WebSocket connection failed: {e}')
            return False
    
    def disconnect(self):
        if self.connected:
            self.sio.disconnect()
    
    def get_price(self, symbol: str) -> float:
        return self.prices.get(symbol, 0)
    
    def get_all_prices(self) -> Dict:
        return self.prices.copy()


class UnifiedTradingControllerWS:
    """Unified Controller with WebSocket Real-Time Updates"""
    
    def __init__(self, config: Dict = None):
        self.config = config or {}
        
        # WebSocket client
        self.ws = WebSocketClient()
        self.ws_connected = self.ws.connect()
        
        if not self.ws_connected:
            logger.warning('⚠️ WebSocket not connected - using file polling fallback')
        
        # Risk Manager
        self.risk_manager = RiskManager(self.config)
        
        # State
        self.is_running = False
        self.cycle_count = 0
        self.cycle_interval = self.config.get('cycle_interval', 2)  # 2 seconds with WebSocket
        self.all_symbols = price_service.all_symbols
        self.active_positions = {}
        
        # Signal history
        self.signals = {}
        
        logger.info('=' * 60)
        logger.info('🚀 UNIFIED TRADING CONTROLLER (WebSocket)')
        logger.info('=' * 60)
        logger.info(f'   Total Symbols: {len(self.all_symbols)}')
        logger.info(f'   WebSocket: {"✅ Connected" if self.ws_connected else "❌ Using fallback"}')
        logger.info(f'   Cycle: {self.cycle_interval}s')
        logger.info('=' * 60)
    
    def get_signal(self, symbol: str) -> Dict:
        """Get signal with real-time price"""
        # Get price from WebSocket or fallback
        price = self.ws.get_price(symbol)
        if price <= 0:
            price = price_service.get_price(symbol)
        
        # Determine if this is Z-Score or Engine symbol
        if symbol in price_service.forex_pairs or symbol in price_service.dollar:
            source = 'ENGINE'
        else:
            source = 'ZSCORE'
        
        # For now, just HOLD
        return {
            'action': 'HOLD',
            'confidence': 50,
            'price': price,
            'source': source,
            'symbol': symbol,
            'timestamp': datetime.now().isoformat()
        }
    
    def process_cycle(self) -> Dict:
        """Process one cycle with real-time data"""
        self.cycle_count += 1
        
        results = {
            'cycle': self.cycle_count,
            'timestamp': datetime.now().isoformat(),
            'signals': {},
            'active_positions': len(self.active_positions)
        }
        
        # Log cycle start
        logger.info(f'\n🔄 CYCLE {self.cycle_count} - {datetime.now().strftime("%H:%M:%S")}')
        logger.info(f'   WebSocket Status: {"✅ Connected" if self.ws.connected else "❌ Disconnected"}')
        
        # Process each symbol
        for symbol in self.all_symbols:
            if symbol in self.active_positions:
                continue
            
            # Get signal
            signal = self.get_signal(symbol)
            results['signals'][symbol] = signal
            
            price = signal.get('price', 0)
            action = signal.get('action', 'HOLD')
            confidence = signal.get('confidence', 0)
            
            if price > 0:
                logger.info(f'📊 {symbol}: {action} ({confidence:.0f}%) @ {price:.5f}')
            else:
                logger.info(f'📊 {symbol}: {action} ({confidence:.0f}%) - NO PRICE')
        
        # Log summary
        logger.info(f'\n📊 Summary:')
        logger.info(f'   Total Symbols: {len(self.all_symbols)}')
        logger.info(f'   Active Positions: {len(self.active_positions)}')
        logger.info(f'   WebSocket: {"✅" if self.ws.connected else "❌"}')
        
        return results
    
    def run(self):
        """Main loop"""
        self.is_running = True
        logger.info('🚀 Starting WebSocket Trading Controller...')
        
        try:
            while self.is_running:
                self.process_cycle()
                time.sleep(self.cycle_interval)
        except KeyboardInterrupt:
            self.stop()
        finally:
            self.ws.disconnect()
    
    def stop(self):
        self.is_running = False
        logger.info('✅ Stopped')


if __name__ == '__main__':
    print('\n' + '=' * 60)
    print('🚀 UNIFIED TRADING CONTROLLER (WebSocket)')
    print('=' * 60)
    
    config = {
        'cycle_interval': 2,  # 2 seconds with WebSocket
        'daily_loss_limit': 100,
        'max_positions': 3,
        'cold_start_threshold': 50,
        'cold_start_min_win_rate': 0.4
    }
    
    controller = UnifiedTradingControllerWS(config)
    print('\n✅ Controller ready. Starting...\n')
    
    try:
        controller.run()
    except KeyboardInterrupt:
        print('\n🛑 Stopped by user')
    finally:
        controller.stop()