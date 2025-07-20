from fastapi import WebSocket
import asyncio
import json
import uuid
from typing import Dict, Any

class WebSocketManager:
    def __init__(self):
        self.active_connections: Dict[str, WebSocket] = {}

    async def connect(self, websocket: WebSocket) -> str:
        """建立WebSocket连接"""
        await websocket.accept()
        session_id = str(uuid.uuid4())
        self.active_connections[session_id] = websocket
        return session_id

    async def disconnect(self, session_id: str):
        """断开连接"""
        if session_id in self.active_connections:
            del self.active_connections[session_id]

    async def send_progress(self, session_id: str, data: Dict):
        """发送进度更新"""
        if session_id in self.active_connections:
            websocket = self.active_connections[session_id]
            await websocket.send_text(json.dumps(data))

    async def broadcast(self, data: Dict):
        """向所有连接的客户端广播消息"""
        for websocket in self.active_connections.values():
            await websocket.send_text(json.dumps(data))
