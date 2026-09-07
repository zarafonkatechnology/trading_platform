import asyncio
import json
import websockets

async def main():
    uri = 'ws://127.0.0.1:8000/ws/prices/test123'
    async with websockets.connect(uri) as ws:
        greeting = await asyncio.wait_for(ws.recv(), timeout=5)
        print('RECV1', greeting)
        await ws.send('ping')
        reply = await asyncio.wait_for(ws.recv(), timeout=5)
        print('RECV2', reply)

if __name__ == '__main__':
    asyncio.run(main())
