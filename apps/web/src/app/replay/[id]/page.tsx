"use client";

import { useEffect, useState } from "react";
import { useParams } from "next/navigation";

import { ReplayView } from "@/components/replay/replay-view";
import { replayApi } from "@/lib/api";  // assuming it will be added or use direct; we'll use fetch with token via api if possible

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

export default function ReplayPage() {
  const params = useParams<{ id: string }>();
  const id = params?.id || "";

  const [result, setResult] = useState<LoadState<ReplayPayload> | null>(null);

  useEffect(() => {
    if (!id) return;

    const load = async () => {
      try {
        const response = await replayApi.get(id);
        if (response.status === 404) {
          setResult({ kind: "not_found" });
          return;
        }
        setResult({ kind: "ok", data: response.data as ReplayPayload });
      } catch (error) {
        setResult({
          kind: "error",
          message: error instanceof Error ? error.message : "Unable to reach the replay API.",
        });
      }
    };

    void load();
  }, [id]);

  if (!result) {
    return <ReplayView id={id} error={undefined} />;
  }

  if (result.kind === "not_found") {
    return <ReplayView id={id} error="Replay not found" />;
  }

  if (result.kind === "error") {
    return <ReplayView id={id} error={result.message} />;
  }

  return <ReplayView id={id} payload={result.data} />;
}
