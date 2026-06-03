from sqlalchemy import Column, Integer, String, DateTime, Float, JSON, ForeignKey
from sqlalchemy.orm import relationship
from datetime import datetime

from infrastructure.db.base import Base


class DecisionRecord(Base):
    __tablename__ = "decision_records"

    id = Column(Integer, primary_key=True, autoincrement=True)
    ticket_id = Column(
        Integer, ForeignKey("tickets.id", ondelete="CASCADE"), nullable=False, index=True
    )
    incident_id = Column(Integer, ForeignKey("incidents.id", ondelete="SET NULL"), nullable=True)
    decision_ts = Column(DateTime, default=datetime.utcnow, index=True)
    feature_snapshot_json = Column(JSON)
    severity_score = Column(Float, default=0.0)
    urgency_score = Column(Float, default=0.0)
    business_impact_score = Column(Float, default=0.0)
    sla_risk_score = Column(Float, default=0.0)
    recurrence_score = Column(Float, default=0.0)
    dependency_criticality_score = Column(Float, default=0.0)
    actionability_score = Column(Float, default=0.0)
    uncertainty_penalty = Column(Float, default=0.0)
    priority_score = Column(Float, default=0.0, index=True)
    root_cause_hypothesis = Column(String(100))
    confidence_score = Column(Float, default=0.0)
    decision_version = Column(String(20), default="v1")
    rule_version = Column(String(20), default="rules-2024-Q1")
    model_version = Column(String(20), nullable=True)
    decision_band = Column(String(40), nullable=True, index=True)
    priority_interval_low = Column(Float, nullable=True)
    priority_interval_high = Column(Float, nullable=True)
    decision_hash = Column(String(64), nullable=True, index=True)
    graph_degree = Column(Integer, default=0)
    graph_weighted_degree = Column(Float, default=0.0)
    anomaly_zscore = Column(Float, nullable=True)
    explanation_json = Column(JSON)

    ticket = relationship("Ticket", back_populates="decisions")
    recommendations = relationship(
        "Recommendation", back_populates="decision_record", cascade="all, delete-orphan"
    )
