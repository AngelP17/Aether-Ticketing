from datetime import datetime

from sqlalchemy import Boolean, Column, DateTime, Integer, String

from infrastructure.db.base import Base


class Category(Base):
    __tablename__ = "categories"

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(100), unique=True, nullable=False)
    color = Column(String(7), default="#6366f1")
    icon = Column(String(50), default="fa-tag")
    is_custom = Column(Boolean, default=False)
    is_active = Column(Boolean, default=True)
    sort_order = Column(Integer, default=0)
    created_at = Column(DateTime, default=datetime.utcnow)
