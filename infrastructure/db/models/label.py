from datetime import datetime

from sqlalchemy import Column, DateTime, Integer, String

from infrastructure.db.base import Base


class Label(Base):
    __tablename__ = "labels"

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(50), unique=True, nullable=False)
    color = Column(String(7), default="#3b82f6")
    created_at = Column(DateTime, default=datetime.utcnow)
