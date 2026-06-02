import { notFound } from "next/navigation";

import { IncidentDetailView } from "@/components/incidents/incident-detail-view";
import { getServerApiUrl } from "@/lib/server-api";

export const dynamic = "force-dynamic";

type LoadState<T> =
  | { kind: "ok"; data: T }
  | { kind: "not_found" }
  | { kind: "error"; message: string };

type IncidentDetailPayload = {
  incident: {
    title: string;
    status: string;
    ticket_count: number;
    confidence?: number;
    business_impact_score?: number;
    opened_at?: string;
  };
  common_cause: string;
  recommended_action: string;
  tickets: Array<{
    ticket_id: string;
    title: string;
    status: string;
    priority_score?: number;
  }>;
};

async function getIncident(id: string): Promise<LoadState<IncidentDetailPayload>> {
  try {
    const response = await fetch(getServerApiUrl(`/api/incidents/${id}`), {
      cache: "no-store",
    });
    if (response.status === 404) {
      return { kind: "not_found" };
    }
    if (!response.ok) {
      return {
        kind: "error",
        message: `Incident API returned ${response.status} ${response.statusText || "without a status message"}.`,
      };
    }
    return { kind: "ok", data: (await response.json()) as IncidentDetailPayload };
  } catch (error) {
    return {
      kind: "error",
      message: error instanceof Error ? error.message : "Unable to reach the incident API.",
    };
  }
}

export default async function IncidentDetailPage({ params }: { params: { id: string } }) {
  const result = await getIncident(params.id);

  if (result.kind === "not_found") {
    notFound();
  }

  if (result.kind === "error") {
    return <IncidentDetailView id={params.id} error={result.message} />;
  }

  return <IncidentDetailView id={params.id} payload={result.data} />;
}
