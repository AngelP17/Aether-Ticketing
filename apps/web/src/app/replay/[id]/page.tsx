import Link from "next/link";
import { notFound } from "next/navigation";

import { getServerApiUrl } from "@/lib/server-api";

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

function formatScore(value?: number | null) {
  if (typeof value !== "number") {
    return "--";
  }
  return value.toFixed(1);
}

function ReplayErrorState({ id, message }: { id: string; message: string }) {
  return (
    <div className="min-h-screen bg-slate-950 p-8 text-slate-50">
      <div className="mx-auto flex min-h-[calc(100vh-4rem)] max-w-5xl items-center">
        <div className="w-full rounded-2xl border border-rose-500/20 bg-slate-900/80 p-8 shadow-xl">
          <div className="text-xs uppercase tracking-[0.3em] text-rose-300">Replay API error</div>
          <h1 className="mt-2 text-2xl font-semibold text-white">Audit replay could not load</h1>
          <p className="mt-4 text-sm leading-7 text-slate-400">{message}</p>
          <div className="mt-6 flex flex-wrap gap-3">
            <Link
              href={`/replay/${id}`}
              className="rounded-full border border-rose-500/30 bg-rose-500/10 px-4 py-2 text-sm text-rose-100 transition hover:border-rose-400 hover:bg-rose-500/15"
            >
              Retry load
            </Link>
            <Link
              href="/command-center"
              className="rounded-full border border-slate-700 px-4 py-2 text-sm text-slate-300 transition hover:border-cyan-300 hover:text-cyan-200"
            >
              Command center
            </Link>
          </div>
        </div>
      </div>
    </div>
  );
}

export default async function ReplayPage({ params }: { params: { id: string } }) {
  const result = await getReplay(params.id);

  if (result.kind === "not_found") {
    notFound();
  }

  if (result.kind === "error") {
    return <ReplayErrorState id={params.id} message={result.message} />;
  }

  const payload = result.data;

  return (
    <div className="min-h-screen bg-slate-950 p-8 text-slate-50">
      <div className="mx-auto max-w-5xl rounded-2xl border border-slate-800 bg-slate-900/80 p-8 shadow-xl">
        <div className="flex flex-wrap items-center justify-between gap-4">
          <div>
            <p className="text-xs uppercase tracking-[0.3em] text-cyan-300">Replay & Audit</p>
            <h1 className="mt-2 text-2xl font-semibold">Audit Replay {params.id}</h1>
          </div>
          <div className="flex gap-3">
            <Link
              href={`/tickets/${params.id}`}
              className="rounded-full border border-slate-700 px-4 py-2 text-sm text-slate-300 transition hover:border-cyan-300 hover:text-cyan-200"
            >
              Ticket case
            </Link>
            <Link
              href="/command-center"
              className="rounded-full border border-slate-700 px-4 py-2 text-sm text-slate-300 transition hover:border-cyan-300 hover:text-cyan-200"
            >
              Command center
            </Link>
          </div>
        </div>

        <div className="mt-6 space-y-6">
          <div className="grid gap-4 md:grid-cols-3">
            <div className="rounded-xl border border-slate-800 bg-slate-950/60 p-4">
              <div className="text-xs uppercase tracking-[0.2em] text-slate-500">Latest Score</div>
              <div className="mt-2 text-lg font-medium text-cyan-300">
                {payload.latest_decision?.priority_score ?? "-"}
              </div>
            </div>
            <div className="rounded-xl border border-slate-800 bg-slate-950/60 p-4">
              <div className="text-xs uppercase tracking-[0.2em] text-slate-500">Root Cause</div>
              <div className="mt-2 text-lg font-medium text-slate-100">
                {payload.latest_decision?.root_cause_hypothesis ?? "-"}
              </div>
            </div>
            <div className="rounded-xl border border-slate-800 bg-slate-950/60 p-4">
              <div className="text-xs uppercase tracking-[0.2em] text-slate-500">Decisions Recorded</div>
              <div className="mt-2 text-lg font-medium text-slate-100">{payload.decision_history.length}</div>
            </div>
          </div>

          <section className="rounded-2xl border border-slate-800 bg-slate-950/60 p-6">
            <h2 className="font-medium text-slate-200">Decision History</h2>
            <div className="mt-4 space-y-3">
              {payload.decision_history.length === 0 ? (
                <div className="rounded-xl border border-dashed border-slate-700 bg-slate-950/50 p-4 text-sm text-slate-400">
                  No stored decisions have been recorded for this ticket yet.
                </div>
              ) : (
                payload.decision_history.map((decision) => (
                  <div key={decision.id} className="rounded-xl border border-slate-800 p-4">
                    <div className="flex items-center justify-between gap-3">
                      <div className="font-medium text-slate-100">{decision.root_cause_hypothesis}</div>
                      <div className="text-xs text-cyan-300">{formatScore(decision.priority_score)}</div>
                    </div>
                    <div className="mt-2 text-xs text-slate-500">{decision.decision_ts}</div>
                    <div className="mt-2 text-sm text-slate-400">
                      Confidence: {formatScore(decision.confidence_score)}
                    </div>
                  </div>
                ))
              )}
            </div>
          </section>

          <section className="rounded-2xl border border-slate-800 bg-slate-950/60 p-6">
            <h2 className="font-medium text-slate-200">Event Timeline</h2>
            <div className="mt-4 space-y-4">
              {payload.events.length === 0 ? (
                <div className="rounded-xl border border-dashed border-slate-700 bg-slate-950/50 p-4 text-sm text-slate-400">
                  No events were recorded for this replay.
                </div>
              ) : (
                payload.events.map((event, index) => (
                  <div key={`${event.event_type}-${index}`} className="rounded-xl border border-slate-800 p-4">
                    <div className="font-medium text-slate-100">{event.event_type}</div>
                    <div className="text-xs text-slate-400">{event.event_ts}</div>
                    <div className="mt-2 text-sm text-slate-300">Actor: {event.actor_type}</div>
                  </div>
                ))
              )}
            </div>
          </section>

          <div className="grid gap-6 lg:grid-cols-2">
            <section className="rounded-2xl border border-slate-800 bg-slate-950/60 p-6">
              <h2 className="font-medium text-slate-200">Operator Feedback</h2>
              <div className="mt-4 space-y-3">
                {payload.operator_feedback.length === 0 ? (
                  <div className="rounded-xl border border-dashed border-slate-700 bg-slate-950/50 p-4 text-sm text-slate-400">
                    No operator feedback has been recorded yet.
                  </div>
                ) : (
                  payload.operator_feedback.map((feedback, index) => (
                    <div key={`${feedback.feedback_ts}-${index}`} className="rounded-xl border border-slate-800 p-4">
                      <div className="font-medium text-slate-100">{feedback.feedback_type}</div>
                      <div className="mt-1 text-xs text-slate-500">{feedback.feedback_ts}</div>
                      <div className="mt-2 text-sm text-slate-400">{feedback.feedback_note || "No note provided."}</div>
                      <div className="mt-2 text-xs uppercase tracking-[0.2em] text-slate-500">
                        {feedback.operator_id || "system"}
                      </div>
                    </div>
                  ))
                )}
              </div>
            </section>

            <section className="rounded-2xl border border-slate-800 bg-slate-950/60 p-6">
              <h2 className="font-medium text-slate-200">Similar Cases</h2>
              <div className="mt-4 space-y-3">
                {payload.similar_cases.length === 0 ? (
                  <div className="rounded-xl border border-dashed border-slate-700 bg-slate-950/50 p-4 text-sm text-slate-400">
                    No similar cases are linked yet.
                  </div>
                ) : (
                  payload.similar_cases.map((ticket) => (
                    <Link
                      key={ticket.ticket_id}
                      href={`/tickets/${ticket.ticket_id}`}
                      className="block rounded-xl border border-slate-800 p-4 transition hover:border-cyan-300/50"
                    >
                      <div className="font-medium text-slate-100">{ticket.ticket_id}</div>
                      <div className="mt-1 text-sm text-slate-400">{ticket.title}</div>
                      <div className="mt-2 text-xs uppercase tracking-[0.2em] text-slate-500">{ticket.status}</div>
                    </Link>
                  ))
                )}
              </div>
            </section>
          </div>
        </div>
      </div>
    </div>
  );
}
