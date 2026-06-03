from sqlalchemy import Column, Integer, String, DateTime, JSON
from datetime import datetime

from infrastructure.db.base import Base


class UserPreference(Base):
    __tablename__ = "user_preferences"

    id = Column(Integer, primary_key=True, autoincrement=True)
    username = Column(String(100), nullable=False, index=True)
    key = Column(String(100), nullable=False, index=True)  # e.g. "theme", "dashboard_layout_id"
    value_json = Column(JSON, nullable=True)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    __table_args__ = (
        # unique per user+key
    )
