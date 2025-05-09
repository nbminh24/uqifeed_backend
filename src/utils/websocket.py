from typing import Dict, Set, Any
from fastapi import WebSocket
import json
import logging

logger = logging.getLogger(__name__)

class WebSocketManager:
    def __init__(self):
        self.active_connections: Dict[str, Set[WebSocket]] = {}
        
    async def connect(self, websocket: WebSocket, user_id: str):
        await websocket.accept()
        if user_id not in self.active_connections:
            self.active_connections[user_id] = set()
        self.active_connections[user_id].add(websocket)
        logger.info(f"User {user_id} connected to WebSocket")
        
    def disconnect(self, websocket: WebSocket, user_id: str):
        if user_id in self.active_connections:
            self.active_connections[user_id].remove(websocket)
            if not self.active_connections[user_id]:
                del self.active_connections[user_id]
        logger.info(f"User {user_id} disconnected from WebSocket")
        
    async def broadcast_to_user(self, user_id: str, message: Dict[str, Any]):
        if user_id in self.active_connections:
            disconnected = set()
            for connection in self.active_connections[user_id]:
                try:
                    await connection.send_json(message)
                except Exception as e:
                    logger.error(f"Error sending message to user {user_id}: {str(e)}")
                    disconnected.add(connection)
                    
            # Clean up disconnected websockets
            for connection in disconnected:
                self.disconnect(connection, user_id)
                
    async def broadcast_to_all(self, message: Dict[str, Any]):
        for user_id in self.active_connections:
            await self.broadcast_to_user(user_id, message)

# Create global WebSocket manager instance
websocket_manager = WebSocketManager() 