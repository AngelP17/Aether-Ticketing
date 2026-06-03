from sqlalchemy import Column, Integer, String, DateTime, Boolean, Float
from datetime import datetime

from infrastructure.db.base import Base


class SlaPolicy(Base):
    __tablename__ = "sla_policies"

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(100), nullable=False)
    priority = Column(String(20), nullable=True, index=True)  # e.g. match ticket priority or *
    category = Column(String(100), nullable=True, index=True)
    target_hours = Column(Float, nullable=False)  # e.g. 24.0
    warn_at_percent = Column(Float, default=75.0)
    breach_action = Column(String(50), default="escalate")  # or notify etc
    active = Column(Boolean, default=True, index=True)
    created_at = Column(DateTime, default=datetime.utcnow)
