# test_fastapi_ws.py
"""
Test FastAPI WebSocket on port 8001
"""

import asyncio
import websockets
import json

async def test():
    print("\n" + "="*60)
    print("🔌 TESTING FASTAPI WEBSOCKET (PORT 8001)")
    print("="*60)
    
    uri = "ws://localhost:8001/ws/prices/test_client"
    
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
            except:
                pass
            
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
            
            # Check HTTP
            import requests
            print("\n3. Checking HTTP endpoints...")
            try:
                response = requests.get("http://localhost:8001/ws/test")
                print(f"   ✅ /ws/test: {response.json()}")
                
                response = requests.get("http://localhost:8001/ws/status")
                status = response.json()
                print(f"   ✅ /ws/status: {status.get('connected', 0)} clients")
            except Exception as e:
                print(f"   ❌ HTTP error: {e}")
            
            print("\n" + "="*60)
            print("✅ FASTAPI WEBSOCKET WORKING!")
            return True
            
    except Exception as e:
        print(f"\n❌ Failed: {e}")
        return False

if __name__ == "__main__":
    asyncio.run(test())