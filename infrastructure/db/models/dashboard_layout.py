from sqlalchemy import Column, Integer, String, DateTime, JSON, Boolean
from datetime import datetime

from infrastructure.db.base import Base


class DashboardLayout(Base):
    __tablename__ = "dashboard_layouts"

    id = Column(Integer, primary_key=True, autoincrement=True)
    owner_username = Column(String(100), nullable=False, index=True)  # or "global"
    name = Column(String(100), nullable=False)
    widgets_json = Column(JSON, nullable=False, default=list)  # [{ "id": , "type": "queue|chart|intel|gov|sla", "config": {...}, "position": {x,y,w,h} }]
    is_default = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
