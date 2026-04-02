from datetime import datetime

from sqlalchemy import Boolean, Column, DateTime, Integer, String

from infrastructure.db.base import Base


class Assignee(Base):
    __tablename__ = "assignees"

    id = Column(Integer, primary_key=True, autoincrement=True)
    display_name = Column(String(100), unique=True, nullable=False, index=True)
    is_active = Column(Boolean, default=True, index=True)
    created_at = Column(DateTime, default=datetime.utcnow)
