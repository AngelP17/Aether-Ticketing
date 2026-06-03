import Link from "next/link";
import {
  AlertTriangle,
  ArrowRight,
  Clock,
  Plus,
  RefreshCw,
  ShieldAlert,
  Sparkles,
} from "lucide-react";

import { OpsShell } from "@/components/ops-shell";
import { getServerApiUrl } from "@/lib/server-api";
import type { Incident } from "@/types";

export const dynamic = "force-dynamic";

type IncidentsFeed =
  | { status: "ready"; incidents: Incident[] }
  | { status: "error"; message: string };

async function getIncidents(): Promise<IncidentsFeed> {
  try {
    const response = await fetch(getServerApiUrl("/api/incidents"), {
      cache: "no-store",
    });
    if (!response.ok) {
      return {
        status: "error",
        message: `Incidents API returned ${response.status} ${response.statusText || "without a status message"}.`,
      };
    }
    return {
      status: "ready",
      incidents: (await response.json()) as Incident[],
    };
  } catch (error) {
    return {
      status: "error",
      message: error instanceof Error ? error.message : "Unable to reach the incidents API.",
    };
  }
}

type Severity = "critical" | "high" | "medium" | "low";

type SeverityPalette = {
  label: string;
  pill: string;
  dot: string;
  accent: string;
};

const severityPalette: Record<Severity, SeverityPalette> = {
  critical: {
    label: "Critical",
    pill: "border-rose-500/25 bg-rose-500/10 text-rose-200",
    dot: "bg-rose-400",
    accent: "border-l-rose-500/40",
  },
  high: {
    label: "High",
    pill: "border-amber-500/25 bg-amber-500/10 text-amber-200",
    dot: "bg-amber-400",
    accent: "border-l-amber-500/40",
  },
  medium: {
    label: "Medium",
    pill: "border-cyan-500/25 bg-cyan-500/10 text-cyan-200",
    dot: "bg-cyan-400",
    accent: "border-l-cyan-500/40",
  },
  low: {
    label: "Low",
    pill: "border-zinc-700/60 bg-zinc-800/70 text-zinc-300",
    dot: "bg-zinc-500",
    accent: "border-l-zinc-700/60",
  },
};

function severityFromImpact(score: number | undefined | null): Severity {
  if (typeof score !== "number") {
    return "low";
  }
  if (score >= 75) {
    return "critical";
  }
  if (score >= 55) {
    return "high";
  }
  if (score >= 35) {
    return "medium";
  }
  return "low";
}

function statusTone(status: string) {
  const normalized = status.trim().toLowerCase();
  if (normalized === "open" || normalized === "active") {
    return "border-rose-500/20 bg-rose-500/10 text-rose-200";
  }
  if (normalized === "monitoring" || normalized === "watching") {
    return "border-cyan-500/20 bg-cyan-500/10 text-cyan-200";
  }
  if (normalized === "resolved" || normalized === "closed") {
    return "border-emerald-500/20 bg-emerald-500/10 text-emerald-200";
  }
  return "border-zinc-700/60 bg-zinc-900/70 text-zinc-300";
}

function formatStarted(value: string | undefined | null) {
  if (!value) {
    return "Started time unknown";
  }
  const parsed = new Date(value);
  if (Number.isNaN(parsed.getTime())) {
    return value;
  }
  const date = parsed.toISOString().slice(0, 10);
  const time = parsed.toISOString().slice(11, 16);
  return `${date} · ${time} UTC`;
}

function sortIncidents(incidents: Incident[]): Incident[] {
  return [...incidents].sort((a, b) => {
    const aTs = a.opened_at ? new Date(a.opened_at).getTime() : 0;
    const bTs = b.opened_at ? new Date(b.opened_at).getTime() : 0;
    if (Number.isNaN(aTs) && Number.isNaN(bTs)) {
      return 0;
    }
    if (Number.isNaN(aTs)) {
      return 1;
    }
    if (Number.isNaN(bTs)) {
      return -1;
    }
    return bTs - aTs;
  });
}

function HeaderActions() {
  return (
    <Link
      href="/tickets/new"
      className="inline-flex items-center gap-2 rounded-xl border border-amber-400/20 bg-amber-500 px-3 py-2 text-sm font-semibold text-black transition hover:bg-amber-400 active:scale-[0.98]"
    >
      <Plus className="h-4 w-4" aria-hidden="true" />
      New ticket
    </Link>
  );
}

function PageHeader({ count }: { count: number }) {
  return (
    <header className="mb-5 flex flex-col gap-3 px-1 sm:flex-row sm:items-end sm:justify-between">
      <div>
        <h1 className="text-3xl font-semibold tracking-tight text-white sm:text-4xl">
          Incidents
        </h1>
        <p className="mt-2 max-w-2xl text-sm leading-6 text-zinc-400">
          Incidents grouped by common cause. Sorted by most recent.
        </p>
      </div>
      <div className="inline-flex items-center gap-2 self-start rounded-full border border-zinc-800/70 bg-black/30 px-3 py-1.5 text-xs text-zinc-400 sm:self-end">
        <ShieldAlert className="h-3.5 w-3.5 text-amber-300" aria-hidden="true" />
        <span className="mono-data text-[11px]">{count} active</span>
      </div>
    </header>
  );
}

function EmptyState() {
  return (
    <div className="ops-card rounded-[22px] px-6 py-12 text-center">
      <div className="mx-auto flex h-12 w-12 items-center justify-center rounded-2xl border border-zinc-800/70 bg-black/30 text-zinc-400">
        <Sparkles className="h-5 w-5" aria-hidden="true" />
      </div>
      <h2 className="mt-4 text-lg font-semibold text-white">No incidents yet</h2>
      <p className="mx-auto mt-2 max-w-md text-sm leading-6 text-zinc-500">
        No incidents yet. Incidents are created when enough related tickets are detected.
      </p>
      <div className="mt-5 flex flex-wrap justify-center gap-3">
        <Link
          href="/command-center"
          className="inline-flex items-center gap-2 rounded-xl border border-zinc-700 bg-zinc-900/70 px-3 py-2 text-sm font-medium text-zinc-100 transition hover:border-amber-500/30 hover:bg-amber-500/10"
        >
          Open Command Center
          <ArrowRight className="h-4 w-4" aria-hidden="true" />
        </Link>
      </div>
    </div>
  );
}

function ErrorState({ message }: { message: string }) {
  return (
    <div className="ops-card rounded-[22px] border border-rose-500/25 px-6 py-10">
      <div className="flex items-start gap-4">
        <div className="flex h-11 w-11 shrink-0 items-center justify-center rounded-2xl border border-rose-500/30 bg-rose-500/10 text-rose-200">
          <AlertTriangle className="h-5 w-5" aria-hidden="true" />
        </div>
        <div className="min-w-0">
          <h2 className="text-xl font-semibold text-white">Incident feed failed to load</h2>
          <p className="mt-2 max-w-3xl text-sm leading-6 text-zinc-400">{message}</p>
          <div className="mt-5 flex flex-wrap gap-3">
            <Link
              href="/incidents"
              className="inline-flex items-center gap-2 rounded-xl border border-rose-500/30 bg-rose-500/10 px-3 py-2 text-sm font-semibold text-rose-100 transition hover:border-rose-400/50 hover:bg-rose-500/15"
            >
              <RefreshCw className="h-4 w-4" aria-hidden="true" />
              Retry load
            </Link>
            <Link
              href="/command-center"
              className="inline-flex items-center gap-2 rounded-xl border border-zinc-700 bg-zinc-900/70 px-3 py-2 text-sm font-medium text-zinc-100 transition hover:border-amber-500/30 hover:bg-amber-500/10"
            >
              Back to Command Center
            </Link>
          </div>
        </div>
      </div>
    </div>
  );
}

function IncidentCard({ incident }: { incident: Incident }) {
  const severity = severityFromImpact(incident.business_impact_score);
  const palette = severityPalette[severity];
  const summary = incident.root_cause_hypothesis?.trim();

  return (
    <Link
      href={`/incidents/${incident.id}`}
      className={`ops-card group block rounded-[22px] border-l-4 ${palette.accent} px-5 py-5 transition hover:border-amber-500/30 hover:shadow-[0_22px_60px_rgba(0,0,0,0.32)] focus:outline-none focus-visible:ring-2 focus-visible:ring-amber-400/40 sm:px-6`}
    >
      <div className="flex flex-col gap-4">
        <div className="flex flex-wrap items-start justify-between gap-3">
          <div className="flex flex-wrap items-center gap-2">
            <span
              className={`inline-flex items-center gap-2 rounded-full border px-2.5 py-1 text-[11px] font-medium uppercase tracking-[0.18em] ${palette.pill}`}
            >
              <span className={`h-1.5 w-1.5 rounded-full ${palette.dot}`} aria-hidden="true" />
              {palette.label}
            </span>
            <span className="mono-data rounded-full border border-zinc-800/70 bg-black/30 px-2.5 py-1 text-[11px] uppercase tracking-[0.22em] text-zinc-400">
              {incident.id}
            </span>
            <span
              className={`rounded-full border px-2.5 py-1 text-[11px] font-medium capitalize ${statusTone(incident.status)}`}
            >
              {incident.status}
            </span>
          </div>
          <div className="mono-data inline-flex items-center gap-1.5 rounded-full border border-zinc-800/70 bg-black/30 px-2.5 py-1 text-[11px] text-zinc-400">
            <Clock className="h-3 w-3" aria-hidden="true" />
            {formatStarted(incident.opened_at)}
          </div>
        </div>

        <h2 className="text-lg font-semibold leading-snug text-white transition group-hover:text-amber-100 sm:text-xl">
          {incident.title}
        </h2>

        {summary ? (
          <p className="line-clamp-2 text-sm leading-6 text-zinc-400">{summary}</p>
        ) : null}

        <div className="flex flex-wrap items-center justify-between gap-3 border-t border-zinc-800/70 pt-4">
          <div className="flex flex-wrap items-center gap-2 text-[11px] text-zinc-500">
            <span className="mono-data rounded-full border border-zinc-800/70 bg-black/30 px-2.5 py-1 uppercase tracking-[0.2em]">
              {incident.ticket_count} tickets
            </span>
            <span className="mono-data rounded-full border border-zinc-800/70 bg-black/30 px-2.5 py-1 uppercase tracking-[0.2em]">
              Impact {Number(incident.business_impact_score ?? 0).toFixed(1)}
            </span>
            <span className="mono-data rounded-full border border-zinc-800/70 bg-black/30 px-2.5 py-1 uppercase tracking-[0.2em]">
              Confidence {Math.round(Number(incident.confidence ?? 0))}%
            </span>
          </div>
          <span className="inline-flex items-center gap-1.5 text-xs font-medium text-amber-300 opacity-0 transition group-hover:opacity-100">
            Open detail
            <ArrowRight className="h-3.5 w-3.5" aria-hidden="true" />
          </span>
        </div>
      </div>
    </Link>
  );
}

export default async function IncidentsPage() {
  const feed = await getIncidents();
  const isReady = feed.status === "ready";
  const incidents = isReady ? sortIncidents(feed.incidents) : [];

  return (
    <OpsShell
      eyebrow="Aether OpsCenter"
      title="Incidents"
      subtitle="Incidents grouped by common cause with links to ticket and replay detail."
      statusPill={
        isReady
          ? { kind: "ready", label: "Live" }
          : { kind: "error", label: "Disconnected" }
      }
      headerActions={<HeaderActions />}
      showNotificationBell
    >
      <div className="mx-auto w-full max-w-[1280px]">
        <PageHeader count={incidents.length} />

        {feed.status === "error" ? (
          <ErrorState message={feed.message} />
        ) : incidents.length === 0 ? (
          <EmptyState />
        ) : (
          <div className="grid gap-4 sm:gap-5">
            {incidents.map((incident) => (
              <IncidentCard key={incident.id} incident={incident} />
            ))}
          </div>
        )}
      </div>
    </OpsShell>
  );
}
