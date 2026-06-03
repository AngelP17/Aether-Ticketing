from sqlalchemy import Column, Integer, String, DateTime, Boolean, ForeignKey
from datetime import datetime
from infrastructure.db.base import Base


class TicketSlaTracking(Base):
    __tablename__ = "ticket_sla_tracking"

    id = Column(Integer, primary_key=True, autoincrement=True)
    ticket_id = Column(Integer, ForeignKey("tickets.id"), nullable=False, index=True)
    sla_policy_id = Column(Integer, ForeignKey("sla_policies.id"), nullable=True)
    first_response_at = Column(DateTime, nullable=True)
    resolved_at = Column(DateTime, nullable=True)
    response_breach = Column(Boolean, default=False)
    resolution_breach = Column(Boolean, default=False)
    paused = Column(Boolean, default=False)
    pause_reason = Column(String(200))
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
