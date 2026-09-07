# standalone_ws_test_fixed.py
"""
Standalone WebSocket server - Fixed for websockets 13.0+
"""

import asyncio
import websockets
import json
import random
import time

connected_clients = set()
prices = {
    'EURUSD': 1.14337,
    'GBPUSD': 1.34509,
    'USDJPY': 162.449,
    'GOLD': 3987.55,
    '#NASDAQ100': 21500.00,
}

async def handler(websocket):
    """Handle WebSocket connection - no path parameter needed"""
    client_addr = websocket.remote_address
    print(f"✅ Client connected: {client_addr}")
    connected_clients.add(websocket)
    
    try:
        # Send initial data
        await websocket.send(json.dumps({
            'type': 'connected',
            'prices': prices,
            'timestamp': time.time()
        }))
        
        async for message in websocket:
            if message == 'ping':
                await websocket.send('pong')
            elif message == 'get_prices':
                await websocket.send(json.dumps({
                    'type': 'price_response',
                    'data': prices
                }))
            elif message == 'get_status':
                await websocket.send(json.dumps({
                    'type': 'status_response',
                    'connected': len(connected_clients),
                    'prices': len(prices)
                }))
            else:
                await websocket.send(f"Echo: {message}")
    
    except websockets.exceptions.ConnectionClosed:
        pass
    finally:
        connected_clients.discard(websocket)
        print(f"❌ Client disconnected: {client_addr} (Total: {len(connected_clients)})")

async def broadcast_loop():
    """Broadcast price updates"""
    last_prices = {}
    while True:
        try:
            # Simulate price changes
            for symbol in prices:
                if symbol in ['EURUSD', 'GBPUSD']:
                    change = random.uniform(-0.0003, 0.0003)
                    prices[symbol] = round(prices[symbol] + change, 5)
                elif symbol in ['#NASDAQ100']:
                    change = random.uniform(-2, 2)
                    prices[symbol] = round(prices[symbol] + change, 2)
                elif symbol == 'GOLD':
                    change = random.uniform(-0.5, 0.5)
                    prices[symbol] = round(prices[symbol] + change, 2)
            
            if prices != last_prices and connected_clients:
                last_prices = prices.copy()
                message = json.dumps({
                    'type': 'price_update',
                    'data': prices,
                    'timestamp': time.time()
                })
                disconnected = set()
                for client in connected_clients:
                    try:
                        await client.send(message)
                    except:
                        disconnected.add(client)
                for client in disconnected:
                    connected_clients.discard(client)
            
            await asyncio.sleep(1)
        except Exception as e:
            print(f"Broadcast error: {e}")
            await asyncio.sleep(1)

async def main():
    """Start standalone WebSocket server"""
    print("\n" + "="*60)
    print("🚀 STANDALONE WEBSOCKET SERVER (PORT 8766) - FIXED")
    print("="*60)
    print("\n📡 Server running on: ws://localhost:8766")
    print("   Test with: python test_standalone_fixed.py")
    print("   Press Ctrl+C to stop\n")
    print("="*60)
    
    # Start broadcast loop
    asyncio.create_task(broadcast_loop())
    
    # Start server on port 8766 - no path parameter needed
    async with websockets.serve(handler, "0.0.0.0", 8766):
        await asyncio.Future()  # Run forever

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n🛑 Server stopped")