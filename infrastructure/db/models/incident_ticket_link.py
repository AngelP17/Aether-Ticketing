from sqlalchemy import Column, Integer, String, Float, ForeignKey
from sqlalchemy.orm import relationship

from infrastructure.db.base import Base


class IncidentTicketLink(Base):
    __tablename__ = "incident_ticket_links"

    id = Column(Integer, primary_key=True, autoincrement=True)
    incident_id = Column(
        Integer, ForeignKey("incidents.id", ondelete="CASCADE"), nullable=False, index=True
    )
    ticket_id = Column(
        Integer, ForeignKey("tickets.id", ondelete="CASCADE"), nullable=False, index=True
    )
    link_type = Column(String(20), nullable=False)
    confidence = Column(Float, default=0.0)

    incident = relationship("Incident", back_populates="ticket_links")
    ticket = relationship("Ticket", back_populates="incident_links")
