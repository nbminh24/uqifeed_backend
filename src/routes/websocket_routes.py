from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Depends
from src.utils.websocket import websocket_manager
from src.services.authentication.user_auth import get_current_user_ws
import logging

logger = logging.getLogger(__name__)

router = APIRouter()

@router.websocket("/ws/{user_id}")
async def websocket_endpoint(websocket: WebSocket, user_id: str):
    try:
        # Authenticate user
        user = await get_current_user_ws(websocket, user_id)
        if not user:
            await websocket.close(code=4001)
            return
            
        # Connect to WebSocket
        await websocket_manager.connect(websocket, user_id)
        
        try:
            while True:
                # Keep connection alive and handle incoming messages
                data = await websocket.receive_text()
                # Process any incoming messages if needed
                
        except WebSocketDisconnect:
            websocket_manager.disconnect(websocket, user_id)
            
    except Exception as e:
        logger.error(f"WebSocket error: {str(e)}")
        try:
            await websocket.close(code=1011)
        except:
            pass 