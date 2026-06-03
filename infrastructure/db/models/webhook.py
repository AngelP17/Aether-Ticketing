from sqlalchemy import Column, Integer, String, DateTime, Boolean, JSON
from datetime import datetime

from infrastructure.db.base import Base


class Webhook(Base):
    __tablename__ = "webhooks"

    id = Column(Integer, primary_key=True, autoincrement=True)
    url = Column(String(500), nullable=False)
    secret = Column(String(200), nullable=True)  # for HMAC sig
    events = Column(JSON, nullable=False, default=list)  # e.g. ["ticket.created", "decision.recomputed", "incident.created"]
    active = Column(Boolean, default=True, index=True)
    created_at = Column(DateTime, default=datetime.utcnow, index=True)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
