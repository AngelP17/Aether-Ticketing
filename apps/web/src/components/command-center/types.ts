export type QueueTicket = {
  ticketId: string;
  title: string;
  status: string;
  priority: string;
  score: number;
  assignee: string;
  category: string;
  daysOpen: number;
  createdAt?: string;
  incidentId?: string;
  recommendation: string;
  requester?: string;
};

export type IncidentCard = {
  id: string;
  title: string;
  rootCause: string;
  ticketCount: number;
  confidence: number;
  impact: number;
};

export type BreakdownItem = {
  label: string;
  value: number;
  color: string;
};

export type TrendData = {
  labels: string[];
  created: number[];
  resolved: number[];
};
