from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from apps.api.config import settings, validate_production_settings
from apps.api.deps import init_db
from apps.api.routes.attachments import router as attachments_router
from apps.api.routes.assets import router as assets_router
from apps.api.routes.auth import router as auth_router
from apps.api.routes.catalog import router as catalog_router
from apps.api.routes.comments import router as comments_router
from apps.api.routes.decisions import router as decisions_router
from apps.api.routes.events import router as events_router
from apps.api.routes.incidents import router as incidents_router
from apps.api.routes.metrics import router as metrics_router
from apps.api.routes.recommendations import router as recommendations_router
from apps.api.routes.replay import router as replay_router
from apps.api.routes.reports import router as reports_router
from apps.api.routes.tickets import router as tickets_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    validate_production_settings()
    if settings.AUTO_INIT_DB:
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


@app.get("/health")
async def health_check():
    return {"status": "healthy", "service": "aether-api"}


@app.get("/")
async def root():
    return {
        "service": "Aether API",
        "version": "0.1.0",
        "docs": "/docs",
    }
