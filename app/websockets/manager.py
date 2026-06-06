from typing import Dict, List
from fastapi import WebSocket


class ConnectionManager:
    def __init__(self):
        self.active_connections: Dict[str, List[WebSocket]] = {}

    async def connect(self, websocket: WebSocket, room: str = "global"):
        await websocket.accept()
        self.active_connections.setdefault(room, []).append(websocket)

    def disconnect(self, websocket: WebSocket, room: str = "global"):
        connections = self.active_connections.get(room, [])
        if websocket in connections:
            connections.remove(websocket)

    async def broadcast(self, message: dict, room: str = "global"):
        for connection in self.active_connections.get(room, []):
            await connection.send_json(message)

    async def broadcast_all(self, message: dict):
        for connections in self.active_connections.values():
            for connection in connections:
                await connection.send_json(message)


manager = ConnectionManager()
