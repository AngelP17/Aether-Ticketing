from sqlalchemy import Column, Integer, String, DateTime, JSON, ForeignKey
from sqlalchemy.orm import relationship
from datetime import datetime

from infrastructure.db.base import Base


class TicketEvent(Base):
    __tablename__ = "ticket_events"

    id = Column(Integer, primary_key=True, autoincrement=True)
    ticket_id = Column(
        Integer, ForeignKey("tickets.id", ondelete="CASCADE"), nullable=False, index=True
    )
    event_type = Column(String(50), nullable=False, index=True)
    event_ts = Column(DateTime, default=datetime.utcnow, index=True)
    actor_type = Column(String(20), nullable=False)
    actor_id = Column(String(100))
    payload_json = Column(JSON)
    source_hash = Column(String(64))

    ticket = relationship("Ticket", back_populates="events")
