from contextlib import asynccontextmanager
from typing import Any

from fastapi import FastAPI, WebSocket
from fastapi.middleware.cors import CORSMiddleware

from apps.api.config import settings, validate_production_settings
from apps.api.deps import init_db
from apps.api.routes.actions import router as actions_router
from apps.api.routes.attachments import router as attachments_router
from apps.api.routes.assets import router as assets_router
from apps.api.routes.auth import router as auth_router
from apps.api.routes.catalog import router as catalog_router
from apps.api.routes.comments import router as comments_router
from apps.api.routes.decisions import router as decisions_router
from apps.api.routes.diagnostics import router as diagnostics_router
from apps.api.routes.events import router as events_router
from apps.api.routes.governance import router as governance_router
from apps.api.services.websocket_manager import manager  # Phase 8 WS

from apps.api.routes.incidents import router as incidents_router
from apps.api.routes.intelligence import router as intelligence_router
from apps.api.routes.metrics import router as metrics_router
from apps.api.routes.recommendations import router as recommendations_router
from apps.api.routes.replay import router as replay_router
from apps.api.routes.reports import router as reports_router
from apps.api.routes.tickets import router as tickets_router


@asynccontextmanager
async def lifespan(app: FastAPI) -> Any:
    validate_production_settings()
    init_db()
    yield


app = FastAPI(
    title="Aether API",
    description="Operational Incident Intelligence and Decision Platform",
    version="0.1.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.ALLOWED_ORIGINS.split(","),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(tickets_router, prefix="/api/tickets", tags=["tickets"])
app.include_router(incidents_router, prefix="/api/incidents", tags=["incidents"])
app.include_router(decisions_router, prefix="/api/decisions", tags=["decisions"])
app.include_router(
    recommendations_router,
    prefix="/api/recommendations",
    tags=["recommendations"],
)
app.include_router(reports_router, prefix="/api/reports", tags=["reports"])
app.include_router(replay_router, prefix="/api/replay", tags=["replay"])
app.include_router(metrics_router, prefix="/api/metrics", tags=["metrics"])
app.include_router(assets_router, prefix="/api/assets", tags=["assets"])
app.include_router(events_router, prefix="/api/events", tags=["events"])
app.include_router(auth_router, prefix="/api/auth", tags=["auth"])
app.include_router(catalog_router, prefix="/api", tags=["catalog"])
app.include_router(comments_router, prefix="/api", tags=["comments"])
app.include_router(attachments_router, prefix="/api", tags=["attachments"])
app.include_router(actions_router, prefix="/api/actions", tags=["actions"])
app.include_router(intelligence_router, prefix="/api/intelligence", tags=["intelligence"])
app.include_router(governance_router, prefix="/api/governance", tags=["governance"])
app.include_router(diagnostics_router, prefix="/api/diagnostics", tags=["diagnostics"])
app.include_router(__import__("apps.api.routes.notifications", fromlist=["router"]).router, prefix="/api/notifications", tags=["notifications"])
app.include_router(__import__("apps.api.routes.audit", fromlist=["router"]).router, prefix="/api/audit", tags=["audit"])
app.include_router(__import__("apps.api.routes.portal", fromlist=["router"]).router, prefix="/api/portal", tags=["portal"])  # Phase 8 public-ish
app.include_router(__import__("apps.api.routes.kb", fromlist=["router"]).router, prefix="/api/kb", tags=["kb"])  # Phase 8




@app.get("/health")
async def health_check() -> Any:
    return {"status": "healthy", "service": "aether-api"}


@app.get("/")
async def root() -> Any:
    return {
        "service": "Aether API",
        "version": "0.1.0",
        "docs": "/docs",
    }


# Phase 8: WebSocket realtime (pub/sub for ticket/incident/decision updates)
# Clients connect e.g. ws://.../ws/tickets/IT-xxx or /ws/global
# Auth is header-based or query token (simple for now; production should verify JWT).
@app.websocket("/ws/{topic}")
async def ws_endpoint(websocket: WebSocket, topic: str = "global") -> None:
    # Minimal: accept all for demo (in prod: parse token from query or subprotocol, call get_current_user logic)
    await manager.connect(websocket, topic)
    try:
        while True:
            # Echo or handle client pings/sub; for broadcast-only server push, just keep alive
            data = await websocket.receive_text()
            # Optional: allow client to request resync or specific topic change
            if data.startswith("subscribe:"):
                new_topic = data.split(":", 1)[1].strip()
                manager.disconnect(websocket, topic)
                await manager.connect(websocket, new_topic)
                topic = new_topic
            else:
                await manager.send_personal({"type": "echo", "data": data}, websocket)
    except Exception:
        pass
    finally:
        manager.disconnect(websocket, topic)
