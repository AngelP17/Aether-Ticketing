"use client";

import Link from "next/link";

import { OpsShell } from "@/components/ops-shell";

type ReplayPayload = {
  ticket_id: string;
  latest_decision?: {
    priority_score?: number;
    root_cause_hypothesis?: string;
    decision_band?: string | null;
    decision_hash?: string | null;
  };
  decision_history: Array<{
    id: number;
    decision_ts: string;
    priority_score: number;
    root_cause_hypothesis: string;
    confidence_score: number;
    decision_band?: string | null;
    decision_hash?: string | null;
    priority_interval_low?: number | null;
    priority_interval_high?: number | null;
    graph_degree?: number | null;
    graph_weighted_degree?: number | null;
    anomaly_zscore?: number | null;
    explanation_json?: Record<string, unknown> | null;
  }>;
  events: Array<{ event_type: string; event_ts: string; actor_type: string }>;
  operator_feedback: Array<{
    feedback_type: string;
    feedback_note?: string;
    feedback_ts: string;
    operator_id?: string;
  }>;
  similar_cases: Array<{ ticket_id: string; title: string; status: string }>;
  action_runs?: Array<{
    id: number;
    status: string;
    action_type: string;
    started_at?: string | null;
    finished_at?: string | null;
    operator_note?: string | null;
  }>;
};

function formatScore(value?: number | null) {
  if (typeof value !== "number") {
    return "--";
  }
  return value.toFixed(1);
}

export function ReplayView({
  id,
  payload,
  error,
}: {
  id: string;
  payload?: ReplayPayload;
  error?: string;
}) {
  if (error) {
    return (
      <OpsShell
        eyebrow="Aether OpsCenter"
        title="Replay & Audit"
        subtitle={`Replay ${id}`}
        statusPill={{ kind: "error", label: "Disconnected" }}
      >
        <div className="mx-auto max-w-5xl">
          <div className="ops-card w-full rounded-2xl border border-rose-500/20 p-6 shadow-xl sm:p-8">
            <h1 className="text-2xl font-semibold text-white">Audit replay could not load</h1>
            <p className="mt-4 text-sm leading-7 text-slate-400">{error}</p>
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
      </OpsShell>
    );
  }

  if (!payload) {
    return null;
  }

  return (
    <OpsShell
      eyebrow="Aether OpsCenter"
      title="Replay & Audit"
      subtitle={`Audit replay for ${id}`}
      statusPill={{ kind: "ready", label: "Live" }}
      headerActions={
        <>
          <Link
            href={`/tickets/${id}`}
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
        </>
      }
      showNotificationBell
    >
      <div className="mx-auto max-w-5xl">
        <div className="ops-card rounded-2xl border border-slate-800 p-5 shadow-xl sm:p-8">
          <div className="flex flex-wrap items-center justify-between gap-4">
            <div>
              <h1 className="text-2xl font-semibold">Audit Replay {id}</h1>
            </div>
          </div>

          <div className="mt-6 space-y-6">
            <div className="grid gap-4 md:grid-cols-3">
              <div className="rounded-xl border border-slate-800 bg-slate-950/60 p-4">
                <div className="text-xs uppercase tracking-[0.2em] text-slate-500">Latest Score</div>
                <div className="mt-2 text-lg font-medium text-cyan-300">
                  {payload.latest_decision?.priority_score ?? "-"}
                </div>
                {payload.latest_decision?.decision_band ? (
                  <div className="mt-1 text-[10px] font-mono text-emerald-300">{payload.latest_decision.decision_band}</div>
                ) : null}
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
                {payload.latest_decision?.decision_hash ? (
                  <div className="mt-1 truncate text-[10px] font-mono text-amber-300" title={payload.latest_decision.decision_hash}>
                    {payload.latest_decision.decision_hash.slice(0, 12)}…
                  </div>
                ) : null}
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
                      <div className="mt-1 flex flex-wrap items-center gap-2 text-xs">
                        {decision.decision_band ? (
                          <span className="rounded border border-emerald-500/30 bg-emerald-500/10 px-1.5 py-0.5 font-mono text-emerald-200">{decision.decision_band}</span>
                        ) : null}
                        {decision.decision_hash ? (
                          <span className="font-mono text-amber-300" title={decision.decision_hash}>{decision.decision_hash.slice(0, 10)}…</span>
                        ) : null}
                        {(decision.graph_degree ?? 0) > 0 ? (
                          <span className="font-mono text-zinc-400">g{decision.graph_degree}</span>
                        ) : null}
                      </div>
                      <div className="mt-2 text-xs text-slate-500">{decision.decision_ts}</div>
                      <div className="mt-1 text-sm text-slate-400">
                        Confidence: {formatScore(decision.confidence_score)}
                        {decision.priority_interval_low != null && decision.priority_interval_high != null ? (
                          <> · interval {decision.priority_interval_low}–{decision.priority_interval_high}</>
                        ) : null}
                      </div>
                      {decision.explanation_json ? (
                        <div className="mt-1 text-[10px] text-slate-500">graph: {JSON.stringify(decision.explanation_json).slice(0, 80)}</div>
                      ) : null}
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

            <section className="rounded-2xl border border-slate-800 bg-slate-950/60 p-6">
              <h2 className="font-medium text-slate-200">Action Runs</h2>
              <div className="mt-4 space-y-3">
                {!payload.action_runs || payload.action_runs.length === 0 ? (
                  <div className="rounded-xl border border-dashed border-slate-700 bg-slate-950/50 p-4 text-sm text-slate-400">
                    No action runs recorded for this ticket (apply actions create entries here).
                  </div>
                ) : (
                  payload.action_runs.map((ar) => (
                    <div key={ar.id} className="rounded-xl border border-slate-800 p-4">
                      <div className="flex items-center justify-between">
                        <div className="font-medium text-slate-100">{ar.action_type}</div>
                        <span className="rounded border border-amber-500/30 bg-amber-500/10 px-2 py-0.5 text-xs font-mono text-amber-200">{ar.status}</span>
                      </div>
                      <div className="mt-1 text-xs text-slate-500">
                        {ar.started_at ? new Date(ar.started_at).toLocaleString() : ""} {ar.finished_at ? "→ " + new Date(ar.finished_at).toLocaleString() : ""}
                      </div>
                      {ar.operator_note ? <div className="mt-1 text-sm text-slate-400">{ar.operator_note}</div> : null}
                    </div>
                  ))
                )}
              </div>
            </section>
          </div>
        </div>
      </div>
    </OpsShell>
  );
}
