from pydantic import BaseModel


class ActionRunModel(BaseModel):
    recommendation_id: int
    action_type: str
    status: str
