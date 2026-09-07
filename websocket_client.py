"""
WebSocket Client for forex_dashboard.py
Connects to the dashboard WebSocket and receives real-time prices
"""

import sys
import os
import json
import time
import logging
from datetime import datetime
from typing import Dict

# Install required package: pip install python-socketio websocket-client

try:
    import socketio
    from socketio import Client
    SOCKETIO_AVAILABLE = True
except ImportError:
    SOCKETIO_AVAILABLE = False
    print("❌ python-socketio not installed. Run: pip install python-socketio")
    sys.exit(1)

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class ForexDashboardClient:
    """WebSocket client for forex_dashboard.py"""
    
    def __init__(self, url='http://localhost:5002'):
        self.url = url
        self.sio = None
        self.prices = {}
        self.balance = 0
        self.equity = 0
        self.timestamp = ''
        self.connected = False
        self._setup_client()
    
    def _setup_client(self):
        """Setup the SocketIO client"""
        self.sio = Client(
            reconnection=True,
            reconnection_attempts=10,
            reconnection_delay=1,
            reconnection_delay_max=5
        )
        
        @self.sio.event
        def connect():
            self.connected = True
            logger.info('✅ Connected to forex_dashboard WebSocket')
        
        @self.sio.event
        def disconnect():
            self.connected = False
            logger.warning('⚠️ Disconnected from forex_dashboard')
        
        @self.sio.event
        def connect_error(error):
            self.connected = False
            logger.error(f'❌ Connection error: {error}')
        
        @self.sio.event
        def price_update(data):
            """Handle price updates"""
            try:
                if 'prices' in data:
                    self.prices = data['prices']
                    logger.debug(f'📡 Received {len(self.prices)} prices')
                    
                    # Print a few prices to show it's working
                    count = 0
                    for symbol, price in list(self.prices.items())[:5]:
                        if price > 0:
                            logger.info(f'   {symbol}: {price:.5f}')
                            count += 1
                    if len(self.prices) > 5:
                        logger.info(f'   ... and {len(self.prices) - 5} more')
                
                if 'balance' in data:
                    self.balance = data['balance']
                if 'equity' in data:
                    self.equity = data['equity']
                if 'timestamp' in data:
                    self.timestamp = data['timestamp']
                    
            except Exception as e:
                logger.error(f'Error processing update: {e}')
        
        @self.sio.event
        def full_update(data):
            """Handle full data updates"""
            try:
                if 'prices' in data:
                    self.prices = data['prices']
                    logger.info(f'📡 Full update: {len(self.prices)} prices')
                if 'balance' in data:
                    self.balance = data['balance']
                if 'equity' in data:
                    self.equity = data['equity']
                if 'timestamp' in data:
                    self.timestamp = data['timestamp']
            except Exception as e:
                logger.error(f'Error processing full update: {e}')
        
        @self.sio.event
        def message(data):
            """Handle generic message"""
            logger.debug(f'📨 Message: {type(data)}')
    
    def connect(self):
        """Connect to the WebSocket server"""
        try:
            logger.info(f'🔌 Connecting to {self.url}...')
            self.sio.connect(self.url, transports=['websocket', 'polling'])
            return True
        except Exception as e:
            logger.error(f'❌ Connection failed: {e}')
            return False
    
    def disconnect(self):
        """Disconnect from the WebSocket server"""
        if self.sio and self.connected:
            try:
                self.sio.disconnect()
                logger.info('✅ Disconnected')
            except:
                pass
            self.connected = False
    
    def get_price(self, symbol: str) -> float:
        """Get price for a symbol"""
        return self.prices.get(symbol, 0)
    
    def get_all_prices(self) -> Dict:
        """Get all prices"""
        return self.prices.copy()
    
    def is_connected(self) -> bool:
        """Check if connected"""
        return self.connected
    
    def get_status(self) -> Dict:
        """Get client status"""
        return {
            'connected': self.connected,
            'symbols': len(self.prices),
            'balance': self.balance,
            'equity': self.equity,
            'timestamp': self.timestamp,
            'url': self.url
        }


def main():
    """Main function to test the WebSocket client"""
    print('\n' + '=' * 60)
    print('📡 FOREX DASHBOARD WEBSOCKET CLIENT')
    print('=' * 60)
    print('Connecting to forex_dashboard.py at http://localhost:5002')
    print('=' * 60 + '\n')
    
    # Create client
    client = ForexDashboardClient()
    
    # Connect
    if not client.connect():
        print('❌ Failed to connect. Make sure forex_dashboard.py is running.')
        print('   Run: python forex_dashboard.py')
        sys.exit(1)
    
    print('\n✅ Connected! Waiting for price updates...\n')
    print('Press Ctrl+C to stop\n')
    
    try:
        # Keep running and display prices
        cycle = 0
        while True:
            cycle += 1
            time.sleep(2)
            
            status = client.get_status()
            prices = client.get_all_prices()
            
            print(f'\n📊 CYCLE {cycle} - {datetime.now().strftime("%H:%M:%S")}')
            print(f'   Connected: {status["connected"]}')
            print(f'   Symbols: {status["symbols"]}')
            print(f'   Balance: ${status["balance"]:.2f}')
            print(f'   Equity: ${status["equity"]:.2f}')
            print(f'   Last Update: {status["timestamp"]}')
            
            if prices:
                print('\n   Sample Prices:')
                count = 0
                for symbol, price in list(prices.items())[:8]:
                    if price > 0:
                        print(f'      {symbol}: {price:.5f}')
                        count += 1
                if len(prices) > 8:
                    print(f'      ... and {len(prices) - 8} more')
            else:
                print('   ⚠️ No prices received yet')
                
    except KeyboardInterrupt:
        print('\n\n🛑 Stopping...')
    finally:
        client.disconnect()
        print('✅ Done')


if __name__ == '__main__':
    main()