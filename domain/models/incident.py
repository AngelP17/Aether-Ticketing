from pydantic import BaseModel


class IncidentModel(BaseModel):
    id: str
    title: str
    status: str
    root_cause_hypothesis: str
