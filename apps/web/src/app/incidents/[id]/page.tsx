"use client";

import { useEffect, useState } from "react";
import { useParams } from "next/navigation";

import { IncidentDetailView } from "@/components/incidents/incident-detail-view";
import { incidentsApi } from "@/lib/api";

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

export default function IncidentDetailPage() {
  const params = useParams<{ id: string }>();
  const id = params?.id || "";

  const [result, setResult] = useState<LoadState<IncidentDetailPayload> | null>(null);

  useEffect(() => {
    if (!id) return;

    const load = async () => {
      try {
        const response = await incidentsApi.get(id);
        if (response.status === 404) {
          setResult({ kind: "not_found" });
          return;
        }
        setResult({ kind: "ok", data: response.data as IncidentDetailPayload });
      } catch (error) {
        setResult({
          kind: "error",
          message: error instanceof Error ? error.message : "Unable to reach the incident API.",
        });
      }
    };

    void load();
  }, [id]);

  if (!result) {
    return <IncidentDetailView id={id} error={undefined} />;
  }

  if (result.kind === "not_found") {
    // For client, we can show a not found UI or redirect, but component handles error
    return <IncidentDetailView id={id} error="Incident not found" />;
  }

  if (result.kind === "error") {
    return <IncidentDetailView id={id} error={result.message} />;
  }

  return <IncidentDetailView id={id} payload={result.data} />;
}
