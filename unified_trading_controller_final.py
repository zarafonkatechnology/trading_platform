# unified_trading_controller_final.py
"""
UNIFIED TRADING CONTROLLER - Uses WebSocket from forex_dashboard.py
Connects to forex_dashboard.py WebSocket for real-time prices
"""

import sys
import os
import logging
import time
import threading
from datetime import datetime
from typing import Dict

# Add current directory to path
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

# Import core modules
from core.price_service import price_service
from core.risk_manager import RiskManager
from core.signal_service import signal_service

# Import WebSocket client
try:
    from websocket_client import ForexDashboardClient
    WS_AVAILABLE = True
except ImportError:
    WS_AVAILABLE = False
    print("❌ websocket_client.py not found")
    print("   Create websocket_client.py first")

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class UnifiedTradingController:
    """
    Unified Trading Controller that connects to forex_dashboard.py WebSocket
    for real-time price updates
    """
    
    def __init__(self, config: Dict = None):
        self.config = config or {}
        
        # Initialize WebSocket client
        self.ws = None
        self.ws_connected = False
        self._init_websocket()
        
        # Risk Manager
        self.risk_manager = RiskManager(self.config)
        
        # State
        self.is_running = False
        self.cycle_count = 0
        self.cycle_interval = self.config.get('cycle_interval', 2)
        self.all_symbols = price_service.all_symbols
        self.active_positions = {}
        self.signals = {}
        
        # Fallback polling if WebSocket fails
        self.use_fallback = not self.ws_connected
        self.fallback_prices = {}
        
        logger.info('=' * 60)
        logger.info('🚀 UNIFIED TRADING CONTROLLER (WebSocket)')
        logger.info('=' * 60)
        logger.info(f'   Total Symbols: {len(self.all_symbols)}')
        logger.info(f'   WebSocket: {"✅ Connected to forex_dashboard" if self.ws_connected else "❌ Using fallback"}')
        logger.info(f'   Cycle: {self.cycle_interval}s')
        logger.info('=' * 60)
        
        # Print initial prices
        if self.ws_connected:
            time.sleep(1)
            self._print_prices()
    
    def _init_websocket(self):
        """Initialize WebSocket connection"""
        try:
            if WS_AVAILABLE:
                self.ws = ForexDashboardClient(url='http://localhost:5002')
                self.ws_connected = self.ws.connect()
                
                if not self.ws_connected:
                    logger.warning('⚠️ WebSocket connection failed - using fallback')
                    self.use_fallback = True
            else:
                self.use_fallback = True
                
        except Exception as e:
            logger.error(f'❌ WebSocket init error: {e}')
            self.use_fallback = True
    
    def _print_prices(self):
        """Print current prices from WebSocket"""
        if not self.ws_connected:
            return
            
        prices = self.ws.get_all_prices()
        if prices:
            logger.info('📊 Current Prices from forex_dashboard:')
            count = 0
            for symbol, price in prices.items():
                if price > 0 and count < 10:
                    logger.info(f'   {symbol}: {price:.5f}')
                    count += 1
            if len(prices) > 10:
                logger.info(f'   ... and {len(prices) - 10} more')
        else:
            logger.info('⚠️ No prices received yet')
    
    def get_price(self, symbol: str) -> float:
        """Get price from WebSocket or fallback"""
        if self.ws_connected:
            price = self.ws.get_price(symbol)
            if price > 0:
                return price
        
        # Fallback to price_service
        return price_service.get_price(symbol)
    
    def get_signal(self, symbol: str) -> Dict:
        """Get trading signal"""
        price = self.get_price(symbol)
        
        # Determine source
        if symbol in price_service.forex_pairs or symbol in price_service.dollar:
            source = 'ENGINE_SYSTEM'
        else:
            source = 'ZSCORE_SYSTEM'
        
        # For now, just HOLD
        return {
            'action': 'HOLD',
            'confidence': 50,
            'price': price,
            'source': source,
            'symbol': symbol,
            'timestamp': datetime.now().isoformat(),
            'ws_connected': self.ws_connected
        }
    
    def process_cycle(self) -> Dict:
        """Process one trading cycle"""
        self.cycle_count += 1
        
        results = {
            'cycle': self.cycle_count,
            'timestamp': datetime.now().isoformat(),
            'signals': {},
            'active_positions': len(self.active_positions),
            'ws_connected': self.ws_connected
        }
        
        # Check WebSocket connection
        if self.ws_connected and not self.ws.is_connected():
            logger.warning('⚠️ WebSocket disconnected - attempting reconnect...')
            self.ws_connected = self.ws.connect()
            if self.ws_connected:
                logger.info('✅ WebSocket reconnected!')
        
        logger.info(f'\n🔄 CYCLE {self.cycle_count} - {datetime.now().strftime("%H:%M:%S")}')
        logger.info(f'   WebSocket: {"✅ Connected" if self.ws_connected else "❌ Fallback"}')
        
        symbols_with_prices = 0
        for symbol in self.all_symbols:
            if symbol in self.active_positions:
                continue
            
            signal = self.get_signal(symbol)
            results['signals'][symbol] = signal
            
            price = signal.get('price', 0)
            if price > 0:
                symbols_with_prices += 1
                # Show progress every 3 cycles
                if self.cycle_count % 3 == 0:
                    logger.info(f'📊 {symbol}: HOLD @ {price:.5f}')
        
        # Log summary
        logger.info(f'\n📊 Summary:')
        logger.info(f'   Symbols with prices: {symbols_with_prices}/{len(self.all_symbols)}')
        logger.info(f'   Active Positions: {len(self.active_positions)}')
        logger.info(f'   WebSocket: {"✅" if self.ws_connected else "❌"}')
        
        return results
    
    def run(self):
        """Main loop"""
        self.is_running = True
        logger.info('🚀 Starting Unified Trading Controller...')
        logger.info(f'   WebSocket: {"Connected to forex_dashboard" if self.ws_connected else "Fallback mode"}')
        
        try:
            while self.is_running:
                self.process_cycle()
                time.sleep(self.cycle_interval)
        except KeyboardInterrupt:
            self.stop()
        finally:
            if self.ws:
                self.ws.disconnect()
    
    def stop(self):
        """Stop the controller"""
        self.is_running = False
        logger.info('✅ Stopped')
    
    def get_status(self) -> Dict:
        """Get system status"""
        ws_status = self.ws.get_status() if self.ws else {}
        return {
            'is_running': self.is_running,
            'cycle_count': self.cycle_count,
            'risk': self.risk_manager.get_status(),
            'symbols': len(self.all_symbols),
            'websocket': {
                'connected': self.ws_connected,
                'prices': len(self.ws.prices) if self.ws else 0
            },
            'timestamp': datetime.now().isoformat()
        }


if __name__ == '__main__':
    print('\n' + '=' * 60)
    print('🚀 UNIFIED TRADING CONTROLLER')
    print('=' * 60)
    
    config = {
        'cycle_interval': 2,
        'daily_loss_limit': 100,
        'max_positions': 3,
        'cold_start_threshold': 50,
        'cold_start_min_win_rate': 0.4
    }
    
    controller = UnifiedTradingController(config)
    print('\n✅ Controller ready. Starting...\n')
    
    try:
        controller.run()
    except KeyboardInterrupt:
        print('\n🛑 Stopped by user')
    finally:
        controller.stop()