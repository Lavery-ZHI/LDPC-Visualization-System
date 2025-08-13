from fastapi import WebSocket
import asyncio
import json
import uuid
from typing import Dict, Any

class WebSocketManager:
    def __init__(self):
        self.active_connections: Dict[str, WebSocket] = {}

    async def connect(self, websocket: WebSocket) -> str:
        """Establish WebSocket connection"""
        await websocket.accept()
        session_id = str(uuid.uuid4())
        self.active_connections[session_id] = websocket
        return session_id

    async def disconnect(self, session_id: str):
        """Disconnect connection"""
        if session_id in self.active_connections:
            del self.active_connections[session_id]

    async def send_progress(self, session_id: str, data: Dict):
        """Send progress update"""
        if session_id in self.active_connections:
            websocket = self.active_connections[session_id]
            await websocket.send_text(json.dumps(data))

    async def broadcast(self, data: Dict):
        """Broadcast message to all connected clients"""
        for websocket in self.active_connections.values():
            await websocket.send_text(json.dumps(data))
