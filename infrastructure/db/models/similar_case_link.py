from sqlalchemy import Column, Integer, String, Float, JSON, ForeignKey
from sqlalchemy.orm import relationship

from infrastructure.db.base import Base


class SimilarCaseLink(Base):
    __tablename__ = "similar_case_links"

    id = Column(Integer, primary_key=True, autoincrement=True)
    ticket_id = Column(
        Integer, ForeignKey("tickets.id", ondelete="CASCADE"), nullable=False, index=True
    )
    similar_ticket_id = Column(
        Integer, ForeignKey("tickets.id", ondelete="CASCADE"), nullable=False, index=True
    )
    similarity_score = Column(Float, default=0.0)
    match_basis_json = Column(JSON)
    resolution_effective = Column(String(10), nullable=True)
    time_to_resolve_hours = Column(Integer, nullable=True)

    ticket = relationship("Ticket", foreign_keys=[ticket_id], back_populates="similar_from")
    similar_ticket = relationship(
        "Ticket", foreign_keys=[similar_ticket_id], back_populates="similar_to"
    )
