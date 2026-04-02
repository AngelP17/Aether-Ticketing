from sqlalchemy import Column, Integer, String, JSON
from sqlalchemy.orm import relationship

from infrastructure.db.base import Base


class Asset(Base):
    __tablename__ = "assets"

    id = Column(Integer, primary_key=True, autoincrement=True)
    asset_name = Column(String(255), nullable=False, index=True)
    asset_type = Column(String(100))
    site_id = Column(String(100), index=True)
    criticality = Column(String(20), default="medium")
    owner_team = Column(String(100))
    dependency_json = Column(JSON)

    tickets = relationship("Ticket", back_populates="asset")
