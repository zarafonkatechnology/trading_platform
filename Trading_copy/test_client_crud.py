# test_websocket.py
"""
Test WebSocket connection for real-time signals
"""

import asyncio
import websockets
import json
import time

async def test_websocket():
    print("=" * 60)
    print("🧪 TESTING WEBSOCKET CONNECTION")
    print("=" * 60)
    
    client_id = "test_client"
    uri = f"ws://localhost:8000/ws/signals/{client_id}"
    
    print(f"\n1️⃣ Connecting to WebSocket: {uri}")
    
    try:
        async with websockets.connect(uri) as websocket:
            print("✅ WebSocket connected")
            
            # 2. Subscribe to symbols
            print("\n2️⃣ Subscribing to symbols...")
            subscribe_msg = {
                "type": "subscribe",
                "symbols": ["EURUSD", "GOLD", "#S&P500"]
            }
            await websocket.send(json.dumps(subscribe_msg))
            print("✅ Subscription sent")
            
            # 3. Wait for messages
            print("\n3️⃣ Waiting for messages (5 seconds)...")
            messages_received = 0
            
            for i in range(5):
                try:
                    message = await asyncio.wait_for(websocket.recv(), timeout=2.0)
                    data = json.loads(message)
                    print(f"   📨 Message {i+1}: {data.get('type', 'unknown')}")
                    
                    if data.get('type') == 'initial_signals':
                        count = data.get('data', {}).get('count', 0)
                        print(f"   📊 Received {count} initial signals")
                    
                    messages_received += 1
                except asyncio.TimeoutError:
                    break
            
            print(f"\n✅ Received {messages_received} messages")
            
            # 4. Send ping
            print("\n4️⃣ Sending ping...")
            await websocket.send(json.dumps({"type": "ping"}))
            print("✅ Ping sent")
            
            # 5. Wait for pong
            try:
                message = await asyncio.wait_for(websocket.recv(), timeout=2.0)
                data = json.loads(message)
                print(f"   📨 Received: {data.get('type', 'unknown')}")
            except asyncio.TimeoutError:
                print("   ⏰ No response")
            
            # 6. Unsubscribe
            print("\n5️⃣ Unsubscribing...")
            await websocket.send(json.dumps({"type": "unsubscribe"}))
            print("✅ Unsubscribe sent")
            
    except Exception as e:
        print(f"❌ Error: {e}")
    
    print("\n" + "=" * 60)
    print("✅ WebSocket test complete!")
    print("=" * 60)

if __name__ == "__main__":
    asyncio.run(test_websocket())