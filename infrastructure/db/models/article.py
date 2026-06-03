from sqlalchemy import Column, Integer, String, DateTime, Text, ForeignKey
from sqlalchemy.orm import relationship
from datetime import datetime

from infrastructure.db.base import Base


class Article(Base):
    __tablename__ = "articles"

    id = Column(Integer, primary_key=True, autoincrement=True)
    title = Column(String(200), nullable=False)
    body = Column(Text, nullable=False)
    root_cause_class = Column(String(100), nullable=True, index=True)  # link to root cause for recs/portal
    author_id = Column(String(100), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, index=True)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Optional: if linking incidents or decisions later
