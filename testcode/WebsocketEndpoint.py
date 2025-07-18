import asyncio
import json
import websockets

async def download():
    uri = "ws://localhost:8000/video/download"
    async with websockets.connect(uri) as websocket:
        await websocket.send(json.dumps({
            "format": "299", # Change format
            "task_id": "2e055bbc-2f10-4980-8bd3-459c5a0c41d8" # Change task_id
        }))

        try:
            while True:  # Explicit loop to keep receiving messages
                message = await websocket.recv()
                print(f"Received: {message}")
        except websockets.exceptions.ConnectionClosed:
            print("Connection closed by the server")

asyncio.run(download())