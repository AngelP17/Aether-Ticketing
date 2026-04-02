from pydantic import BaseModel


class AuditRecordModel(BaseModel):
    entity_type: str
    entity_id: str
    version_tag: str | None = None
