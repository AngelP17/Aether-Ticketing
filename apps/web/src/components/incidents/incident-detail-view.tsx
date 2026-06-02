"use client";

import Link from "next/link";

import { OpsShell } from "@/components/ops-shell";

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
  graph_evidence?: {
    evidence_basis?: string;
    shared_site?: string | null;
    distinct_sites?: number;
    shared_requester_count?: number;
    shared_assignee_count?: number;
    primary_requesters?: string[];
    primary_assignees?: string[];
  };
  tickets: Array<{
    ticket_id: string;
    title: string;
    status: string;
    priority_score?: number;
  }>;
};

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

function impactTone(value?: number | null) {
  if (typeof value !== "number") {
    return "text-slate-200";
  }
  if (value >= 80) {
    return "text-rose-200";
  }
  if (value >= 55) {
    return "text-amber-200";
  }
  return "text-emerald-200";
}

export function IncidentDetailView({
  id,
  payload,
  error,
}: {
  id: string;
  payload?: IncidentDetailPayload;
  error?: string;
}) {
  if (error) {
    return (
      <OpsShell
        eyebrow="Aether OpsCenter"
        title="Incident Detail"
        subtitle={`Incident ${id}`}
        statusPill={{ kind: "error", label: "Disconnected" }}
      >
        <div className="mx-auto max-w-7xl">
          <div className="ops-card rounded-[2rem] border border-rose-500/20 p-6 shadow-2xl shadow-black/30 sm:p-8">
            <div className="text-xs uppercase tracking-[0.28em] text-rose-300">Incident API error</div>
            <h1 className="mt-3 text-3xl font-semibold tracking-tight text-white">This incident could not load</h1>
            <p className="mt-4 max-w-3xl text-sm leading-7 text-slate-400">{error}</p>
            <div className="mt-6 flex flex-wrap gap-3">
              <Link
                href="/command-center"
                className="rounded-2xl border border-white/10 bg-white/5 px-4 py-3 text-sm font-medium text-slate-200 transition hover:border-cyan-300/40 hover:bg-cyan-400/10 hover:text-white"
              >
                Back to queue
              </Link>
              <Link
                href={`/incidents/${id}`}
                className="rounded-2xl border border-rose-500/30 bg-rose-500/10 px-4 py-3 text-sm font-medium text-rose-100 transition hover:border-rose-400/40 hover:bg-rose-500/15"
              >
                Retry load
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
      title="Incident Detail"
      subtitle={payload.incident.title}
      statusPill={{ kind: "ready", label: "Live" }}
      headerActions={
        <>
          <Link
            href="/command-center"
            className="rounded-2xl border border-white/10 bg-white/5 px-4 py-3 text-sm font-medium text-slate-200 transition hover:border-cyan-300/40 hover:bg-cyan-400/10 hover:text-white"
          >
            Back to queue
          </Link>
          <Link
            href="/reports"
            className="rounded-2xl border border-amber-500/30 bg-amber-500/10 px-4 py-3 text-sm font-medium text-amber-100 transition hover:border-amber-400/40 hover:bg-amber-500/15"
          >
            Open reports
          </Link>
        </>
      }
      showNotificationBell
    >
      <div className="mx-auto max-w-7xl">
        <div className="rounded-[2rem] border border-white/8 bg-black/20 shadow-2xl shadow-black/30 backdrop-blur-xl">
          <div className="border-b border-white/6 px-5 py-5 sm:px-7">
            <div className="flex flex-col gap-5 lg:flex-row lg:items-start lg:justify-between">
              <div className="min-w-0">
                <div className="flex flex-wrap items-center gap-3 text-xs uppercase tracking-[0.28em] text-cyan-200">
                  <span>Incident Detail</span>
                  <span className="h-1 w-1 rounded-full bg-slate-600" />
                  <span>{id}</span>
                </div>
                <h1 className="mt-3 text-3xl font-semibold tracking-tight text-white sm:text-4xl">
                  {payload.incident.title}
                </h1>
                <p className="mt-3 max-w-3xl text-sm leading-6 text-slate-400">
                  Cluster-level view of correlated tickets, operational impact, and the coordinated action expected from
                  the ops center.
                </p>
              </div>
            </div>
          </div>

          <div className="space-y-6 px-5 py-6 sm:px-7">
            <section className="grid gap-4 md:grid-cols-2 xl:grid-cols-4">
              <div className="rounded-[1.5rem] border border-white/8 bg-gradient-to-br from-slate-900/95 to-slate-950/80 p-5">
                <div className="text-xs uppercase tracking-[0.24em] text-slate-500">Status</div>
                <div className="mt-3 text-2xl font-semibold text-white">{payload.incident.status}</div>
                <div className="mt-2 text-sm text-slate-400">Current lifecycle state of the cluster.</div>
              </div>
              <div className="rounded-[1.5rem] border border-white/8 bg-gradient-to-br from-slate-900/95 to-slate-950/80 p-5">
                <div className="text-xs uppercase tracking-[0.24em] text-slate-500">Linked Tickets</div>
                <div className="mt-3 text-3xl font-semibold text-white">{payload.incident.ticket_count}</div>
                <div className="mt-2 text-sm text-slate-400">Cases currently grouped into this incident.</div>
              </div>
              <div className="rounded-[1.5rem] border border-white/8 bg-gradient-to-br from-cyan-500/10 to-slate-950/80 p-5">
                <div className="text-xs uppercase tracking-[0.24em] text-slate-500">Confidence</div>
                <div className="mt-3 text-3xl font-semibold text-cyan-200">
                  {formatPercent(payload.incident.confidence)}
                </div>
                <div className="mt-2 text-sm text-slate-400">Strength of the current grouping hypothesis.</div>
              </div>
              <div className="rounded-[1.5rem] border border-white/8 bg-gradient-to-br from-amber-500/10 to-slate-950/80 p-5">
                <div className="text-xs uppercase tracking-[0.24em] text-slate-500">Business Impact</div>
                <div className={`mt-3 text-3xl font-semibold ${impactTone(payload.incident.business_impact_score)}`}>
                  {formatScore(payload.incident.business_impact_score)}
                </div>
                <div className="mt-2 text-sm text-slate-400">Estimated operational severity across the cluster.</div>
              </div>
            </section>

            <section className="grid gap-6 xl:grid-cols-[1.05fr,0.95fr]">
              <section className="rounded-[1.75rem] border border-white/8 bg-white/[0.03] p-6 shadow-xl shadow-black/20">
                <div className="flex flex-wrap items-start justify-between gap-4">
                  <div>
                    <p className="text-xs uppercase tracking-[0.24em] text-cyan-200">Operational Assessment</p>
                    <h2 className="mt-2 text-2xl font-semibold text-white">{payload.incident.title}</h2>
                  </div>
                  <div className="rounded-full border border-white/10 bg-white/5 px-3 py-1 text-xs text-slate-300">
                    {id}
                  </div>
                </div>

                <div className="mt-6 rounded-[1.25rem] border border-white/6 bg-slate-950/50 p-5">
                  <div className="text-xs uppercase tracking-[0.22em] text-slate-500">Common Cause</div>
                  <p className="mt-3 text-sm leading-7 text-slate-300">{payload.common_cause}</p>
                </div>

                <div className="mt-5 rounded-[1.25rem] border border-cyan-400/20 bg-cyan-400/10 p-5">
                  <div className="text-xs uppercase tracking-[0.22em] text-cyan-200">Recommended Action</div>
                  <p className="mt-3 text-sm leading-7 text-cyan-50">{payload.recommended_action}</p>
                </div>
              </section>

              <section className="rounded-[1.75rem] border border-white/8 bg-white/[0.03] p-6 shadow-xl shadow-black/20">
                <p className="text-xs uppercase tracking-[0.24em] text-cyan-200">Operator Actions</p>
                <div className="mt-5 space-y-3">
                  <Link
                    href="/command-center"
                    className="flex min-h-11 items-center justify-between rounded-[1.15rem] border border-white/10 bg-white/5 px-4 py-3 text-sm text-slate-200 transition hover:border-cyan-300/40 hover:bg-cyan-400/10"
                  >
                    <span>Return to ranked queue</span>
                    <span className="text-cyan-200">Open</span>
                  </Link>
                  <Link
                    href={`/api/reports/excel?incident_id=${id}`}
                    className="flex min-h-11 items-center justify-between rounded-[1.15rem] border border-amber-500/20 bg-amber-500/10 px-4 py-3 text-sm text-amber-100 transition hover:border-amber-400/40 hover:bg-amber-500/15"
                  >
                    <span>Export incident-facing reporting</span>
                    <span>Download</span>
                  </Link>
                </div>

                <div className="mt-6 rounded-[1.25rem] border border-white/6 bg-slate-950/45 p-5">
                  <div className="text-xs uppercase tracking-[0.22em] text-slate-500">Cluster Snapshot</div>
                  <div className="mt-4 grid gap-3 sm:grid-cols-2">
                    <div>
                      <div className="text-xs uppercase tracking-[0.18em] text-slate-500">Opened At</div>
                      <div className="mt-2 text-sm text-slate-200">{payload.incident.opened_at || "--"}</div>
                    </div>
                    <div>
                      <div className="text-xs uppercase tracking-[0.18em] text-slate-500">Confidence</div>
                      <div className="mt-2 text-sm text-slate-200">{formatPercent(payload.incident.confidence)}</div>
                    </div>
                    <div>
                      <div className="text-xs uppercase tracking-[0.18em] text-slate-500">Impact</div>
                      <div className="mt-2 text-sm text-slate-200">
                        {formatScore(payload.incident.business_impact_score)}
                      </div>
                    </div>
                    <div>
                      <div className="text-xs uppercase tracking-[0.18em] text-slate-500">Ticket Count</div>
                      <div className="mt-2 text-sm text-slate-200">{payload.incident.ticket_count}</div>
                    </div>
                  </div>
                </div>

                {payload.graph_evidence ? (
                  <div className="mt-6 rounded-[1.25rem] border border-violet-500/20 bg-violet-500/5 p-5">
                    <div className="text-xs uppercase tracking-[0.22em] text-violet-200">
                      Graph Evidence
                    </div>
                    <p className="mt-3 text-xs leading-6 text-violet-100/80">
                      {payload.graph_evidence.evidence_basis ||
                        "Deterministic ticket-to-ticket graph signal."}
                    </p>
                    <dl className="mt-4 grid gap-3 text-xs text-slate-200 sm:grid-cols-2">
                      <div>
                        <dt className="uppercase tracking-[0.18em] text-slate-500">Shared Site</dt>
                        <dd className="mt-1">{payload.graph_evidence.shared_site || "—"}</dd>
                      </div>
                      <div>
                        <dt className="uppercase tracking-[0.18em] text-slate-500">Distinct Sites</dt>
                        <dd className="mt-1">{payload.graph_evidence.distinct_sites ?? "—"}</dd>
                      </div>
                      <div>
                        <dt className="uppercase tracking-[0.18em] text-slate-500">Shared Requesters</dt>
                        <dd className="mt-1">
                          {payload.graph_evidence.shared_requester_count ?? 0}
                        </dd>
                      </div>
                      <div>
                        <dt className="uppercase tracking-[0.18em] text-slate-500">Shared Assignees</dt>
                        <dd className="mt-1">
                          {payload.graph_evidence.shared_assignee_count ?? 0}
                        </dd>
                      </div>
                    </dl>
                    {payload.graph_evidence.primary_requesters?.length ||
                    payload.graph_evidence.primary_assignees?.length ? (
                      <div className="mt-4 grid gap-3 text-xs sm:grid-cols-2">
                        {payload.graph_evidence.primary_requesters?.length ? (
                          <div>
                            <div className="text-xs uppercase tracking-[0.18em] text-slate-500">
                              Primary Requesters
                            </div>
                            <div className="mt-1 text-slate-200">
                              {payload.graph_evidence.primary_requesters.join(", ")}
                            </div>
                          </div>
                        ) : null}
                        {payload.graph_evidence.primary_assignees?.length ? (
                          <div>
                            <div className="text-xs uppercase tracking-[0.18em] text-slate-500">
                              Primary Assignees
                            </div>
                            <div className="mt-1 text-slate-200">
                              {payload.graph_evidence.primary_assignees.join(", ")}
                            </div>
                          </div>
                        ) : null}
                      </div>
                    ) : null}
                  </div>
                ) : null}
              </section>
            </section>

            <section className="rounded-[1.75rem] border border-white/8 bg-white/[0.03] p-6 shadow-xl shadow-black/20">
              <div className="flex flex-wrap items-center justify-between gap-3">
                <div>
                  <p className="text-xs uppercase tracking-[0.24em] text-cyan-200">Related Tickets</p>
                  <h2 className="mt-2 text-xl font-semibold text-white">Cases inside this incident</h2>
                </div>
                <div className="rounded-full border border-white/10 bg-white/5 px-3 py-1 text-xs text-slate-300">
                  {payload.tickets.length} tickets
                </div>
              </div>

              <div className="mt-5 space-y-3">
                {payload.tickets.length === 0 ? (
                  <div className="rounded-[1.15rem] border border-dashed border-white/10 bg-slate-950/45 px-4 py-6 text-sm text-slate-400">
                    The API returned an incident with no linked tickets.
                  </div>
                ) : (
                  payload.tickets.map((ticket) => (
                    <Link
                      key={ticket.ticket_id}
                      href={`/tickets/${ticket.ticket_id}`}
                      className="block rounded-[1.15rem] border border-white/8 bg-slate-950/45 p-4 transition hover:border-cyan-300/40 hover:bg-cyan-400/5"
                    >
                      <div className="flex flex-col gap-3 md:grid md:grid-cols-[auto,minmax(0,1fr),auto] md:items-center">
                        <div className="min-w-[7rem] text-sm font-semibold text-white">{ticket.ticket_id}</div>
                        <div className="min-w-0 text-sm text-slate-300">{ticket.title}</div>
                        <div className="flex flex-wrap items-center gap-2 md:justify-end">
                          <span className="rounded-full border border-white/10 bg-white/5 px-3 py-1 text-[11px] uppercase tracking-[0.2em] text-slate-300">
                            {ticket.status}
                          </span>
                          <span className="rounded-full border border-cyan-400/20 bg-cyan-400/10 px-3 py-1 text-[11px] text-cyan-100">
                            Score {formatScore(ticket.priority_score)}
                          </span>
                        </div>
                      </div>
                    </Link>
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
