from pydantic import BaseModel


class DecisionRecordModel(BaseModel):
    ticket_id: str
    priority_score: float
    root_cause_hypothesis: str
