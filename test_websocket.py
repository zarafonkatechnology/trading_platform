# test_websocket.py
"""
Simple test to verify WebSocket connection to forex_dashboard.py
"""

import time
import logging

try:
    import socketio
    from socketio import Client
    print("✅ socketio imported")
except ImportError as e:
    print(f"❌ socketio import error: {e}")
    print("Run: pip install python-socketio")
    exit(1)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def main():
    print('\n' + '=' * 60)
    print('🔌 TESTING WEBSOCKET CONNECTION')
    print('=' * 60)
    print('Connecting to http://localhost:5002...')
    
    try:
        # Create client
        sio = Client()
        
        @sio.event
        def connect():
            print('✅ Connected to WebSocket server!')
            print('📡 Waiting for price updates...')
            print('   (You should see price data in a few seconds)')
        
        @sio.event
        def disconnect():
            print('❌ Disconnected from WebSocket server')
        
        @sio.event
        def connect_error(error):
            print(f'❌ Connection error: {error}')
        
        @sio.event
        def price_update(data):
            """Handle price updates"""
            if 'prices' in data:
                prices = data['prices']
                print(f'\n📡 Received {len(prices)} prices:')
                # Show first 5 prices
                count = 0
                for symbol, price in list(prices.items())[:5]:
                    if price > 0:
                        print(f'   {symbol}: {price:.5f}')
                        count += 1
                if len(prices) > 5:
                    print(f'   ... and {len(prices) - 5} more')
                
                if 'timestamp' in data:
                    print(f'   Timestamp: {data["timestamp"]}')
        
        # Connect
        print('🔌 Connecting...')
        sio.connect('http://localhost:5002', transports=['websocket', 'polling'])
        
        print('\n✅ Connection established!')
        print('   Press Ctrl+C to stop\n')
        
        # Keep running
        while True:
            time.sleep(1)
            
    except KeyboardInterrupt:
        print('\n\n🛑 Stopping...')
    except Exception as e:
        print(f'\n❌ Error: {e}')
        print('\nMake sure forex_dashboard.py is running:')
        print('   python forex_dashboard.py')
    finally:
        try:
            sio.disconnect()
            print('✅ Disconnected')
        except:
            pass

if __name__ == '__main__':
    main()