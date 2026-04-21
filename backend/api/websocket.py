"""
WebSocket connection manager and endpoint.

URL: wss://liquid-glass-calendar-design.onrender.com/ws

All connected clients receive broadcast messages in JSON format:
  { "type": str, "data": dict }

Message types:
  slot_booked       — when a slot is booked
  slot_freed        — when a booking is deleted (slot freed)
  slot_added        — when admin adds a new time slot
  slot_deleted      — when admin deletes a time slot
  booking_cancelled — when a booking is cancelled by client
  booking_updated   — when admin edits booking details
  work_day_added    — when admin adds a new work day
"""

import json
import logging
from typing import List

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

logger = logging.getLogger(__name__)
router = APIRouter(tags=["websocket"])


class ConnectionManager:
    """Manages a pool of active WebSocket connections."""

    def __init__(self) -> None:
        self.active_connections: List[WebSocket] = []

    async def connect(self, websocket: WebSocket) -> None:
        await websocket.accept()
        self.active_connections.append(websocket)
        logger.info(
            "WebSocket connected. Total: %d", len(self.active_connections)
        )

    def disconnect(self, websocket: WebSocket) -> None:
        if websocket in self.active_connections:
            self.active_connections.remove(websocket)
        logger.info(
            "WebSocket disconnected. Total: %d", len(self.active_connections)
        )

    async def broadcast(self, message: dict) -> None:
        """Send a JSON message to all connected clients."""
        payload = json.dumps(message, ensure_ascii=False)
        disconnected: List[WebSocket] = []
        for ws in self.active_connections:
            try:
                await ws.send_text(payload)
            except Exception:
                disconnected.append(ws)

        for ws in disconnected:
            self.disconnect(ws)


# Singleton connection manager — imported by route modules
manager = ConnectionManager()


@router.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket) -> None:
    """WebSocket endpoint. Keeps connection alive and handles pings."""
    await manager.connect(websocket)
    try:
        while True:
            # Wait for any message from client (ping/pong or ignore)
            data = await websocket.receive_text()
            # Echo ping back
            try:
                msg = json.loads(data)
                if msg.get("type") == "ping":
                    await websocket.send_text(json.dumps({"type": "pong"}))
            except json.JSONDecodeError:
                pass
    except WebSocketDisconnect:
        manager.disconnect(websocket)
