import Link from "next/link";
import { notFound } from "next/navigation";

import { getServerApiUrl } from "@/lib/server-api";

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

function IncidentErrorState({ id, message }: { id: string; message: string }) {
  return (
    <div className="min-h-screen bg-[#060816] px-4 py-5 text-slate-50 sm:px-6 lg:px-8">
      <div className="mx-auto flex min-h-[calc(100vh-2.5rem)] max-w-7xl items-center">
        <div className="w-full rounded-[2rem] border border-rose-500/20 bg-black/20 p-8 shadow-2xl shadow-black/30 backdrop-blur-xl">
          <div className="text-xs uppercase tracking-[0.28em] text-rose-300">Incident API error</div>
          <h1 className="mt-3 text-3xl font-semibold tracking-tight text-white">This incident could not load</h1>
          <p className="mt-4 max-w-3xl text-sm leading-7 text-slate-400">{message}</p>
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
    </div>
  );
}

export default async function IncidentDetailPage({ params }: { params: { id: string } }) {
  const result = await getIncident(params.id);

  if (result.kind === "not_found") {
    notFound();
  }

  if (result.kind === "error") {
    return <IncidentErrorState id={params.id} message={result.message} />;
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
                  <span>Incident Detail</span>
                  <span className="h-1 w-1 rounded-full bg-slate-600" />
                  <span>{params.id}</span>
                </div>
                <h1 className="mt-3 text-3xl font-semibold tracking-tight text-white sm:text-4xl">
                  {payload.incident.title}
                </h1>
                <p className="mt-3 max-w-3xl text-sm leading-6 text-slate-400">
                  Cluster-level view of correlated tickets, operational impact, and the coordinated action expected from
                  the ops center.
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
                  href="/reports"
                  className="rounded-2xl border border-amber-500/30 bg-amber-500/10 px-4 py-3 text-sm font-medium text-amber-100 transition hover:border-amber-400/40 hover:bg-amber-500/15"
                >
                  Open reports
                </Link>
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
                    {params.id}
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
                    href={`/api/reports/excel?incident_id=${params.id}`}
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
    </div>
  );
}
