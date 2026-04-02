from sqlalchemy import Column, Integer, String, DateTime, JSON

from infrastructure.db.base import Base


class AuditRecord(Base):
    __tablename__ = "audit_records"

    id = Column(Integer, primary_key=True, autoincrement=True)
    entity_type = Column(String(30), nullable=False, index=True)
    entity_id = Column(String(50), nullable=False, index=True)
    snapshot_ts = Column(DateTime, nullable=False, index=True)
    snapshot_json = Column(JSON, nullable=False)
    version_tag = Column(String(30))
    reason = Column(String(100))
