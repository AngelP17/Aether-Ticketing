from sqlalchemy import Column, Integer, String, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from datetime import datetime

from infrastructure.db.base import Base


class OperatorFeedback(Base):
    __tablename__ = "operator_feedback"

    id = Column(Integer, primary_key=True, autoincrement=True)
    recommendation_id = Column(
        Integer, ForeignKey("recommendations.id", ondelete="CASCADE"), nullable=False, index=True
    )
    ticket_id = Column(
        Integer, ForeignKey("tickets.id", ondelete="CASCADE"), nullable=False, index=True
    )
    feedback_type = Column(String(30), nullable=False)
    feedback_note = Column(String(500))
    feedback_ts = Column(DateTime, default=datetime.utcnow)
    operator_id = Column(String(100))

    recommendation = relationship("Recommendation", back_populates="feedback")
