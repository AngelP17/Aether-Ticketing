import Link from "next/link";
import { notFound } from "next/navigation";

import { getServerApiUrl } from "@/lib/server-api";

type LoadState<T> =
  | { kind: "ok"; data: T }
  | { kind: "not_found" }
  | { kind: "error"; message: string };

type TicketDetailPayload = {
  ticket: {
    title: string;
    status: string;
    priority_raw: string;
    category?: string;
    requester?: string;
    assignee?: string;
    description?: string;
    resolution_notes?: string;
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
  events: Array<{ event_type: string; event_ts: string; actor_type: string }>;
  linked_incident?: { id: string; title?: string };
};

async function getTicket(id: string): Promise<LoadState<TicketDetailPayload>> {
  try {
    const response = await fetch(getServerApiUrl(`/api/tickets/${id}`), {
      cache: "no-store",
    });
    if (response.status === 404) {
      return { kind: "not_found" };
    }
    if (!response.ok) {
      return {
        kind: "error",
        message: `Ticket API returned ${response.status} ${response.statusText || "without a status message"}.`,
      };
    }
    return { kind: "ok", data: (await response.json()) as TicketDetailPayload };
  } catch (error) {
    return {
      kind: "error",
      message: error instanceof Error ? error.message : "Unable to reach the ticket API.",
    };
  }
}

function formatScore(value?: number | null) {
  if (typeof value !== "number") {
    return "--";
  }
  return value.toFixed(1);
}

function formatPercent(value?: number | null) {
  if (typeof value !== "number") {
    return "--";
  }
  return `${Math.round(value)}%`;
}

function priorityTone(priority?: string | null) {
  const normalized = (priority || "").toLowerCase();
  if (normalized === "critical") {
    return "border-rose-500/30 bg-rose-500/10 text-rose-100";
  }
  if (normalized === "high") {
    return "border-amber-500/30 bg-amber-500/10 text-amber-100";
  }
  if (normalized === "medium") {
    return "border-yellow-500/30 bg-yellow-500/10 text-yellow-100";
  }
  return "border-emerald-500/30 bg-emerald-500/10 text-emerald-100";
}

function riskTone(value?: number | null) {
  if (typeof value !== "number") {
    return "text-slate-200";
  }
  if (value >= 75) {
    return "text-rose-200";
  }
  if (value >= 45) {
    return "text-amber-200";
  }
  return "text-emerald-200";
}

function TicketErrorState({ id, message }: { id: string; message: string }) {
  return (
    <div className="min-h-screen bg-[#060816] px-4 py-5 text-slate-50 sm:px-6 lg:px-8">
      <div className="mx-auto flex min-h-[calc(100vh-2.5rem)] max-w-7xl items-center">
        <div className="w-full rounded-[2rem] border border-rose-500/20 bg-black/20 p-8 shadow-2xl shadow-black/30 backdrop-blur-xl">
          <div className="text-xs uppercase tracking-[0.28em] text-rose-300">Ticket API error</div>
          <h1 className="mt-3 text-3xl font-semibold tracking-tight text-white">This case could not load</h1>
          <p className="mt-4 max-w-3xl text-sm leading-7 text-slate-400">{message}</p>
          <div className="mt-6 flex flex-wrap gap-3">
            <Link
              href="/command-center"
              className="rounded-2xl border border-white/10 bg-white/5 px-4 py-3 text-sm font-medium text-slate-200 transition hover:border-cyan-300/40 hover:bg-cyan-400/10 hover:text-white"
            >
              Back to queue
            </Link>
            <Link
              href={`/tickets/${id}`}
              className="rounded-2xl border border-rose-500/30 bg-rose-500/10 px-4 py-3 text-sm font-medium text-rose-100 transition hover:border-rose-400/40 hover:bg-rose-500/15"
            >
              Retry load
            </Link>
          </div>
        </div>
      </div>
    </div>
  );
}

export default async function TicketCasePage({ params }: { params: { id: string } }) {
  const result = await getTicket(params.id);

  if (result.kind === "not_found") {
    notFound();
  }

  if (result.kind === "error") {
    return <TicketErrorState id={params.id} message={result.message} />;
  }

  const payload = result.data;

  return (
    <div className="min-h-screen bg-[#060816] px-4 py-5 text-slate-50 sm:px-6 lg:px-8">
      <div className="mx-auto max-w-7xl">
        <div className="rounded-[2rem] border border-white/8 bg-black/20 shadow-2xl shadow-black/30 backdrop-blur-xl">
          <div className="border-b border-white/6 px-5 py-5 sm:px-7">
            <div className="flex flex-col gap-5 lg:flex-row lg:items-start lg:justify-between">
              <div className="min-w-0">
                <div className="flex flex-wrap items-center gap-3 text-xs uppercase tracking-[0.28em] text-cyan-200">
                  <span>Ticket Case View</span>
                  <span className="h-1 w-1 rounded-full bg-slate-600" />
                  <span>{params.id}</span>
                </div>
                <h1 className="mt-3 text-3xl font-semibold tracking-tight text-white sm:text-4xl">
                  {payload.ticket.title}
                </h1>
                <p className="mt-3 max-w-3xl text-sm leading-6 text-slate-400">
                  Decision context, recommendation stack, and supporting history for a single operational case.
                </p>
              </div>

              <div className="flex flex-wrap gap-3">
                <Link
                  href="/command-center"
                  className="rounded-2xl border border-white/10 bg-white/5 px-4 py-3 text-sm font-medium text-slate-200 transition hover:border-cyan-300/40 hover:bg-cyan-400/10 hover:text-white"
                >
                  Back to queue
                </Link>
                <Link
                  href={`/replay/${params.id}`}
                  className="rounded-2xl border border-amber-500/30 bg-amber-500/10 px-4 py-3 text-sm font-medium text-amber-100 transition hover:border-amber-400/40 hover:bg-amber-500/15"
                >
                  Open audit replay
                </Link>
                {payload.linked_incident ? (
                  <Link
                    href={`/incidents/${payload.linked_incident.id}`}
                    className="rounded-2xl border border-cyan-400/30 bg-cyan-400/10 px-4 py-3 text-sm font-medium text-cyan-100 transition hover:border-cyan-300/40 hover:bg-cyan-400/15"
                  >
                    Open linked incident
                  </Link>
                ) : null}
              </div>
            </div>
          </div>

          <div className="space-y-6 px-5 py-6 sm:px-7">
            <section className="grid gap-4 md:grid-cols-2 xl:grid-cols-4">
              <div className="rounded-[1.5rem] border border-white/8 bg-gradient-to-br from-slate-900/95 to-slate-950/80 p-5">
                <div className="text-xs uppercase tracking-[0.24em] text-slate-500">Status</div>
                <div className="mt-3 text-2xl font-semibold text-white">{payload.ticket.status}</div>
                <div className="mt-2 text-sm text-slate-400">Current operating state of the case.</div>
              </div>
              <div className="rounded-[1.5rem] border border-white/8 bg-gradient-to-br from-slate-900/95 to-slate-950/80 p-5">
                <div className="text-xs uppercase tracking-[0.24em] text-slate-500">Priority</div>
                <div className="mt-3">
                  <span className={`rounded-full border px-3 py-1 text-sm font-medium ${priorityTone(payload.ticket.priority_raw)}`}>
                    {payload.ticket.priority_raw}
                  </span>
                </div>
                <div className="mt-4 text-sm text-slate-400">Raw queue priority preserved from the source system.</div>
              </div>
              <div className="rounded-[1.5rem] border border-white/8 bg-gradient-to-br from-cyan-500/10 to-slate-950/80 p-5">
                <div className="text-xs uppercase tracking-[0.24em] text-slate-500">Decision Score</div>
                <div className="mt-3 text-3xl font-semibold text-cyan-200">{formatScore(payload.decision?.priority_score)}</div>
                <div className="mt-2 text-sm text-slate-400">Current ranked decision priority.</div>
              </div>
              <div className="rounded-[1.5rem] border border-white/8 bg-gradient-to-br from-violet-500/10 to-slate-950/80 p-5">
                <div className="text-xs uppercase tracking-[0.24em] text-slate-500">Confidence</div>
                <div className="mt-3 text-3xl font-semibold text-violet-200">
                  {formatPercent(payload.decision?.confidence_score)}
                </div>
                <div className="mt-2 text-sm text-slate-400">How strongly the current hypothesis is supported.</div>
              </div>
            </section>

            <section className="grid gap-6 xl:grid-cols-[1.2fr,0.8fr]">
              <div className="rounded-[1.75rem] border border-white/8 bg-white/[0.03] p-6 shadow-xl shadow-black/20">
                <div className="flex flex-wrap items-start justify-between gap-4">
                  <div>
                    <p className="text-xs uppercase tracking-[0.24em] text-cyan-200">Case Summary</p>
                    <h2 className="mt-2 text-2xl font-semibold text-white">{payload.ticket.title}</h2>
                  </div>
                  <div className="flex flex-wrap gap-2 text-xs text-slate-300">
                    <span className="rounded-full border border-white/10 bg-white/5 px-3 py-1">
                      Category: {payload.ticket.category || "-"}
                    </span>
                    <span className="rounded-full border border-white/10 bg-white/5 px-3 py-1">
                      Requester: {payload.ticket.requester || "-"}
                    </span>
                    <span className="rounded-full border border-white/10 bg-white/5 px-3 py-1">
                      Assignee: {payload.ticket.assignee || "-"}
                    </span>
                  </div>
                </div>

                <div className="mt-6 rounded-[1.25rem] border border-white/6 bg-slate-950/50 p-5">
                  <div className="text-xs uppercase tracking-[0.22em] text-slate-500">Original Description</div>
                  <p className="mt-3 text-sm leading-7 text-slate-300">
                    {payload.ticket.description || "No original description is available for this case."}
                  </p>
                </div>

                {payload.ticket.resolution_notes ? (
                  <div className="mt-5 rounded-[1.25rem] border border-emerald-500/20 bg-emerald-500/10 p-5">
                    <div className="text-xs uppercase tracking-[0.22em] text-emerald-200">Resolution Notes</div>
                    <p className="mt-3 text-sm leading-7 text-emerald-50">{payload.ticket.resolution_notes}</p>
                  </div>
                ) : null}
              </div>

              <div className="space-y-6">
                <section className="rounded-[1.75rem] border border-white/8 bg-white/[0.03] p-6 shadow-xl shadow-black/20">
                  <div className="flex items-center justify-between gap-3">
                    <div>
                      <p className="text-xs uppercase tracking-[0.24em] text-cyan-200">Decision Breakdown</p>
                      <h2 className="mt-2 text-xl font-semibold text-white">Current reasoning</h2>
                    </div>
                    <div className="rounded-full border border-white/10 bg-white/5 px-3 py-1 text-xs text-slate-300">
                      Live
                    </div>
                  </div>

                  <div className="mt-5 grid gap-3 sm:grid-cols-2">
                    <div className="rounded-[1.15rem] border border-white/6 bg-slate-950/45 p-4">
                      <div className="text-xs uppercase tracking-[0.22em] text-slate-500">Root Cause</div>
                      <div className="mt-2 text-sm font-medium text-slate-100">
                        {payload.decision?.root_cause_hypothesis || "-"}
                      </div>
                    </div>
                    <div className="rounded-[1.15rem] border border-white/6 bg-slate-950/45 p-4">
                      <div className="text-xs uppercase tracking-[0.22em] text-slate-500">SLA Risk</div>
                      <div className={`mt-2 text-sm font-medium ${riskTone(payload.decision?.sla_risk_score)}`}>
                        {formatScore(payload.decision?.sla_risk_score)}
                      </div>
                    </div>
                    <div className="rounded-[1.15rem] border border-white/6 bg-slate-950/45 p-4">
                      <div className="text-xs uppercase tracking-[0.22em] text-slate-500">Actionability</div>
                      <div className="mt-2 text-sm font-medium text-slate-100">
                        {formatScore(payload.decision?.actionability_score)}
                      </div>
                    </div>
                    <div className="rounded-[1.15rem] border border-white/6 bg-slate-950/45 p-4">
                      <div className="text-xs uppercase tracking-[0.22em] text-slate-500">Recurrence</div>
                      <div className="mt-2 text-sm font-medium text-slate-100">
                        {formatScore(payload.decision?.recurrence_score)}
                      </div>
                    </div>
                  </div>
                </section>

                <section className="rounded-[1.75rem] border border-white/8 bg-white/[0.03] p-6 shadow-xl shadow-black/20">
                  <p className="text-xs uppercase tracking-[0.24em] text-cyan-200">Operator Actions</p>
                  <div className="mt-4 space-y-3">
                    <Link
                      href={`/replay/${params.id}`}
                      className="flex min-h-11 items-center justify-between rounded-[1.15rem] border border-white/10 bg-white/5 px-4 py-3 text-sm text-slate-200 transition hover:border-cyan-300/40 hover:bg-cyan-400/10"
                    >
                      <span>Inspect replay timeline</span>
                      <span className="text-cyan-200">Open</span>
                    </Link>
                    {payload.linked_incident ? (
                      <Link
                        href={`/incidents/${payload.linked_incident.id}`}
                        className="flex min-h-11 items-center justify-between rounded-[1.15rem] border border-cyan-400/20 bg-cyan-400/10 px-4 py-3 text-sm text-cyan-100 transition hover:border-cyan-300/40 hover:bg-cyan-400/15"
                      >
                        <span>Escalate via linked incident</span>
                        <span>{payload.linked_incident.id}</span>
                      </Link>
                    ) : (
                      <div className="rounded-[1.15rem] border border-dashed border-white/10 bg-slate-950/45 px-4 py-3 text-sm text-slate-400">
                        No linked incident is active for this case yet.
                      </div>
                    )}
                  </div>
                </section>
              </div>
            </section>

            <section className="grid gap-6 xl:grid-cols-2">
              <section className="rounded-[1.75rem] border border-white/8 bg-white/[0.03] p-6 shadow-xl shadow-black/20">
                <div className="flex items-center justify-between gap-3">
                  <div>
                    <p className="text-xs uppercase tracking-[0.24em] text-cyan-200">Recommendation Stack</p>
                    <h2 className="mt-2 text-xl font-semibold text-white">Suggested next actions</h2>
                  </div>
                  <div className="rounded-full border border-white/10 bg-white/5 px-3 py-1 text-xs text-slate-300">
                    {payload.recommendations.length} items
                  </div>
                </div>
                <div className="mt-5 space-y-3">
                  {payload.recommendations.length === 0 ? (
                    <div className="rounded-[1.15rem] border border-dashed border-white/10 bg-slate-950/45 px-4 py-6 text-sm text-slate-400">
                      No recommendations have been generated yet.
                    </div>
                  ) : (
                    payload.recommendations.map((recommendation) => (
                      <div
                        key={`${recommendation.rank}-${recommendation.action_label}`}
                        className="rounded-[1.15rem] border border-white/8 bg-slate-950/45 p-4"
                      >
                        <div className="flex items-start justify-between gap-4">
                          <div className="min-w-0">
                            <div className="text-xs uppercase tracking-[0.22em] text-amber-200">
                              Recommendation {recommendation.rank}
                            </div>
                            <div className="mt-2 text-sm font-medium text-white">{recommendation.action_label}</div>
                          </div>
                          <div className="rounded-full border border-cyan-400/20 bg-cyan-400/10 px-3 py-1 text-xs text-cyan-100">
                            {formatPercent(typeof recommendation.confidence === "number" ? recommendation.confidence * 100 : null)}
                          </div>
                        </div>
                        <p className="mt-3 text-sm leading-6 text-slate-400">{recommendation.rationale}</p>
                      </div>
                    ))
                  )}
                </div>
              </section>

              <section className="rounded-[1.75rem] border border-white/8 bg-white/[0.03] p-6 shadow-xl shadow-black/20">
                <div className="flex items-center justify-between gap-3">
                  <div>
                    <p className="text-xs uppercase tracking-[0.24em] text-cyan-200">Supporting History</p>
                    <h2 className="mt-2 text-xl font-semibold text-white">Similar cases</h2>
                  </div>
                  <div className="rounded-full border border-white/10 bg-white/5 px-3 py-1 text-xs text-slate-300">
                    {payload.similar_cases.length} matches
                  </div>
                </div>
                <div className="mt-5 space-y-3">
                  {payload.similar_cases.length === 0 ? (
                    <div className="rounded-[1.15rem] border border-dashed border-white/10 bg-slate-950/45 px-4 py-6 text-sm text-slate-400">
                      No similar cases were surfaced yet.
                    </div>
                  ) : (
                    payload.similar_cases.map((ticket) => (
                      <Link
                        key={ticket.ticket_id}
                        href={`/tickets/${ticket.ticket_id}`}
                        className="block rounded-[1.15rem] border border-white/8 bg-slate-950/45 p-4 transition hover:border-cyan-300/40 hover:bg-cyan-400/5"
                      >
                        <div className="flex flex-wrap items-center justify-between gap-3">
                          <div className="text-sm font-semibold text-white">{ticket.ticket_id}</div>
                          <div className="rounded-full border border-white/10 bg-white/5 px-3 py-1 text-[11px] uppercase tracking-[0.2em] text-slate-300">
                            {ticket.status}
                          </div>
                        </div>
                        <div className="mt-2 text-sm text-slate-400">{ticket.title}</div>
                      </Link>
                    ))
                  )}
                </div>
              </section>
            </section>
          </div>
        </div>
      </div>
    </div>
  );
}
