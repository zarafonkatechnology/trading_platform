# test_standalone_fixed.py
"""
Test standalone WebSocket server on port 8766 - Fixed
"""

import asyncio
import websockets
import json

async def test():
    print("\n" + "="*60)
    print("🔌 TESTING STANDALONE WEBSOCKET (PORT 8766) - FIXED")
    print("="*60)
    
    uri = "ws://localhost:8766"
    
    print(f"\n📡 Connecting to: {uri}")
    
    try:
        async with websockets.connect(uri) as websocket:
            print("✅ CONNECTED!")
            
            # Wait for initial
            try:
                response = await asyncio.wait_for(websocket.recv(), timeout=3)
                data = json.loads(response)
                print(f"📨 Initial: {data.get('type')}")
                prices = data.get('prices', {})
                print(f"   Prices: {len(prices)} symbols")
            except Exception as e:
                print(f"   ⚠️ No initial message: {e}")
            
            # Test ping
            print("\n1. Testing ping...")
            await websocket.send("ping")
            response = await asyncio.wait_for(websocket.recv(), timeout=3)
            print(f"   ✅ Ping: {response}")
            
            # Test get prices
            print("\n2. Getting prices...")
            await websocket.send("get_prices")
            response = await asyncio.wait_for(websocket.recv(), timeout=3)
            data = json.loads(response)
            prices = data.get('data', {})
            print(f"   ✅ Received {len(prices)} prices")
            
            for symbol, price in list(prices.items())[:3]:
                print(f"      {symbol}: {price}")
            
            # Test get status
            print("\n3. Getting status...")
            await websocket.send("get_status")
            response = await asyncio.wait_for(websocket.recv(), timeout=3)
            data = json.loads(response)
            print(f"   ✅ Status: {data.get('connected', 0)} clients")
            
            print("\n" + "="*60)
            print("✅ STANDALONE WEBSOCKET WORKING!")
            return True
            
    except Exception as e:
        print(f"\n❌ Failed: {e}")
        return False

if __name__ == "__main__":
    asyncio.run(test())