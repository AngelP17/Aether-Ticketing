from datetime import datetime

from sqlalchemy import Column, DateTime, Integer, String, Float, Boolean, ForeignKey
from sqlalchemy.orm import relationship

from infrastructure.db.base import Base


class Recommendation(Base):
    __tablename__ = "recommendations"

    id = Column(Integer, primary_key=True, autoincrement=True)
    decision_record_id = Column(
        Integer, ForeignKey("decision_records.id", ondelete="CASCADE"), nullable=False, index=True
    )
    rank = Column(Integer, nullable=False)
    action_type = Column(String(50), nullable=False)
    action_label = Column(String(255), nullable=False)
    rationale = Column(String(500))
    risk_level = Column(String(20), default="low")
    expected_benefit = Column(String(255))
    confidence = Column(Float, default=0.0)
    requires_approval = Column(Boolean, default=False)
    recommended_runbook_id = Column(String(50), nullable=True)
    status = Column(String(20), default="proposed", index=True)
    created_at = Column(DateTime, default=datetime.utcnow, index=True)

    decision_record = relationship("DecisionRecord", back_populates="recommendations")
    feedback = relationship("OperatorFeedback", back_populates="recommendation", uselist=False)
    action_runs = relationship(
        "ActionRun", back_populates="recommendation", cascade="all, delete-orphan"
    )
