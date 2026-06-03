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
  category_id?: number;
  created_at: string;
  resolved_at?: string;
  days_open: number;
  incident_id?: string;
  description?: string;
  resolution_notes?: string;
  requester?: string;
  labels?: TicketLabel[];
}

export interface Feedback {
  id: number;
  feedback_type: string;
  feedback_note?: string | null;
  operator_id?: string | null;
  feedback_ts?: string | null;
}

export interface ActionRun {
  id: number;
  recommendation_id: number;
  action_type: string;
  status: string;
  risk_level?: string | null;
  requested_by?: string | null;
  approved_by?: string | null;
  started_at?: string | null;
  finished_at?: string | null;
  rollback_available?: boolean;
  result_json?: unknown;
  rollback_metadata_json?: unknown;
  rollback_payload_json?: unknown;
  operator_note?: string | null;
  ticket_event_id?: number | null;
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
  recommended_runbook_id?: string | null;
  requires_approval?: boolean;
  status?: string;
  created_at?: string;
  last_feedback?: Feedback | null;
  latest_action_run?: ActionRun | null;
}

export interface GraphFeatures {
  ticket_id: string;
  graph_degree: number;
  graph_weighted_degree: number;
  edge_counts: Record<string, number>;
  neighbor_count: number;
  is_isolated: boolean;
  signal_density: number;
  graph_reasoning?: string;
}

export interface GraphEvidence {
  shared_site?: string;
  distinct_sites?: string[];
  shared_requester_count?: number;
  shared_assignee_count?: number;
  primary_requesters?: string[];
  primary_assignees?: string[];
  evidence_basis?: string;
  edge_counts?: Record<string, number>;
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
  decision_version?: string;
  rule_version?: string;
  model_version?: string | null;
  decision_band?: string | null;
  priority_interval_low?: number | null;
  priority_interval_high?: number | null;
  decision_hash?: string | null;
  graph_degree?: number | null;
  graph_weighted_degree?: number | null;
  graph_signal_density?: number | null;
  graph_reasoning?: string | null;
  band_rationale?: string | null;
  operator_action?: string | null;
  feature_snapshot_json?: Record<string, unknown> | null;
  explanation_json?: Record<string, unknown> | null;
  recommendations: Recommendation[];
}

export interface Incident {
  id: number;
  incident_key?: string | null;
  title: string;
  status: string;
  root_cause_hypothesis?: string | null;
  site_scope?: string | null;
  ticket_count: number;
  confidence: number;
  business_impact_score: number;
  opened_at?: string | null;
  last_updated_at?: string | null;
  graph_evidence?: GraphEvidence | null;
}

export interface IncidentDetail {
  incident: Incident;
  tickets: Array<{
    id?: number;
    ticket_id: string;
    title?: string;
    status?: string;
    priority_raw?: string;
    request_type?: string;
    assignee?: string;
    requester?: string;
    date_opened?: string;
    created_at?: string;
    link_confidence?: number;
  }>;
  common_cause?: string;
  recommended_action?: string;
  graph_evidence?: GraphEvidence | null;
}

export interface TicketLabel {
  id: number;
  name: string;
  color: string;
}

export interface TicketAttachment {
  id: number;
  original_name: string;
  mime_type: string;
  file_size: number;
  created_at?: string;
  uploaded_by?: string;
  comment_id?: number | null;
  url: string;
}

export interface TicketComment {
  id: number;
  ticket_id: string;
  author_username: string;
  author_display_name: string;
  body: string;
  created_at?: string;
  updated_at?: string;
  attachments: TicketAttachment[];
}

export interface TicketDetailPayload {
  ticket: Ticket & {
    request_type?: string;
  };
  decision?: Decision | null;
  recommendations: Recommendation[];
  similar_cases: Array<{
    ticket_id: string;
    title: string;
    status: string;
    priority_raw?: string;
    assignee?: string;
    date_opened?: string;
    similarity_score?: number;
  }>;
  events: Array<{
    event_type: string;
    event_ts: string;
    actor_type: string;
    actor_id?: string;
    payload?: Record<string, unknown>;
  }>;
  linked_incident?: { id: number; title?: string; incident_key?: string } | null;
  comments: TicketComment[];
  attachments: TicketAttachment[];
}

export interface CatalogCategory {
  id: number;
  name: string;
  color: string;
  icon: string;
  is_custom: boolean;
  is_active: boolean;
}

export interface CatalogOptions {
  categories: CatalogCategory[];
  labels: TicketLabel[];
  staff: string[];
  assignees: string[];
  requesters: string[];
  users: Array<{ username: string; role: string; display_name: string }>;
}

export interface ApplyRecommendationPayload {
  action_type?: string;
  override_priority?: number;
  confirm?: boolean;
  note?: string;
}

export interface ApplyRecommendationResponse {
  recommendation_id: number;
  action_run: ActionRun;
  event_id: number;
  ticket_state: Record<string, unknown>;
  rollback_available: boolean;
  rollback_payload: Record<string, unknown>;
  feedback: Feedback;
}

export interface IntelligenceHealthResponse {
  status: string;
  engine: {
    name: string;
    version: string;
    model_version: string | null;
    description: string;
  };
  scoring_weights: {
    version: string;
    severity: number;
    urgency: number;
    business_impact: number;
    sla_risk: number;
    recurrence: number;
    dependency_criticality: number;
    actionability: number;
    uncertainty_penalty: number;
  };
  subsystems: {
    decision_records: { count: number; last_decision_ts: string | null };
    recommendations: { count: number };
    operator_feedback: {
      count: number;
      by_type: Record<string, number>;
      last_feedback_ts: string | null;
    };
    action_runs: {
      count: number;
      by_status: Record<string, number>;
      last_started_at: string | null;
    };
    incidents: { count: number; stable_ids: boolean };
    retrieval: {
      similar_case_links: number;
      engine: string;
    };
    graph?: {
      node_count: number;
      edge_count: number;
      isolated_count: number;
      average_degree: number;
      average_weighted_degree: number;
      edges_by_type: Record<string, number>;
    };
    tickets: { count: number };
  };
  drift?: {
    status: "ok" | "watch" | "drift" | "unavailable";
    current_decision_count?: number;
    prior_decision_count?: number;
    priority_shift?: { delta: number; pct_change: number; drift_flag: boolean };
    uncertainty_shift?: { delta: number; pct_change: number; drift_flag: boolean };
    review_needed_rate_shift?: { delta: number; pct_change: number; drift_flag: boolean };
    root_cause_spikes?: Array<{ root_cause: string; current_count: number; prior_count: number; pct_change: number }>;
  };
  feedback_loop: {
    enabled: boolean;
    adjustment_cap: number;
    decay_factor: number;
    source: string;
  };
  truthful_disclosure: {
    no_external_llm: boolean;
    no_trained_ml_model: boolean;
    actions_are_real_workflow_mutations: boolean;
    runbooks_require_human_review: boolean;
    graph_features_are_deterministic?: boolean;
    decision_hash_is_deterministic?: boolean;
  };
}

export interface GovernanceSummaryResponse {
  drift: {
    status: "ok" | "watch" | "drift" | "unavailable";
    current_decision_count?: number;
    prior_decision_count?: number;
    priority_shift?: { delta: number; pct_change: number; drift_flag: boolean };
    uncertainty_shift?: { delta: number; pct_change: number; drift_flag: boolean };
    review_needed_rate_shift?: { delta: number; pct_change: number; drift_flag: boolean };
    root_cause_spikes?: Array<{
      root_cause: string;
      current_count: number;
      prior_count: number;
      pct_change: number;
    }>;
    rule_version?: string;
    engine?: string;
  };
  graph: {
    node_count: number;
    edge_count: number;
    isolated_count: number;
    average_degree: number;
    average_weighted_degree: number;
    edges_by_type: Record<string, number>;
  };
  card: {
    title: string;
    kind: string;
    issued_at: string;
    engine: {
      name: string;
      kind: string;
      version: string;
      decision_schema_version: string;
      model_version: string | null;
      external_llm: boolean;
      trained_ml_model: boolean;
    };
    what_this_engine_is: string[];
    what_this_engine_is_not: string[];
    inputs: string[];
    outputs: {
      decision_record: string[];
      recommendations: string[];
      incidents: string[];
    };
    scoring_weights: Record<string, number>;
    graph_weights: Record<string, number>;
    uncertainty_bands: {
      labels: string[];
      thresholds: Record<string, number>;
    };
    guardrails: string[];
    ownership: {
      team: string;
      review_cadence: string;
      override_path: string;
    };
  };
}
