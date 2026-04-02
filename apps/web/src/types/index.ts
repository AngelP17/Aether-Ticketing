export interface Ticket {
  ticket_id: string;
  title: string;
  status: string;
  priority_raw: string;
  priority_score?: number;
  root_cause_hypothesis?: string;
  confidence_score?: number;
  site?: string;
  assignee?: string;
  category?: string;
  created_at: string;
  resolved_at?: string;
  days_open: number;
  incident_id?: string;
}

export interface Decision {
  id: number;
  ticket_id: string;
  priority_score: number;
  severity_score: number;
  urgency_score: number;
  business_impact_score: number;
  sla_risk_score: number;
  recurrence_score: number;
  dependency_criticality_score: number;
  actionability_score: number;
  uncertainty_penalty: number;
  root_cause_hypothesis: string;
  confidence_score: number;
  decision_ts: string;
}

export interface Recommendation {
  id: number;
  rank: number;
  action_type: string;
  action_label: string;
  rationale: string;
  risk_level: string;
  confidence: number;
  expected_benefit: string;
  status: string;
}

export interface Incident {
  id: string;
  title: string;
  status: string;
  root_cause_hypothesis: string;
  ticket_count: number;
  confidence: number;
  business_impact_score: number;
  opened_at: string;
}
