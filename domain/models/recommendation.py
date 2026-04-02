from pydantic import BaseModel


class RecommendationModel(BaseModel):
    rank: int
    action_type: str
    action_label: str
