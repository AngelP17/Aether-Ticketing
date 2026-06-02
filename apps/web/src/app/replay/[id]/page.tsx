import { notFound } from "next/navigation";

import { ReplayView } from "@/components/replay/replay-view";
import { getServerApiUrl } from "@/lib/server-api";

export const dynamic = "force-dynamic";

type LoadState<T> =
  | { kind: "ok"; data: T }
  | { kind: "not_found" }
  | { kind: "error"; message: string };

type ReplayPayload = {
  ticket_id: string;
  latest_decision?: {
    priority_score?: number;
    root_cause_hypothesis?: string;
  };
  decision_history: Array<{
    id: number;
    decision_ts: string;
    priority_score: number;
    root_cause_hypothesis: string;
    confidence_score: number;
  }>;
  events: Array<{ event_type: string; event_ts: string; actor_type: string }>;
  operator_feedback: Array<{
    feedback_type: string;
    feedback_note?: string;
    feedback_ts: string;
    operator_id?: string;
  }>;
  similar_cases: Array<{ ticket_id: string; title: string; status: string }>;
};

async function getReplay(id: string): Promise<LoadState<ReplayPayload>> {
  try {
    const response = await fetch(getServerApiUrl(`/api/replay/${id}`), {
      cache: "no-store",
    });
    if (response.status === 404) {
      return { kind: "not_found" };
    }
    if (!response.ok) {
      return {
        kind: "error",
        message: `Replay API returned ${response.status} ${response.statusText || "without a status message"}.`,
      };
    }
    return { kind: "ok", data: (await response.json()) as ReplayPayload };
  } catch (error) {
    return {
      kind: "error",
      message: error instanceof Error ? error.message : "Unable to reach the replay API.",
    };
  }
}

export default async function ReplayPage({ params }: { params: { id: string } }) {
  const result = await getReplay(params.id);

  if (result.kind === "not_found") {
    notFound();
  }

  if (result.kind === "error") {
    return <ReplayView id={params.id} error={result.message} />;
  }

  return <ReplayView id={params.id} payload={result.data} />;
}
