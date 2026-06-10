"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import {
  useCallback,
  startTransition,
  useDeferredValue,
  useEffect,
  useMemo,
  useRef,
  useState,
} from "react";
import type { ComponentType } from "react";
import {
  Activity,
  CheckCircle2,
  Clock3,
  Columns3,
  FileSpreadsheet,
  Filter,
  Gauge,
  LogOut,
  Plus,
  Shield,
  ShieldAlert,
} from "lucide-react";
import type { AxiosResponse } from "axios";

import { OpsShell } from "@/components/ops-shell";
import { SectionEmptyState } from "@/components/command-center/section-empty-state";
import { QueueTable } from "@/components/command-center/queue-table";
import { IncidentList } from "@/components/command-center/incident-list";
import { DecisionDetailPanel } from "@/components/command-center/decision-detail-panel";
import { priorityPalette } from "@/components/command-center/palettes";
import type { IncidentCard, QueueTicket } from "@/components/command-center/types";
import { NotificationBell, useToast } from "@/components/notifications";
import { governanceApi, intelligenceApi, metricsApi, ticketsApi, incidentsApi, reportsApi } from "@/lib/api";
import { clearStoredSession } from "@/lib/auth";
import { parseFilename } from "@/lib/export-utils";
import type { GovernanceSummaryResponse, Incident, IntelligenceHealthResponse, Ticket } from "@/types";
// Recharts removed for the snapshot analytics — replaced with custom hairline + mono dense bars
// to match design-taste-frontend OpsCenter rules (DENSITY 8, hairline data surfaces, one amber accent,
// no generic lib defaults, mono for counts/scores). See AGENTS.md.

type QueueMetrics = {
  total_open: number;
  critical: number;
  sla_breach_risk: number;
  incident_clusters: number;
};

type FeedStatus = "loading" | "ready" | "error";

type FeedState = {
  tickets: Ticket[];
  incidents: Incident[];
  metrics: QueueMetrics | null;
  intelligence: IntelligenceHealthResponse | null;
  governance: GovernanceSummaryResponse | null;
  status: FeedStatus;
  syncedAt: number;
  errorMessage: string | null;
  warnings: string[];
};

type TicketFilter = "all" | "active" | "closed";

const ticketFilterOptions: Array<{ key: TicketFilter; label: string }> = [
  { key: "all", label: "Full Queue" },
  { key: "active", label: "Active" },
  { key: "closed", label: "Closed" },
];

type MetricCard = {
  label: string;
  value: number;
  note: string;
  tone: string;
  icon: ComponentType<{ className?: string }>;
};

const initialFeed: FeedState = {
  tickets: [],
  incidents: [],
  metrics: null,
  intelligence: null,
  governance: null,
  status: "loading",
  syncedAt: Date.now(),
  errorMessage: null,
  warnings: [],
};

function isClosedStatus(status: string) {
  return status === "Closed" || status === "Resolved";
}

function normalizeConfidence(value: number) {
  return value > 1 ? value / 100 : value;
}

const GENERIC_RECOMMENDATION =
  "Validate ownership, root cause, and next concrete action.";

function describeAction(ticket: Omit<QueueTicket, "recommendation"> | undefined) {
  if (!ticket) {
    return "Select a case to inspect the recommended next move.";
  }

  const cause = ticket.category.toLowerCase();
  const title = ticket.title.toLowerCase();

  if (cause.includes("server") || title.includes("server")) {
    return "Treat this as shared-service risk, review blast radius, and collapse duplicate work into a single incident response track.";
  }
  if (cause.includes("network") || title.includes("vpn") || title.includes("isp")) {
    return "Verify whether this is a local break or upstream path issue, then escalate with evidence instead of another comment loop.";
  }
  if (cause.includes("hardware")) {
    return "Batch hardware work with nearby queue items so the team clears setup debt in one pass instead of one-off touches.";
  }
  if (cause.includes("access") || cause.includes("permission")) {
    return "Collect the approval trail now and close the access change cleanly instead of leaving it stranded in waiting status.";
  }
  return GENERIC_RECOMMENDATION;
}

async function apiData<T>(request: Promise<AxiosResponse<T>>): Promise<T> {
  const response = await request;
  return response.data;
}

function toQueueTicketFromLive(ticket: Ticket): QueueTicket {
  const base: Omit<QueueTicket, "recommendation"> = {
    ticketId: ticket.ticket_id,
    title: ticket.title,
    status: ticket.status,
    priority: ticket.priority_raw,
    score: ticket.priority_score ?? 0,
    assignee: ticket.assignee || "Unassigned",
    category: ticket.category || ticket.root_cause_hypothesis || "Unknown",
    daysOpen: ticket.days_open,
    createdAt: ticket.created_at,
    incidentId: ticket.incident_id,
  };
  return { ...base, recommendation: describeAction(base) };
}

function getLiveIncidents(incidents: Incident[]): IncidentCard[] {
  return incidents.map((incident) => ({
    id: String(incident.id),
    numericId: incident.id,
    title: incident.title,
    rootCause: incident.root_cause_hypothesis || "Unknown cause",
    ticketCount: incident.ticket_count,
    confidence: normalizeConfidence(incident.confidence),
    impact: incident.business_impact_score,
  }));
}

function statusPillFor(status: FeedStatus) {
  if (status === "ready") {
    return { kind: "ready" as const, label: "Live · API connected" };
  }
  if (status === "loading") {
    return { kind: "loading" as const, label: "Syncing live data" };
  }
  return { kind: "error" as const, label: "Live data unavailable" };
}

export default function CommandCenterPage() {
  const router = useRouter();
  const toast = useToast();
  const toastRef = useRef(toast);
  const [feed, setFeed] = useState<FeedState>(initialFeed);
  const [selectedTicketId, setSelectedTicketId] = useState<string | null>(null);
  const [search, setSearch] = useState("");
  const [ticketFilter, setTicketFilter] = useState<TicketFilter>("all");
  const [lastSyncSeconds, setLastSyncSeconds] = useState(0);
  const [isExporting, setIsExporting] = useState(false);
  const [isSigningOut, setIsSigningOut] = useState(false);
  const deferredSearch = useDeferredValue(search);
  const syncStart = useRef(Date.now());
  const mountedRef = useRef(true);

  useEffect(() => {
    toastRef.current = toast;
  }, [toast]);

  const hydrateFeed = useCallback(
    async ({ notifyOnError = false }: { notifyOnError?: boolean } = {}) => {
      if (mountedRef.current) {
        setFeed((current) => ({
          ...current,
          status: "loading",
          errorMessage: null,
          warnings: [],
        }));
      }

      try {
        const [ticketsResult, metricsResult, incidentsResult, intelligenceResult, governanceResult] = await Promise.allSettled([
          apiData<Ticket[]>(ticketsApi.list({ limit: 250 })),
          apiData<QueueMetrics>(metricsApi.get()),
          apiData<Incident[]>(incidentsApi.list()),
          apiData<IntelligenceHealthResponse>(intelligenceApi.health()),
          apiData<GovernanceSummaryResponse>(governanceApi.summary()),
        ]);

        if (ticketsResult.status === "rejected") {
          throw ticketsResult.reason;
        }

        const warnings: string[] = [];

        const metrics =
          metricsResult.status === "fulfilled"
            ? metricsResult.value
            : (warnings.push("Queue metrics are temporarily unavailable. Summary cards are derived from live tickets."), null);

        const incidents =
          incidentsResult.status === "fulfilled"
            ? incidentsResult.value
            : (warnings.push("Incident clustering is temporarily unavailable."), []);

        const intelligence =
          intelligenceResult.status === "fulfilled"
            ? intelligenceResult.value
            : (warnings.push("Decision intelligence is temporarily unavailable."), null);

        const governance =
          governanceResult.status === "fulfilled"
            ? governanceResult.value
            : (warnings.push("Governance drift status is temporarily unavailable."), null);

        if (!mountedRef.current) {
          return;
        }

        const syncedAt = Date.now();
        syncStart.current = syncedAt;

        startTransition(() => {
          setFeed({
            tickets: ticketsResult.value,
            incidents,
            metrics,
            intelligence,
            governance,
            status: "ready",
            syncedAt,
            errorMessage: null,
            warnings,
          });
          setLastSyncSeconds(0);
        });
      } catch (error) {
        const message =
          error instanceof Error ? error.message : "The command center could not load the live API.";

        if (!mountedRef.current) {
          return;
        }

        startTransition(() => {
          setFeed({
            tickets: [],
            incidents: [],
            metrics: null,
            intelligence: null,
            governance: null,
            status: "error",
            syncedAt: Date.now(),
            errorMessage: message,
            warnings: [],
          });
        });

        if (notifyOnError) {
          toastRef.current.error("Live data unavailable", message);
        }
      }
    },
    [],
  );

  useEffect(() => {
    mountedRef.current = true;
    void hydrateFeed();

    const timer = window.setInterval(() => {
      setLastSyncSeconds(Math.floor((Date.now() - syncStart.current) / 1000));
    }, 1000);

    return () => {
      mountedRef.current = false;
      window.clearInterval(timer);
    };
  }, [hydrateFeed]);

  const liveQueue = feed.tickets
    .filter((ticket) => !isClosedStatus(ticket.status))
    .sort((left, right) => (right.priority_score ?? 0) - (left.priority_score ?? 0))
    .map(toQueueTicketFromLive);

  const rankedQueue = liveQueue;
  const incidentCards = getLiveIncidents(feed.incidents);
  const searchTerm = deferredSearch.trim().toLowerCase();

  const openTickets = feed.metrics?.total_open ?? rankedQueue.length;
  const closedResolved = feed.tickets.filter((ticket) => isClosedStatus(ticket.status)).length;
  const criticalOpen =
    feed.metrics?.critical ??
    feed.tickets.filter(
      (ticket) => !isClosedStatus(ticket.status) && ticket.priority_raw === "Critical",
    ).length;
  const slaRisk =
    feed.metrics?.sla_breach_risk ?? rankedQueue.filter((ticket) => ticket.daysOpen >= 3).length;
  const metrics: MetricCard[] = [
    {
      label: "Open",
      value: openTickets,
      note: `${slaRisk} at SLA risk.`,
      tone: "from-cyan-500/15 to-cyan-500/[0.03] text-cyan-100",
      icon: Gauge,
    },
    {
      label: "Critical",
      value: criticalOpen,
      note: `${incidentCards.length} incident cluster${incidentCards.length === 1 ? "" : "s"}.`,
      tone: "from-rose-500/15 to-rose-500/[0.03] text-rose-100",
      icon: ShieldAlert,
    },
    {
      label: "SLA Risk",
      value: slaRisk,
      note:
        feed.metrics?.sla_breach_risk != null
          ? "Within 75% of SLA window."
          : "3+ days open (local estimate).",
      tone: "from-orange-500/15 to-orange-500/[0.03] text-orange-100",
      icon: Clock3,
    },
    {
      label: "Resolved",
      value: closedResolved,
      note: "Completed this session.",
      tone: "from-emerald-500/15 to-emerald-500/[0.03] text-emerald-100",
      icon: CheckCircle2,
    },
  ];

  const filteredQueue = rankedQueue.filter((ticket) => {
    if (!searchTerm) {
      return true;
    }

    return [
      ticket.ticketId,
      ticket.title,
      ticket.assignee,
      ticket.category,
      ticket.priority,
      ticket.status,
    ]
      .join(" ")
      .toLowerCase()
      .includes(searchTerm);
  });

  // Derived for dashboard charts (Recharts, client-side from live feed)
  const categoryData = useMemo(() => {
    const counts: Record<string, number> = {};
    feed.tickets.forEach((t) => {
      const c = (t.category || t.root_cause_hypothesis || "Unknown").toString();
      counts[c] = (counts[c] || 0) + 1;
    });
    return Object.entries(counts)
      .sort((a, b) => b[1] - a[1])
      .slice(0, 5)
      .map(([name, value]) => ({ name, value }));
  }, [feed.tickets]);

  const assigneeData = useMemo(() => {
    const counts: Record<string, number> = {};
    feed.tickets.forEach((t) => {
      const a = (t.assignee || "Unassigned").toString();
      counts[a] = (counts[a] || 0) + 1;
    });
    return Object.entries(counts)
      .sort((a, b) => b[1] - a[1])
      .slice(0, 6)
      .map(([name, value]) => ({ name: name.length > 14 ? name.slice(0, 12) + "…" : name, value }));
  }, [feed.tickets]);

  const edgeData = useMemo(() => {
    const g = feed.governance?.graph || (feed.intelligence as any)?.subsystems?.graph;
    const et = g?.edges_by_type || {};
    return Object.entries(et as Record<string, number>)
      .sort((a, b) => b[1] - a[1])
      .slice(0, 5)
      .map(([name, value]) => ({ name: name.replace(/_/g, " ").slice(0, 14), value }));
  }, [feed.governance, feed.intelligence]);

  const ticketRows = [...feed.tickets]
    .sort((left, right) => new Date(right.created_at).getTime() - new Date(left.created_at).getTime())
    .map(toQueueTicketFromLive)
    .filter((ticket) => {
    const matchesSearch =
      !searchTerm ||
      [ticket.ticketId, ticket.title, ticket.assignee, ticket.category, ticket.priority, ticket.status]
        .join(" ")
        .toLowerCase()
        .includes(searchTerm);

    if (!matchesSearch) {
      return false;
    }

    if (ticketFilter === "all") {
      return true;
    }
    if (ticketFilter === "active") {
      return !isClosedStatus(ticket.status);
    }
    return isClosedStatus(ticket.status);
  });

  useEffect(() => {
    if (!filteredQueue.length) {
      setSelectedTicketId(null);
      return;
    }

    if (!selectedTicketId || !filteredQueue.some((ticket) => ticket.ticketId === selectedTicketId)) {
      setSelectedTicketId(filteredQueue[0].ticketId);
    }
  }, [filteredQueue, selectedTicketId]);

  const selectedTicket = filteredQueue.find((ticket) => ticket.ticketId === selectedTicketId) ?? filteredQueue[0];
  const linkedIncident =
    incidentCards.find((incident) => incident.id === selectedTicket?.incidentId) ??
    incidentCards.find((incident) =>
      selectedTicket ? incident.rootCause.toLowerCase().includes(selectedTicket.category.toLowerCase()) : false,
    );
  const relatedTickets = selectedTicket
    ? rankedQueue
        .filter((ticket) => ticket.ticketId !== selectedTicket.ticketId)
        .map((ticket) => {
          const relationScore =
            (ticket.incidentId && ticket.incidentId === selectedTicket.incidentId ? 4 : 0) +
            (ticket.category === selectedTicket.category ? 3 : 0) +
            (ticket.assignee === selectedTicket.assignee ? 2 : 0) +
            (ticket.priority === selectedTicket.priority ? 1 : 0);
          return { ticket, relationScore };
        })
        .filter((item) => item.relationScore > 0)
        .sort((left, right) => right.relationScore - left.relationScore || right.ticket.score - left.ticket.score)
        .slice(0, 5)
        .map((item) => item.ticket)
    : [];

  async function handleWorkbookDownload() {
    if (isExporting) {
      return;
    }

    setIsExporting(true);

    try {
      const response = await reportsApi.excel();

      if (response.status !== 200) {
        const data = response.data as any;
        const msg = data?.detail || data?.message || `Export failed with status ${response.status}`;
        throw new Error(msg);
      }

      const blob = response.data as Blob;
      if (blob.size === 0) {
        throw new Error("The workbook export was empty.");
      }

      const filename = parseFilename(response.headers["content-disposition"] as string | null);
      const url = URL.createObjectURL(blob);
      const anchor = document.createElement("a");

      anchor.href = url;
      anchor.download = filename;
      anchor.rel = "noopener";
      document.body.appendChild(anchor);
      anchor.click();
      anchor.remove();

      window.setTimeout(() => URL.revokeObjectURL(url), 1000);
      toast.success("Workbook download started", filename);
    } catch (error) {
      const message = error instanceof Error ? error.message : "Could not generate workbook.";
      toast.error("Export failed", message);
    } finally {
      setIsExporting(false);
    }
  }

  async function handleLogout() {
    if (isSigningOut) {
      return;
    }

    setIsSigningOut(true);

    try {
      await fetch("/api/auth/logout", {
        method: "POST",
        cache: "no-store",
      }).catch(() => null);
    } finally {
      clearStoredSession();
      toast.success("Signed out successfully");
      router.replace("/login");
      setIsSigningOut(false);
    }
  }

  const sheetItems = [
    { kind: "link" as const, href: "/tickets/new", label: "New ticket", icon: Plus, tone: "amber" as const },
    { kind: "link" as const, href: "/board", label: "Workflow board", icon: Columns3, tone: "default" as const },
    { kind: "link" as const, href: "/reports", label: "Reports", icon: Activity, tone: "cyan" as const },
    {
      kind: "action" as const,
      onClick: handleWorkbookDownload,
      label: isExporting ? "Preparing export..." : "Export workbook",
      icon: FileSpreadsheet,
      tone: "amber" as const,
    },
  ];

  const shellWarnings: string[] = [
    ...(incidentCards.length > 0
      ? [`${incidentCards.length} active incident${incidentCards.length === 1 ? "" : "s"}`]
      : []),
    ...feed.warnings,
  ];

  return (
    <OpsShell
      eyebrow="Aether OpsCenter"
      title="Command Center"
      subtitle="Ranked queue, incident clusters, and operator actions."
      statusPill={statusPillFor(feed.status)}
      lastSyncSeconds={lastSyncSeconds}
      warnings={shellWarnings}
      search={{
        value: search,
        onChange: setSearch,
        placeholder: "Search queue, owner, category, or ticket",
      }}
      sheetItems={sheetItems}
      exportButton={{ isExporting, onClick: handleWorkbookDownload, label: "Export workbook" }}
      showNotificationBell
      onLogout={handleLogout}
      isSigningOut={isSigningOut}
      headerActions={
        <>
          {/* Desktop action row */}
          <div className="hidden flex-wrap gap-2 xl:flex">
            <Link
              href="/tickets/new"
              className="inline-flex items-center gap-2 rounded-full bg-amber-500 px-4 py-2.5 text-sm font-semibold text-black transition hover:bg-amber-400"
            >
              <Plus className="h-4 w-4" />
              New ticket
            </Link>
            <button
              type="button"
              onClick={handleWorkbookDownload}
              disabled={isExporting}
              className="inline-flex items-center gap-2 rounded-full border border-amber-400/20 bg-amber-500/10 px-4 py-2.5 text-sm font-medium text-amber-100 transition hover:bg-amber-500/20"
            >
              <FileSpreadsheet className="h-4 w-4" />
              {isExporting ? "Exporting..." : "Export"}
            </button>
            <Link
              href="/board"
              className="inline-flex items-center gap-2 rounded-full border border-zinc-700/60 bg-zinc-900/60 px-4 py-2.5 text-sm font-medium text-zinc-200 transition hover:border-zinc-500"
            >
              <Columns3 className="h-4 w-4" />
              Board
            </Link>
            <Link
              href="/reports"
              className="inline-flex items-center gap-2 rounded-full border border-zinc-700/60 bg-zinc-900/60 px-4 py-2.5 text-sm font-medium text-zinc-200 transition hover:border-zinc-500"
            >
              <Activity className="h-4 w-4" />
              Reports
            </Link>
            <Link
              href="/admin"
              className="inline-flex items-center gap-2 rounded-full border border-zinc-700/60 bg-zinc-900/60 px-4 py-2.5 text-sm font-medium text-zinc-200 transition hover:border-zinc-500"
            >
              <Shield className="h-4 w-4" />
              Admin
            </Link>
            <button
              type="button"
              onClick={handleLogout}
              disabled={isSigningOut}
              className="inline-flex items-center gap-2 rounded-full border border-zinc-700/60 bg-zinc-900/60 px-4 py-2.5 text-sm font-medium text-zinc-200 transition hover:border-rose-400/40 hover:text-rose-100 disabled:cursor-not-allowed disabled:opacity-70"
            >
              <LogOut className="h-4 w-4" />
              {isSigningOut ? "Signing out..." : "Logout"}
            </button>
            <NotificationBell />
          </div>

          {/* Mobile/tablet condensed action row */}
          <div className="flex items-center gap-2 xl:hidden">
            <Link
              href="/tickets/new"
              className="inline-flex items-center gap-2 rounded-full bg-amber-500 px-4 py-2.5 text-sm font-semibold text-black transition hover:bg-amber-400"
            >
              <Plus className="h-4 w-4" />
              <span className="hidden sm:inline">New ticket</span>
            </Link>
            <button
              type="button"
              onClick={handleWorkbookDownload}
              disabled={isExporting}
              className="inline-flex h-10 w-10 items-center justify-center rounded-full border border-amber-400/20 bg-amber-500/10 text-amber-100 transition hover:bg-amber-500/20"
              aria-label={isExporting ? "Preparing export" : "Export workbook"}
            >
              <FileSpreadsheet className="h-4 w-4" />
            </button>
            <NotificationBell />
          </div>
        </>
      }
    >
      {feed.status === "loading" ? (
        <div className="mt-6 grid gap-4">
          <div className="grid gap-4 grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-5">
            {Array.from({ length: 5 }).map((_, index) => (
              <div
                key={index}
                className="ops-card rounded-[22px] border border-zinc-800/60 bg-black/20 p-5"
              >
                <div className="h-3 w-24 rounded-full bg-zinc-800/90" />
                <div className="mt-5 h-10 w-20 rounded-full bg-zinc-800/80" />
                <div className="mt-4 h-3 w-full rounded-full bg-zinc-900/80" />
                <div className="mt-2 h-3 w-2/3 rounded-full bg-zinc-900/80" />
              </div>
            ))}
          </div>
          <div className="ops-card rounded-[22px] p-6">
            <SectionEmptyState
              title="Loading live workspace"
              message="Pulling tickets, metrics, and incident clusters from the API now."
            />
          </div>
        </div>
      ) : feed.status === "error" ? (
        <div className="mt-6 ops-card rounded-[22px] p-6">
          <div className="flex flex-col gap-4 border-b border-zinc-800/50 pb-5 sm:flex-row sm:items-center sm:justify-between">
            <div>
              <h2 className="text-2xl font-semibold text-zinc-50">Live data did not load</h2>
              <p className="mt-2 max-w-2xl text-sm leading-6 text-zinc-400">
                {feed.errorMessage || "The live API did not return a usable response for this workspace."}
              </p>
            </div>
            <button
              type="button"
              onClick={() => void hydrateFeed({ notifyOnError: true })}
              className="inline-flex items-center gap-2 rounded-full border border-amber-400/20 bg-amber-500/10 px-4 py-2.5 text-sm font-medium text-amber-100 transition hover:bg-amber-500/20"
            >
              <Activity className="h-4 w-4" />
              Retry live sync
            </button>
          </div>

          <div className="mt-5 grid gap-4 grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-5">
            {metrics.map((card) => {
              const Icon = card.icon;
              return (
                <div
                  key={card.label}
                  className={`ops-card relative overflow-hidden rounded-[22px] bg-gradient-to-br p-5 ${card.tone}`}
                >
                  <div className="flex items-center justify-between">
                    <div className="mono-data text-[10px] uppercase tracking-[0.28em] text-zinc-500">
                      {card.label}
                    </div>
                    <div className="rounded-2xl border border-white/10 bg-black/20 p-2">
                      <Icon className="h-4 w-4" />
                    </div>
                  </div>
                  <div className="mono-data mt-5 text-4xl font-bold tracking-tight text-zinc-50">0</div>
                  <p className="mt-3 text-sm leading-6 text-zinc-400">
                    Live values will appear after the next successful sync.
                  </p>
                </div>
              );
            })}
          </div>
        </div>
      ) : (
        <>
          <section id="overview" className="mt-6 grid gap-4 grid-cols-2 lg:grid-cols-4">
            {metrics.map((card) => {
              const Icon = card.icon;
              return (
                <div
                  key={card.label}
                  className={`ops-stat-tile relative overflow-hidden rounded-[22px] bg-gradient-to-br p-5 ${card.tone}`}
                >
                  <div className="flex items-center justify-between">
                    <div className="mono-data text-[10px] uppercase tracking-[0.28em] text-zinc-500">
                      {card.label}
                    </div>
                    <div className="rounded-2xl border border-white/10 bg-black/20 p-2">
                      <Icon className="h-4 w-4" />
                    </div>
                  </div>
                  <div className="mono-data mt-5 text-4xl font-bold tracking-tight text-zinc-50">{card.value}</div>
                  <p className="mt-3 text-sm leading-6 text-zinc-400">{card.note}</p>
                </div>
              );
            })}
          </section>

          <section id="decision" className="mt-6 grid gap-6 xl:grid-cols-[minmax(0,1.18fr),minmax(360px,0.82fr)]">
            <QueueTable
              tickets={filteredQueue}
              selectedId={selectedTicket?.ticketId ?? null}
              onSelect={setSelectedTicketId}
              searchTerm={searchTerm}
            />

            <GraphCommandLens
              selectedTicket={selectedTicket}
              linkedIncident={linkedIncident}
              relatedTickets={relatedTickets}
              categoryData={categoryData}
              assigneeData={assigneeData}
              edgeData={edgeData}
              intelligence={feed.intelligence}
              governance={feed.governance}
              incidents={incidentCards}
            />
          </section>

          <section id="tickets" className="mt-6 ops-card rounded-[22px] p-5 sm:p-6">
            <div className="flex flex-col gap-4 border-b border-zinc-800/50 pb-4 lg:flex-row lg:items-end lg:justify-between">
              <div>
                <h2 className="text-2xl font-semibold text-zinc-50">Full Ticket List</h2>
                <p className="mt-1 text-sm text-zinc-400">
                  {ticketRows.length} of {feed.tickets.length} tickets
                </p>
              </div>
              <div className="flex flex-wrap gap-2">
                {ticketFilterOptions.map((option) => (
                  <button
                    key={option.key}
                    type="button"
                    onClick={() => setTicketFilter(option.key)}
                    className={`inline-flex items-center gap-2 rounded-full border px-3 py-2 text-xs font-medium transition ${
                      ticketFilter === option.key
                        ? "border-amber-400/25 bg-amber-500/10 text-amber-100"
                        : "border-zinc-800/70 bg-black/20 text-zinc-400 hover:border-zinc-700"
                    }`}
                  >
                    <Filter className="h-3.5 w-3.5" />
                    {option.label}
                  </button>
                ))}
              </div>
            </div>

            <div className="mt-4 space-y-2">
              {ticketRows.length ? ticketRows.slice(0, 30).map((ticket) => (
                <Link
                  key={ticket.ticketId}
                  href={`/tickets/${ticket.ticketId}`}
                  className="flex items-center gap-4 rounded-2xl border border-zinc-800/60 bg-black/20 px-4 py-3 text-sm transition hover:border-amber-400/20 hover:bg-amber-500/[0.03]"
                >
                  <div className="mono-data shrink-0 text-[11px] text-zinc-500">{ticket.ticketId}</div>
                  <div className="min-w-0 flex-1">
                    <div className="flex items-center gap-2">
                      <span className="truncate text-zinc-100">{ticket.title}</span>
                    </div>
                    <div className="mt-1 flex flex-wrap gap-2 text-xs text-zinc-500">
                      <span>{ticket.category}</span>
                      <span>{ticket.assignee}</span>
                      <span className="mono-data">{ticket.daysOpen}d</span>
                    </div>
                  </div>
                  <span
                    className="shrink-0 rounded-full px-2.5 py-1 text-[11px] font-medium"
                    style={{
                      color: priorityPalette[ticket.priority] ?? "#d4d4d8",
                      backgroundColor: `${priorityPalette[ticket.priority] ?? "#71717a"}18`,
                    }}
                  >
                    {ticket.priority}
                  </span>
                  <span className="mono-data shrink-0 text-xs text-zinc-400">{ticket.score.toFixed(0)}</span>
                </Link>
              )) : (
                <SectionEmptyState
                  title="No tickets visible"
                  message={
                    searchTerm
                      ? "No tickets matched the current search and filter combination."
                      : "The live ticket stream is currently empty."
                  }
                />
              )}
              {ticketRows.length > 30 && (
                <div className="py-2 text-center text-sm text-zinc-500">
                  Showing 30 of {ticketRows.length}. Use search to narrow results.
                </div>
              )}
            </div>
          </section>
        </>
      )}
    </OpsShell>
  );
}

type DenseBarDatum = { name: string; value: number };

function DenseBarList({
  title,
  data,
  valueTone = "text-zinc-300",
  emptyLabel = "No data yet",
}: {
  title: string;
  data: DenseBarDatum[];
  valueTone?: string;
  emptyLabel?: string;
}) {
  const maxValue = Math.max(...data.map((item) => item.value), 0);

  return (
    <div className="border-t border-zinc-800/60 pt-3">
      <div className="mb-2 flex items-center justify-between gap-3">
        <div className="text-xs font-medium text-zinc-300">{title}</div>
        <div className="mono-data text-[10px] text-zinc-600">{data.length} rows</div>
      </div>
      <div className="space-y-1.5">
        {data.length ? (
          data.map((item) => {
            const width = maxValue > 0 ? Math.max(3, (item.value / maxValue) * 100) : 0;

            return (
              <div key={`${title}-${item.name}`} className="grid grid-cols-[96px,minmax(0,1fr),36px] items-center gap-2 text-[11px]">
                <span className="truncate text-zinc-500">{item.name}</span>
                <div className="h-[3px] overflow-hidden rounded-full bg-zinc-900/80">
                  <div className="h-full rounded-full bg-amber-500" style={{ width: `${width}%` }} />
                </div>
                <span className={`mono-data text-right ${valueTone}`}>{item.value}</span>
              </div>
            );
          })
        ) : (
          <div className="text-xs text-zinc-600">{emptyLabel}</div>
        )}
      </div>
    </div>
  );
}

function GraphCommandLens({
  selectedTicket,
  linkedIncident,
  relatedTickets,
  categoryData,
  assigneeData,
  edgeData,
  intelligence,
  governance,
  incidents,
}: {
  selectedTicket: QueueTicket | undefined;
  linkedIncident: IncidentCard | undefined;
  relatedTickets: QueueTicket[];
  categoryData: DenseBarDatum[];
  assigneeData: DenseBarDatum[];
  edgeData: DenseBarDatum[];
  intelligence: IntelligenceHealthResponse | null;
  governance: GovernanceSummaryResponse | null;
  incidents: IncidentCard[];
}) {
  const graph = intelligence?.subsystems.graph ?? governance?.graph;
  const graphUnavailable =
    graph && "status" in graph && graph.status === "unavailable";
  const graphNodes = graphUnavailable ? 0 : graph?.node_count ?? 0;
  const graphEdges = graphUnavailable ? 0 : graph?.edge_count ?? 0;
  const averageDegree = graphUnavailable ? 0 : graph?.average_degree ?? 0;
  const driftStatus = governance?.drift?.status ?? intelligence?.drift?.status ?? "unavailable";
  const incidentLabel = linkedIncident
    ? `${linkedIncident.ticketCount} linked ticket${linkedIncident.ticketCount === 1 ? "" : "s"}`
    : "No active incident";
  const selectedScore = selectedTicket ? selectedTicket.score.toFixed(0) : "--";
  const graphSignal = edgeData[0];

  return (
    <aside className="min-h-0 space-y-5 xl:sticky xl:top-6 xl:max-h-[calc(100dvh-3rem)] xl:overflow-y-auto xl:pr-1">
      <section className="ops-card overflow-hidden rounded-[22px] border-amber-500/20 p-3">
        <div className="flex items-center justify-between gap-4">
          <div className="min-w-0">
            <h2 className="text-lg font-semibold text-zinc-50">Graph Command Lens</h2>
          </div>
          <span className="mono-data shrink-0 rounded-full border border-amber-400/20 bg-amber-500/10 px-3 py-1.5 text-[10px] text-amber-200">
            live graph
          </span>
        </div>

        <div className="mt-3 rounded-[18px] border border-zinc-800/70 bg-black/25 p-2.5">
          <div className="flex items-start justify-between gap-4">
            <div className="min-w-0">
              <div className="mono-data text-[11px] text-zinc-500">
                {selectedTicket?.ticketId ?? "No ticket selected"}
              </div>
              <div className="mt-1 truncate text-sm font-medium text-zinc-100">
                {selectedTicket?.title ?? "Select a ranked ticket to load the command lens."}
              </div>
            </div>
            <div className="mono-data shrink-0 text-4xl font-bold leading-none text-amber-200">
              {selectedScore}
            </div>
          </div>
          <div className="mt-2 grid grid-cols-3 divide-x divide-zinc-800/70 border-t border-zinc-800/70 pt-2 text-center">
            <div className="px-2">
              <div className="mono-data text-sm font-semibold text-zinc-50">{graphNodes}</div>
              <div className="mt-1 text-[10px] text-zinc-500">nodes</div>
            </div>
            <div className="px-2">
              <div className="mono-data text-sm font-semibold text-zinc-50">{graphEdges}</div>
              <div className="mt-1 text-[10px] text-zinc-500">edges</div>
            </div>
            <div className="px-2">
              <div className="mono-data text-sm font-semibold text-amber-200">
                {averageDegree.toFixed(1)}
              </div>
              <div className="mt-1 text-[10px] text-zinc-500">avg degree</div>
            </div>
          </div>
        </div>

        <div className="mt-2 grid grid-cols-2 gap-2 text-sm 2xl:grid-cols-4">
          <div className="rounded-2xl border border-zinc-800/60 bg-black/15 p-2.5">
            <div className="text-[11px] text-zinc-500">Blast radius</div>
            <div className="mono-data mt-1 truncate text-amber-200">{incidentLabel}</div>
          </div>
          <div className="rounded-2xl border border-zinc-800/60 bg-black/15 p-2.5">
            <div className="text-[11px] text-zinc-500">Drift status</div>
            <div className="mono-data mt-1 text-zinc-200">{formatStatus(driftStatus)}</div>
          </div>
          <div className="rounded-2xl border border-zinc-800/60 bg-black/15 p-2.5">
            <div className="text-[11px] text-zinc-500">Primary relation</div>
            <div className="mono-data mt-1 truncate text-zinc-200">
              {graphSignal ? graphSignal.name : "none"}
            </div>
          </div>
          <div className="rounded-2xl border border-zinc-800/60 bg-black/15 p-2.5">
            <div className="text-[11px] text-zinc-500">Related work</div>
            <div className="mono-data mt-1 text-zinc-200">{relatedTickets.length} matches</div>
          </div>
        </div>

        <div className="mt-2 rounded-2xl border border-amber-500/20 bg-amber-500/[0.04] p-2.5">
          <div className="text-xs font-medium text-amber-100">Next action</div>
          <p className="mt-1 line-clamp-2 text-sm leading-6 text-zinc-300">
            {selectedTicket?.recommendation ?? "Select a ticket to inspect the next operational move."}
          </p>
        </div>

      </section>

      <DecisionDetailPanel
        selectedTicket={selectedTicket}
        linkedIncident={linkedIncident}
        rail
      />

      <section className="ops-card rounded-[22px] p-4">
        <div className="flex items-start justify-between gap-4 border-b border-zinc-800/60 pb-3">
          <div>
            <h3 className="text-lg font-semibold text-zinc-50">Signal Matrix</h3>
            <p className="mt-1 text-sm leading-6 text-zinc-400">
              Queue shape, owner load, and graph edge mix from the live workspace.
            </p>
          </div>
          <span className="mono-data rounded-full border border-zinc-800 bg-black/20 px-3 py-1.5 text-[10px] text-zinc-500">
            {graphEdges} edges
          </span>
        </div>
        <div className="mt-4 space-y-4">
          <DenseBarList title="Graph relation types" data={edgeData} valueTone="text-amber-300" emptyLabel="No graph edges yet" />
          <DenseBarList title="Top categories" data={categoryData} />
          <DenseBarList title="Assignee load" data={assigneeData} />
        </div>
        <div className="mt-4 border-t border-zinc-800/60 pt-3">
          <div className="mb-2 flex items-center justify-between gap-3">
            <div className="text-xs font-medium text-zinc-300">Related work</div>
            <div className="mono-data text-[10px] text-zinc-600">{relatedTickets.length} matches</div>
          </div>
          <div className="space-y-2">
            {relatedTickets.length ? (
              relatedTickets.map((ticket) => (
                <Link
                  key={ticket.ticketId}
                  href={`/tickets/${ticket.ticketId}`}
                  className="grid grid-cols-[88px,minmax(0,1fr),36px] items-center gap-2 rounded-2xl border border-zinc-800/60 bg-black/20 px-3 py-2 text-xs transition hover:border-amber-400/30 hover:bg-amber-500/[0.03]"
                >
                  <span className="mono-data truncate text-zinc-500">{ticket.ticketId}</span>
                  <span className="truncate text-zinc-300">{ticket.title}</span>
                  <span className="mono-data text-right text-amber-200">{ticket.score.toFixed(0)}</span>
                </Link>
              ))
            ) : (
              <div className="rounded-2xl border border-zinc-800/60 bg-black/20 px-3 py-3 text-xs text-zinc-500">
                No category, owner, priority, or incident neighbors in the active queue.
              </div>
            )}
          </div>
        </div>
      </section>

      <DecisionIntelligencePanel
        intelligence={intelligence}
        governance={governance}
      />
      <IncidentList incidents={incidents} />
    </aside>
  );
}

function formatStatus(status: string | undefined) {
  if (!status) {
    return "unavailable";
  }
  return status.replace(/_/g, " ");
}

function DecisionIntelligencePanel({
  intelligence,
  governance,
}: {
  intelligence: IntelligenceHealthResponse | null;
  governance: GovernanceSummaryResponse | null;
}) {
  const graph = intelligence?.subsystems.graph ?? governance?.graph;
  const graphUnavailable =
    graph && "status" in graph && graph.status === "unavailable";
  const drift = governance?.drift ?? intelligence?.drift;
  const driftStatus = drift?.status ?? "unavailable";
  const recommendationCount = intelligence?.subsystems.recommendations.count ?? 0;
  const similarLinks = intelligence?.subsystems.retrieval.similar_case_links ?? 0;
  const actionRuns = intelligence?.subsystems.action_runs.count ?? 0;
  const feedbackCount = intelligence?.subsystems.operator_feedback.count ?? 0;

  return (
    <section className="ops-card rounded-[22px] p-5">
      <div className="flex flex-col gap-3 border-b border-zinc-800/70 pb-4 sm:flex-row sm:items-start sm:justify-between">
        <div>
          <h3 className="text-lg font-semibold text-zinc-50">Decision intelligence</h3>
          <p className="mt-1 text-sm leading-6 text-zinc-400">
            Deterministic rules, graph links, drift checks, and recommendation feedback.
          </p>
        </div>
        <span className="inline-flex w-fit items-center rounded-full border border-amber-400/20 bg-amber-500/10 px-3 py-1.5 text-[11px] font-medium text-amber-100">
          No trained ML model
        </span>
      </div>

      {/* High-density intel stats: hairline + mono numbers, minimal containers (per AGENTS "shape rule for data surfaces").
          No generic rounded cards for counts; tight grid with subtle separators. */}
      <div className="mt-4 grid grid-cols-2 gap-x-4 gap-y-2 text-sm border-t border-zinc-800/50 pt-3">
        <div><span className="text-[10px] text-zinc-500">Graph nodes</span><div className="mono-data text-base font-semibold text-zinc-100 mt-0.5">{graphUnavailable ? "—" : (graph?.node_count ?? 0)}</div></div>
        <div><span className="text-[10px] text-zinc-500">Graph edges</span><div className="mono-data text-base font-semibold text-zinc-100 mt-0.5">{graphUnavailable ? "—" : (graph?.edge_count ?? 0)}</div></div>
        <div><span className="text-[10px] text-zinc-500">Drift status</span><div className="mono-data text-base font-semibold text-amber-300 mt-0.5">{formatStatus(driftStatus)}</div></div>
        <div><span className="text-[10px] text-zinc-500">Similar links</span><div className="mono-data text-base font-semibold text-zinc-100 mt-0.5">{similarLinks}</div></div>
        <div><span className="text-[10px] text-zinc-500">Recommendations</span><div className="mono-data text-base font-semibold text-zinc-100 mt-0.5">{recommendationCount}</div></div>
        <div><span className="text-[10px] text-zinc-500">Feedback / runs</span><div className="mono-data text-base font-semibold text-zinc-100 mt-0.5">{feedbackCount} / {actionRuns}</div></div>
      </div>

      {/* Graph + drift — enhanced dense visuals (hairline, mono, amber primary for graph data).
          Matches the custom snapshot bars above and the "deterministic rules, graph links, drift checks" truth. */}
      {graph && !graphUnavailable && graph.edges_by_type && Object.keys(graph.edges_by_type).length > 0 ? (
        <div className="mt-4 rounded-xl border border-zinc-800/60 bg-black/10 p-3">
          <div className="text-[10px] mono-data text-amber-400 mb-1.5">Relation types (ticket graph)</div>
          <div className="space-y-0.5">
            {Object.entries(graph.edges_by_type as Record<string, number>)
              .sort((a, b) => b[1] - a[1])
              .map(([k, v]) => {
                const vals = Object.values(graph.edges_by_type as Record<string, number>);
                const max = Math.max(...vals);
                const w = max > 0 ? (v / max) * 100 : 0;
                return (
                  <div key={k} className="flex items-center gap-2 text-[11px]">
                    <span className="w-28 truncate text-zinc-400 shrink-0 font-mono text-[10px]">{k.replace(/_/g, " ")}</span>
                    <div className="h-[2px] flex-1 bg-zinc-900/70 rounded overflow-hidden">
                      <div className="h-full bg-amber-500 transition-all" style={{ width: `${w}%` }} />
                    </div>
                    <span className="mono-data w-8 text-right text-amber-300 shrink-0">{v}</span>
                  </div>
                );
              })}
          </div>
          <div className="mt-1 text-[9px] mono-data text-zinc-600">feeds PageRank centrality • 0.10 score weight</div>
        </div>
      ) : null}

      {drift && driftStatus !== "unavailable" && (drift.priority_shift || drift.uncertainty_shift) ? (
        <div className="mt-3 rounded-xl border border-zinc-800/60 bg-black/10 p-3 text-[11px]">
          <div className="text-[10px] mono-data text-zinc-500 mb-1.5">Drift signals (weekly)</div>
          <div className="space-y-1">
            {drift.priority_shift ? (
              <div className="flex items-center gap-2">
                <span className="w-16 text-zinc-400">priority</span>
                <div className="flex-1 h-1.5 bg-zinc-900/70 rounded overflow-hidden">
                  <div className="h-full bg-rose-500" style={{ width: `${Math.min(Math.abs(drift.priority_shift.pct_change || 0) / 5, 100)}%` }} />
                </div>
                <span className="mono-data text-rose-300 tabular-nums">Δ {drift.priority_shift.delta} ({drift.priority_shift.pct_change}%)</span>
              </div>
            ) : null}
            {drift.uncertainty_shift ? (
              <div className="flex items-center gap-2">
                <span className="w-16 text-zinc-400">uncertainty</span>
                <div className="flex-1 h-1.5 bg-zinc-900/70 rounded overflow-hidden">
                  <div className="h-full bg-amber-500" style={{ width: `${Math.min(Math.abs(drift.uncertainty_shift.pct_change || 0) / 5, 100)}%` }} />
                </div>
                <span className="mono-data text-amber-300 tabular-nums">Δ {drift.uncertainty_shift.delta} ({drift.uncertainty_shift.pct_change}%)</span>
              </div>
            ) : null}
          </div>
          {drift.root_cause_spikes?.length ? (
            <div className="mt-1 text-[10px] text-zinc-500">root spikes: {drift.root_cause_spikes.slice(0,2).map((s: any) => s.root_cause).join(", ")}</div>
          ) : null}
        </div>
      ) : null}

      {driftStatus === "unavailable" || graphUnavailable ? (
        <div className="mt-4 rounded-2xl border border-rose-500/20 bg-rose-500/10 p-3 text-sm leading-6 text-rose-100">
          Intelligence data is partially unavailable. Run the production migration and recheck
          governance health after deploy.
        </div>
      ) : null}
    </section>
  );
}

// IntelStat component removed — inlined as hairline dense grid above for data-surface rules.
