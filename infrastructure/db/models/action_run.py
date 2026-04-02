from sqlalchemy import Column, Integer, String, DateTime, JSON, ForeignKey
from sqlalchemy.orm import relationship
from datetime import datetime

from infrastructure.db.base import Base


class ActionRun(Base):
    __tablename__ = "action_runs"

    id = Column(Integer, primary_key=True, autoincrement=True)
    recommendation_id = Column(
        Integer, ForeignKey("recommendations.id", ondelete="CASCADE"), nullable=False, index=True
    )
    action_type = Column(String(50), nullable=False)
    risk_level = Column(String(20), default="low")
    requested_by = Column(String(100))
    approved_by = Column(String(100), nullable=True)
    started_at = Column(DateTime, default=datetime.utcnow)
    finished_at = Column(DateTime, nullable=True)
    status = Column(String(20), default="pending", index=True)
    result_json = Column(JSON, nullable=True)
    rollback_available = Column(Integer, default=0)
    rollback_metadata_json = Column(JSON, nullable=True)

    recommendation = relationship("Recommendation", back_populates="action_runs")
