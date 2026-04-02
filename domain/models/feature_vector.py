from pydantic import BaseModel


class FeatureVectorModel(BaseModel):
    severity_score: float
    urgency_score: float
    business_impact_score: float
