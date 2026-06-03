from datetime import datetime

from sqlalchemy import Boolean, Column, Date, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import relationship

from infrastructure.db.base import Base


class Ticket(Base):
    __tablename__ = "tickets"

    id = Column(Integer, primary_key=True, autoincrement=True)
    ticket_id = Column(String(20), unique=True, nullable=False, index=True)
    title = Column(Text, nullable=False)
    clean_summary = Column(Text)
    status = Column(String(50), default="Open", index=True)
    priority = Column(String(50), default="Low", index=True)
    request_type = Column(String(100))
    category_id = Column(Integer, nullable=True, index=True)
    staff_assigned = Column(String(100), index=True)
    requester = Column(String(100))
    date_opened = Column(Date, nullable=True, index=True)
    description = Column(Text)
    resolution_notes = Column(Text)
    source_hash = Column(String(64), nullable=True)
    priority_score_cache = Column(Integer, nullable=True)
    confidence_score_cache = Column(Integer, nullable=True)
    root_cause_hypothesis = Column(String(100), nullable=True)
    site_id = Column(String(100))
    asset_id = Column(Integer, ForeignKey("assets.id"), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, index=True)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, index=True)
    resolved_at = Column(DateTime, nullable=True)
    source_system = Column(String(50), default="import")
    is_active = Column(Boolean, default=True, index=True)

    events = relationship("TicketEvent", back_populates="ticket", cascade="all, delete-orphan")
    decisions = relationship(
        "DecisionRecord", back_populates="ticket", cascade="all, delete-orphan"
    )
    similar_from = relationship(
        "SimilarCaseLink",
        foreign_keys="SimilarCaseLink.ticket_id",
        back_populates="ticket",
        cascade="all, delete-orphan",
    )
    similar_to = relationship(
        "SimilarCaseLink",
        foreign_keys="SimilarCaseLink.similar_ticket_id",
        back_populates="similar_ticket",
        cascade="all, delete-orphan",
    )
    incident_links = relationship(
        "IncidentTicketLink", back_populates="ticket", cascade="all, delete-orphan"
    )
    asset = relationship("Asset", back_populates="tickets")

    @property
    def external_ticket_id(self) -> str:
        return str(self.ticket_id)

    @external_ticket_id.setter
    def external_ticket_id(self, value: str) -> None:
        self.ticket_id = value  # type: ignore[assignment]

    @property
    def priority_raw(self) -> str:
        return str(self.priority)

    @priority_raw.setter
    def priority_raw(self, value: str) -> None:
        self.priority = value  # type: ignore[assignment]

    @property
    def assignee(self) -> str | None:
        return self.staff_assigned  # type: ignore[return-value]

    @assignee.setter
    def assignee(self, value: str | None) -> None:
        self.staff_assigned = value  # type: ignore[assignment]

    @property
    def raw_description(self) -> str | None:
        return self.description  # type: ignore[return-value]

    @raw_description.setter
    def raw_description(self, value: str | None) -> None:
        self.description = value  # type: ignore[assignment]
