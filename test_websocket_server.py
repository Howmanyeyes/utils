# async_websocket_server.py

import asyncio
import websockets
from websockets.exceptions import ConnectionClosedOK, ConnectionClosedError

# Set of connected clients
connected_clients = set()

async def handler(websocket, path = None):
    # Register client
    connected_clients.add(websocket)
    client_address = websocket.remote_address
    print(f"Client connected: {client_address}")

    try:
        async for message in websocket:
            print(f"Received message from {client_address}: {message}")
            # Echo the message back to the sender
            await websocket.send(f"Echo: {message}")
    except ConnectionClosedOK:
        print(f"Client disconnected gracefully: {client_address}")
    except ConnectionClosedError:
        print(f"Client disconnected with error: {client_address}")
    finally:
        # Unregister client
        connected_clients.remove(websocket)
        print(f"Client removed: {client_address}")

async def main():
    server = await websockets.serve(
        handler,              # Handler for incoming connections
        "localhost",         # Host
        8765,                # Port
        ping_interval=20,    # Optional: Keep connection alive
        ping_timeout=20
    )
    print("WebSocket server started on ws://localhost:8765")
    await server.wait_closed()

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\nWebSocket server stopped.")
