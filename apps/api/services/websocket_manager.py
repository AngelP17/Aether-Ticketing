"""
WebSocket manager (Phase 8 realtime).

Simple in-memory connection manager. Broadcast by topic (e.g. "ticket:IT-xxx" or "global").
FastAPI WebSocket endpoints will use this.
For prod scale: use Redis pub/sub + multiple workers (deps already have redis/websockets).
"""
from __future__ import annotations

import json
import logging
from typing import Any, Dict, Set

from fastapi import WebSocket

logger = logging.getLogger(__name__)


class ConnectionManager:
    def __init__(self) -> None:
        self.active: Dict[str, Set[WebSocket]] = {}  # topic -> sockets

    async def connect(self, websocket: WebSocket, topic: str = "global") -> None:
        await websocket.accept()
        if topic not in self.active:
            self.active[topic] = set()
        self.active[topic].add(websocket)
        logger.debug("[ws] connected topic=%s total=%s", topic, len(self.active[topic]))

    def disconnect(self, websocket: WebSocket, topic: str = "global") -> None:
        if topic in self.active and websocket in self.active[topic]:
            self.active[topic].remove(websocket)
            if not self.active[topic]:
                del self.active[topic]

    async def send_personal(self, message: dict[str, Any], websocket: WebSocket) -> None:
        try:
            await websocket.send_text(json.dumps(message, default=str))
        except Exception:
            pass

    async def broadcast(self, message: dict[str, Any], topic: str = "global") -> None:
        if topic not in self.active:
            return
        dead: list[WebSocket] = []
        for ws in list(self.active[topic]):
            try:
                await ws.send_text(json.dumps(message, default=str))
            except Exception:
                dead.append(ws)
        for ws in dead:
            self.disconnect(ws, topic)
        logger.debug("[ws] broadcast topic=%s to %s", topic, len(self.active.get(topic, [])))

    async def broadcast_ticket_update(self, ticket_id: str, payload: dict[str, Any]) -> None:
        msg = {"type": "ticket_update", "ticket_id": ticket_id, "payload": payload}
        await self.broadcast(msg, f"ticket:{ticket_id}")
        await self.broadcast(msg, "global")  # also global for command center listeners

    async def broadcast_incident_update(self, incident_id: str, payload: dict[str, Any]) -> None:
        msg = {"type": "incident_update", "incident_id": incident_id, "payload": payload}
        await self.broadcast(msg, f"incident:{incident_id}")
        await self.broadcast(msg, "global")


manager = ConnectionManager()
