# ============================================================
# api/websocket.py — WebSocket connection manager
# ============================================================

from fastapi import WebSocket, WebSocketDisconnect
from typing import List
from datetime import datetime


class ConnectionManager:
    """Manages WebSocket connections for real-time updates"""

    def __init__(self):
        self.active_connections: List[WebSocket] = []

    async def connect(self, websocket: WebSocket):
        """Accept and store new WebSocket connection"""
        await websocket.accept()
        self.active_connections.append(websocket)

    def disconnect(self, websocket: WebSocket):
        """Remove WebSocket connection"""
        if websocket in self.active_connections:
            self.active_connections.remove(websocket)

    async def broadcast(self, message: dict):
        """Send message to all connected clients"""
        disconnected = []
        for connection in self.active_connections:
            try:
                await connection.send_json(message)
            except:
                disconnected.append(connection)

        # Remove broken connections
        for conn in disconnected:
            self.disconnect(conn)

    async def send_booking_update(self, event_type: str, booking_data: dict):
        """Send booking update to all clients"""
        message = {
            "type": "booking_update",
            "event": event_type,  # "created", "updated", "cancelled"
            "data": booking_data,
            "timestamp": str(datetime.now())
        }
        await self.broadcast(message)

    async def send_slot_update(self, event_type: str, slot_data: dict):
        """Send slot availability update to all clients"""
        message = {
            "type": "slot_update",
            "event": event_type,  # "added", "removed", "closed"
            "data": slot_data,
            "timestamp": str(datetime.now())
        }
        await self.broadcast(message)


# Global instance
manager = ConnectionManager()
