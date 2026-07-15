"""
WebSocket connection manager and endpoint.

URL: wss://liquid-glass-calendar-design.onrender.com/ws

Optional auth via initData query parameter:
  wss://.../ws?init_data=<tgWebAppData>

Without initData → anonymous connection (receives broadcasts only).
With valid initData → authenticated connection with user_id tracked.

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
from typing import Dict, List, Optional

from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Query

from api.deps import verify_ws_init_data

logger = logging.getLogger(__name__)
router = APIRouter(tags=["websocket"])


class ConnectionManager:
    """Manages a pool of active WebSocket connections with optional auth."""

    def __init__(self) -> None:
        # Maps WebSocket → user_id (None = anonymous)
        self._connections: Dict[WebSocket, Optional[int]] = {}

    @property
    def active_connections(self) -> List[WebSocket]:
        return list(self._connections.keys())

    async def connect(self, websocket: WebSocket, user_id: Optional[int] = None) -> None:
        await websocket.accept()
        self._connections[websocket] = user_id
        logger.info(
            "WebSocket connected. user_id=%s. Total: %d",
            user_id, len(self._connections),
        )

    def disconnect(self, websocket: WebSocket) -> None:
        if websocket in self._connections:
            del self._connections[websocket]
        logger.info(
            "WebSocket disconnected. Total: %d", len(self._connections)
        )

    async def broadcast(self, message: dict) -> None:
        """Send a JSON message to all connected clients."""
        payload = json.dumps(message, ensure_ascii=False)
        disconnected: List[WebSocket] = []
        for ws in list(self._connections.keys()):
            try:
                await ws.send_text(payload)
            except Exception:
                disconnected.append(ws)

        for ws in disconnected:
            self.disconnect(ws)

    async def send_to_user(self, user_id: int, message: dict) -> bool:
        """Send a message to a specific authenticated user. Returns True if sent."""
        payload = json.dumps(message, ensure_ascii=False)
        for ws, uid in self._connections.items():
            if uid == user_id:
                try:
                    await ws.send_text(payload)
                    return True
                except Exception:
                    self.disconnect(ws)
        return False


# Singleton connection manager — imported by route modules
manager = ConnectionManager()


@router.websocket("/ws")
async def websocket_endpoint(
    websocket: WebSocket,
    init_data: Optional[str] = Query(None, alias="init_data"),
) -> None:
    """
    WebSocket endpoint with optional initData authentication.

    Query params:
      init_data=<Telegram WebApp initData>  — optional, authenticates the connection

    Without initData: anonymous read-only connection.
    With valid initData: authenticated, user_id tracked for targeted messages.
    """
    user_id: Optional[int] = None

    if init_data:
        user_id = await verify_ws_init_data(init_data)
        if user_id:
            logger.info("WebSocket authenticated: user_id=%d", user_id)
        else:
            logger.warning("WebSocket initData validation failed, connecting as anonymous")

    await manager.connect(websocket, user_id=user_id)
    try:
        while True:
            data = await websocket.receive_text()
            try:
                msg = json.loads(data)
                if msg.get("type") == "ping":
                    await websocket.send_text(json.dumps({"type": "pong"}))
            except json.JSONDecodeError:
                pass
    except WebSocketDisconnect:
        manager.disconnect(websocket)
