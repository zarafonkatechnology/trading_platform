import asyncio
import json
import websockets

async def main():
    uri = 'ws://127.0.0.1:8001/ws/signals/test_client'
    async with websockets.connect(uri) as ws:
        print('connected')
        await ws.send(json.dumps({'type': 'subscribe', 'symbols': ['EURUSD']}))
        msg = await asyncio.wait_for(ws.recv(), timeout=5)
        print('first', msg)
        await ws.send(json.dumps({'type': 'ping'}))
        msg2 = await asyncio.wait_for(ws.recv(), timeout=5)
        print('second', msg2)

asyncio.run(main())
