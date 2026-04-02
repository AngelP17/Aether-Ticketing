from datetime import datetime

from sqlalchemy import Column, DateTime, ForeignKey, Integer, String, Text

from infrastructure.db.base import Base


class TicketComment(Base):
    __tablename__ = "ticket_comments"

    id = Column(Integer, primary_key=True, autoincrement=True)
    ticket_id = Column(
        String(20),
        ForeignKey("tickets.ticket_id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    author_username = Column(String(100), nullable=False, index=True)
    author_display_name = Column(String(100), nullable=False)
    body = Column(Text, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, index=True)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
