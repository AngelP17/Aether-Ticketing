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
  decision?: {
    priority_score?: number;
    confidence_score?: number;
    root_cause_hypothesis?: string;
    sla_risk_score?: number;
    actionability_score?: number;
    recurrence_score?: number;
  };
  recommendations: Array<{
    rank: number;
    action_label: string;
    rationale: string;
    confidence: number;
  }>;
  similar_cases: Array<{ ticket_id: string; title: string; status: string }>;
  events: Array<{ event_type: string; event_ts: string; actor_type: string; actor_id?: string; payload?: Record<string, unknown> }>;
  linked_incident?: { id: string; title?: string };
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
  requesters: string[];
  users: Array<{ username: string; role: string; display_name: string }>;
}
