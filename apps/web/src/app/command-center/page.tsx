"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import {
  useCallback,
  startTransition,
  useDeferredValue,
  useEffect,
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
  Layers3,
  LogOut,
  Plus,
  Radar,
  Shield,
  ShieldAlert,
  Ticket as TicketIcon,
} from "lucide-react";

import { OpsShell } from "@/components/ops-shell";
import { SectionEmptyState } from "@/components/command-center/section-empty-state";
import { CompactStatusChart } from "@/components/command-center/status-donut";
import { PriorityStackChart } from "@/components/command-center/priority-donut";
import { TrendChart } from "@/components/command-center/trend-chart";
import { QueueTable } from "@/components/command-center/queue-table";
import { IncidentList } from "@/components/command-center/incident-list";
import { DecisionDetailPanel } from "@/components/command-center/decision-detail-panel";
import { priorityPalette, statusPalette, chartPalette } from "@/components/command-center/palettes";
import type { BreakdownItem, IncidentCard, QueueTicket } from "@/components/command-center/types";
import { NotificationBell, useToast } from "@/components/notifications";
import { clearStoredSession } from "@/lib/auth";
import type { Incident, Ticket } from "@/types";

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
  status: FeedStatus;
  syncedAt: number;
  errorMessage: string | null;
  warnings: string[];
};

type MetricCard = {
  label: string;
  value: number;
  note: string;
  tone: string;
  icon: ComponentType<{ className?: string }>;
};

type ActivityItem = {
  id: string;
  text: string;
  subtext: string;
  color: string;
};

type TicketFilter = "all" | "active" | "waiting" | "closed";

const ticketFilterOptions: Array<{ key: TicketFilter; label: string }> = [
  { key: "all", label: "All" },
  { key: "active", label: "Active" },
  { key: "waiting", label: "Waiting" },
  { key: "closed", label: "Closed" },
];

const initialFeed: FeedState = {
  tickets: [],
  incidents: [],
  metrics: null,
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

function aggregateCounts(values: string[], maxItems = 6): BreakdownItem[] {
  const counts = new Map<string, number>();
  values.forEach((value) => {
    const key = value || "Unknown";
    counts.set(key, (counts.get(key) ?? 0) + 1);
  });

  return Array.from(counts.entries())
    .sort((left, right) => right[1] - left[1])
    .slice(0, maxItems)
    .map(([label, value], index) => ({
      label,
      value,
      color:
        statusPalette[label] ??
        priorityPalette[label] ??
        chartPalette[index % chartPalette.length],
    }));
}

function describeAction(ticket: QueueTicket | undefined) {
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
  return ticket.recommendation;
}

async function fetchJsonWithTimeout<T>(path: string, timeoutMs = 3500): Promise<T> {
  const controller = new AbortController();
  const timer = window.setTimeout(() => controller.abort(), timeoutMs);

  try {
    const response = await fetch(path, {
      signal: controller.signal,
      cache: "no-store",
    });

    if (!response.ok) {
      throw new Error(await readExportError(response));
    }

    return (await response.json()) as T;
  } catch (error) {
    if (error instanceof DOMException && error.name === "AbortError") {
      throw new Error(`Timed out while loading ${path}.`);
    }

    if (error instanceof Error) {
      throw error;
    }

    throw new Error(`Could not load ${path}.`);
  } finally {
    window.clearTimeout(timer);
  }
}

function parseFilename(contentDisposition: string | null) {
  if (!contentDisposition) {
    return "aether_report.xlsx";
  }

  const encodedMatch = contentDisposition.match(/filename\*\s*=\s*UTF-8''([^;]+)/i);
  if (encodedMatch?.[1]) {
    try {
      return decodeURIComponent(encodedMatch[1]);
    } catch {
      return encodedMatch[1].replace(/["']/g, "");
    }
  }

  const filenameMatch = contentDisposition.match(/filename\s*=\s*("?)([^";]+)\1/i);
  if (filenameMatch?.[2]) {
    return filenameMatch[2];
  }

  return "aether_report.xlsx";
}

async function readExportError(response: Response) {
  const contentType = response.headers.get("content-type") || "";
  const body = await response.text().catch(() => "");

  if (contentType.includes("application/json")) {
    try {
      const data = JSON.parse(body) as unknown;
      if (data && typeof data === "object") {
        const record = data as Record<string, unknown>;
        if (typeof record.detail === "string") {
          return record.detail;
        }
        if (typeof record.message === "string") {
          return record.message;
        }
      }
    } catch {
      // Fall through to the raw body or generic status message below.
    }
  }

  return body || `Request failed with status ${response.status}.`;
}

function toQueueTicketFromLive(ticket: Ticket): QueueTicket {
  return {
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
    recommendation: describeAction({
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
      recommendation: "Validate ownership, root cause, and next concrete action.",
    }),
  };
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

function buildActivity(queue: QueueTicket[]): ActivityItem[] {
  return queue.slice(0, 6).map((ticket, index) => {
    let color = "#f59e0b";
    let verb = "triaged";

    if (ticket.status === "Resolved") {
      color = "#06b6d4";
      verb = "resolved";
    } else if (ticket.status === "Closed") {
      color = "#22c55e";
      verb = "closed";
    } else if (ticket.status === "Waiting for Info") {
      color = "#8b5cf6";
      verb = "parked";
    } else if (ticket.priority === "High" || ticket.priority === "Critical") {
      color = "#f97316";
      verb = "escalated";
    }

    return {
      id: ticket.ticketId,
      text: `${ticket.assignee} ${verb} ${ticket.ticketId}`,
      subtext: ticket.title,
      color: color || chartPalette[index % chartPalette.length],
    };
  });
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

function scrollToSection(id: string) {
  if (typeof document === "undefined") {
    return;
  }
  document.getElementById(id)?.scrollIntoView({ behavior: "smooth", block: "start" });
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
        const [ticketsResult, metricsResult, incidentsResult] = await Promise.allSettled([
          fetchJsonWithTimeout<Ticket[]>("/api/tickets?limit=160", 5000),
          fetchJsonWithTimeout<QueueMetrics>("/api/metrics", 5000),
          fetchJsonWithTimeout<Incident[]>("/api/incidents", 5000),
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

  const statusSlices = aggregateCounts(feed.tickets.map((ticket) => ticket.status), 5);
  const prioritySlices = aggregateCounts(feed.tickets.map((ticket) => ticket.priority_raw), 4);
  const requestTypeSlices = aggregateCounts(
    feed.tickets.map((ticket) => ticket.category || ticket.root_cause_hypothesis || "Unknown"),
    8,
  );
  const assigneeSlices = aggregateCounts(feed.tickets.map((ticket) => ticket.assignee || "Unassigned"), 5);
  const openMix = aggregateCounts(
    feed.tickets
      .filter((ticket) => !isClosedStatus(ticket.status))
      .map((ticket) => ticket.category || ticket.root_cause_hypothesis || "Unknown"),
    7,
  );

  const totalTickets = feed.tickets.length;
  const openTickets = feed.metrics?.total_open ?? rankedQueue.length;
  const closedResolved = feed.tickets.filter((ticket) => isClosedStatus(ticket.status)).length;
  const criticalOpen =
    feed.metrics?.critical ??
    feed.tickets.filter(
      (ticket) => !isClosedStatus(ticket.status) && ticket.priority_raw === "Critical",
    ).length;
  const slaRisk =
    feed.metrics?.sla_breach_risk ?? rankedQueue.filter((ticket) => ticket.daysOpen >= 3).length;
  const trendTickets = feed.tickets;
  const metrics: MetricCard[] = [
    {
      label: "Total Tickets",
      value: totalTickets,
      note: "Live ticket volume returned by the API.",
      tone: "from-amber-500/15 to-amber-500/[0.03] text-amber-100",
      icon: Layers3,
    },
    {
      label: "Open Queue",
      value: openTickets,
      note: `${slaRisk} cases drifting toward SLA risk.`,
      tone: "from-cyan-500/15 to-cyan-500/[0.03] text-cyan-100",
      icon: Gauge,
    },
    {
      label: "Closed / Resolved",
      value: closedResolved,
      note: "Completed work still visible in the live stream.",
      tone: "from-emerald-500/15 to-emerald-500/[0.03] text-emerald-100",
      icon: CheckCircle2,
    },
    {
      label: "Critical Open",
      value: criticalOpen,
      note: `${incidentCards.length} incident clusters currently tracked.`,
      tone: "from-rose-500/15 to-rose-500/[0.03] text-rose-100",
      icon: ShieldAlert,
    },
    {
      label: "SLA Risk",
      value: slaRisk,
      note:
        feed.metrics?.sla_breach_risk != null
          ? "Tickets within 75% of their SLA window, reported live by the metrics API."
          : "Open tickets open 3+ days, derived locally while the metrics API is unavailable.",
      tone: "from-orange-500/15 to-orange-500/[0.03] text-orange-100",
      icon: Clock3,
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
      return !isClosedStatus(ticket.status) && ticket.status !== "Waiting for Info";
    }
    if (ticketFilter === "waiting") {
      return ticket.status === "Waiting for Info";
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

  async function handleWorkbookDownload() {
    if (isExporting) {
      return;
    }

    setIsExporting(true);

    try {
      const response = await fetch("/api/reports/excel", {
        method: "GET",
        cache: "no-store",
      });

      if (!response.ok) {
        throw new Error(await readExportError(response));
      }

      const blob = await response.blob();
      if (blob.size === 0) {
        throw new Error("The workbook export was empty.");
      }

      const filename = parseFilename(response.headers.get("content-disposition"));
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

  const railItems = [
    { kind: "action" as const, label: "Overview", onClick: () => scrollToSection("overview"), icon: Gauge },
    { kind: "action" as const, label: "Command", onClick: () => scrollToSection("decision"), icon: Radar },
    { kind: "action" as const, label: "Tickets", onClick: () => scrollToSection("tickets"), icon: TicketIcon },
    { kind: "link" as const, href: "/board", label: "Board", icon: Columns3 },
    { kind: "link" as const, href: "/reports", label: "Reports", icon: FileSpreadsheet },
    { kind: "link" as const, href: "/admin", label: "Admin", icon: Shield },
  ];

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
    ...(incidentCards.length > 0
      ? [
          {
            kind: "action" as const,
            onClick: () => scrollToSection("decision"),
            label: `Incident clusters (${incidentCards.length})`,
            icon: ShieldAlert,
            tone: "rose" as const,
          },
        ]
      : []),
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
      subtitle="Live triage, incident intelligence, and operator actions in one cockpit."
      statusPill={statusPillFor(feed.status)}
      lastSyncSeconds={lastSyncSeconds}
      warnings={shellWarnings}
      search={{
        value: search,
        onChange: setSearch,
        placeholder: "Search queue, owner, category, or ticket",
      }}
      railItems={railItems}
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
      <section className="ops-command-strip rise">
        <div className="flex min-w-0 flex-col gap-4 lg:flex-row lg:items-center lg:justify-between">
          <div className="min-w-0">
            <div className="flex flex-wrap items-center gap-2">
              <span className="aether-eyebrow text-amber-300">Live Ops</span>
              <span className="aether-chip border-amber-400/25 bg-amber-500/10 text-amber-100">
                {feed.status === "ready" ? `${totalTickets} tickets indexed` : "sync pending"}
              </span>
              <span className="aether-chip">
                {feed.status === "ready" ? `${lastSyncSeconds}s since sync` : feed.status}
              </span>
            </div>
            <div className="mt-3 flex flex-wrap items-baseline gap-x-4 gap-y-1">
              <h2 className="text-2xl font-semibold tracking-tight text-zinc-50 sm:text-3xl">
                Operations cockpit
              </h2>
              <p className="text-sm text-zinc-400">
                Ranked queue, SLA pressure, incident clusters, and export state from the live API.
              </p>
            </div>
          </div>

          <div className="grid grid-cols-3 gap-2 lg:min-w-[420px]">
            <div className="ops-command-meter">
              <span>Open</span>
              <strong>{openTickets}</strong>
            </div>
            <div className="ops-command-meter">
              <span>SLA</span>
              <strong className="text-orange-200">{slaRisk}</strong>
            </div>
            <div className="ops-command-meter">
              <span>Clusters</span>
              <strong className="text-rose-200">{incidentCards.length}</strong>
            </div>
          </div>
        </div>
      </section>

      {feed.status === "loading" ? (
        <div className="mt-6 grid gap-4">
          <div className="grid gap-4 grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-5">
            {Array.from({ length: 5 }).map((_, index) => (
              <div
                key={index}
                className="ops-card rounded-[24px] border border-zinc-800/60 bg-black/20 p-5"
              >
                <div className="h-3 w-24 rounded-full bg-zinc-800/90" />
                <div className="mt-5 h-10 w-20 rounded-full bg-zinc-800/80" />
                <div className="mt-4 h-3 w-full rounded-full bg-zinc-900/80" />
                <div className="mt-2 h-3 w-2/3 rounded-full bg-zinc-900/80" />
              </div>
            ))}
          </div>
          <div className="ops-card rounded-[26px] p-6">
            <SectionEmptyState
              title="Loading live workspace"
              message="Pulling tickets, metrics, and incident clusters from the API now."
            />
          </div>
        </div>
      ) : feed.status === "error" ? (
        <div className="mt-6 ops-card rounded-[26px] p-6">
          <div className="flex flex-col gap-4 border-b border-zinc-800/50 pb-5 sm:flex-row sm:items-center sm:justify-between">
            <div>
              <div className="mono-data text-[10px] uppercase tracking-[0.28em] text-rose-300">
                Command center offline
              </div>
              <h2 className="mt-2 text-2xl font-semibold text-zinc-50">Live data did not load</h2>
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
                  className={`ops-card relative overflow-hidden rounded-[24px] bg-gradient-to-br p-5 ${card.tone}`}
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
          <section id="overview" className="mt-6 grid gap-4 grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-5">
            {metrics.map((card) => {
              const Icon = card.icon;
              return (
                <div
                  key={card.label}
                  className={`ops-stat-tile relative overflow-hidden rounded-[24px] bg-gradient-to-br p-5 ${card.tone}`}
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

          <section className="mt-6 grid gap-4 2xl:grid-cols-[1fr,1fr,0.95fr]">
            <CompactStatusChart data={statusSlices} />
            <PriorityStackChart data={prioritySlices} />
            <TrendChart tickets={trendTickets} />
          </section>

          <section id="decision" className="mt-6 grid gap-6 2xl:grid-cols-[1.15fr,0.85fr]">
            <QueueTable
              tickets={filteredQueue}
              selectedId={selectedTicket?.ticketId ?? null}
              onSelect={setSelectedTicketId}
              searchTerm={searchTerm}
            />
            <div className="space-y-6">
              <DecisionDetailPanel
                selectedTicket={selectedTicket}
                linkedIncident={linkedIncident}
              />
              <IncidentList incidents={incidentCards} />
            </div>
          </section>

          <section className="mt-6 grid gap-6 xl:grid-cols-[1fr,1fr]">
            <div className="ops-card rounded-[24px] p-5 sm:p-6">
              <div className="mono-data text-[10px] uppercase tracking-[0.28em] text-zinc-500">
                Top Request Types
              </div>
              <div className="mt-5 space-y-4">
                {requestTypeSlices.length ? requestTypeSlices.map((slice) => (
                    <div key={slice.label} className="flex items-center justify-between gap-3 text-sm">
                      <span
                        className="h-2 w-2 shrink-0 rounded-full"
                        style={{ backgroundColor: slice.color }}
                      />
                      <span className="flex-1 truncate text-zinc-300">{slice.label}</span>
                      <span className="mono-data text-zinc-500">{slice.value}</span>
                    </div>
                )) : (
                  <SectionEmptyState
                    title="No request mix"
                    message="Request-type distribution will appear when live tickets are available."
                  />
                )}
              </div>
            </div>

            <div className="ops-card rounded-[24px] p-5 sm:p-6">
              <div className="mono-data text-[10px] uppercase tracking-[0.28em] text-zinc-500">
                Team Workload
              </div>
              <div className="mt-5 space-y-4">
                {assigneeSlices.length ? assigneeSlices.map((slice) => (
                    <div key={slice.label} className="flex items-center justify-between gap-3 text-sm">
                      <div className="mono-data flex h-7 w-7 shrink-0 items-center justify-center rounded-full bg-gradient-to-br from-amber-400 to-cyan-400 text-[10px] font-bold text-black">
                        {slice.label.slice(0, 2).toUpperCase()}
                      </div>
                      <span className="flex-1 truncate text-zinc-300">{slice.label}</span>
                      <span className="mono-data rounded-full border border-zinc-800 bg-zinc-900/60 px-2.5 py-1 text-[11px] text-zinc-400">
                        {slice.value}
                      </span>
                    </div>
                )) : (
                  <SectionEmptyState
                    title="No workload yet"
                    message="Assignee workload will populate once the live queue returns ownership data."
                  />
                )}
              </div>
            </div>
          </section>

          <section className="mt-6 ops-card rounded-[24px] p-5 sm:p-6">
            <div className="flex flex-col gap-3 sm:flex-row sm:items-end sm:justify-between">
              <div>
                <div className="mono-data text-[10px] uppercase tracking-[0.28em] text-zinc-500">
                  Open Queue Composition
                </div>
                <p className="mt-2 text-sm leading-6 text-zinc-400">
                  These are the request pockets actually consuming the open queue right now.
                </p>
              </div>
              <div className="inline-flex items-center gap-2 rounded-full border border-zinc-800/60 bg-black/20 px-3 py-2 text-xs text-zinc-500">
                <Activity className="h-3.5 w-3.5" />
                Live composition
              </div>
            </div>
            <div className="mt-4 flex flex-wrap gap-2">
              {openMix.length ? openMix.map((slice) => (
                <div
                  key={slice.label}
                  className="rounded-full border px-3 py-2 text-xs font-medium"
                  style={{
                    borderColor: `${slice.color}35`,
                    backgroundColor: `${slice.color}18`,
                    color: slice.color,
                  }}
                >
                  {slice.label} <span className="mono-data opacity-70">{slice.value}</span>
                </div>
              )) : (
                <SectionEmptyState
                  title="No open queue composition"
                  message="Open-category composition will appear once live tickets are in flight."
                />
              )}
            </div>
          </section>

          <section id="tickets" className="mt-6 ops-card rounded-[26px] p-5 sm:p-6">
            <div className="flex flex-col gap-4 border-b border-zinc-800/50 pb-4 lg:flex-row lg:items-end lg:justify-between">
              <div>
                <h2 className="text-2xl font-semibold text-zinc-50">Ticket Stream</h2>
                <p className="mt-1 text-sm text-zinc-400">
                  Searchable, filterable, and export-adjacent instead of a thin afterthought.
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

            <div className="mt-4 overflow-hidden rounded-[22px] border border-zinc-800/60">
              <div className="ops-ticket-table bg-zinc-950/80 px-4 py-3 text-[11px] uppercase tracking-[0.24em] text-zinc-500">
                <div>ID</div>
                <div>Title</div>
                <div>Status</div>
                <div>Priority</div>
                <div>Owner</div>
              </div>

              {ticketRows.length ? ticketRows.map((ticket) => (
                <div key={ticket.ticketId}>
                  <Link
                    href={`/tickets/${ticket.ticketId}`}
                    className="ops-ticket-table items-center gap-3 border-t border-zinc-800/60 bg-black/10 px-4 py-4 text-sm transition hover:bg-white/[0.02]"
                  >
                    <div className="mono-data text-zinc-400">{ticket.ticketId}</div>
                    <div className="min-w-0">
                      <div className="truncate text-zinc-100">{ticket.title}</div>
                      <div className="mt-1 text-xs text-zinc-500">{ticket.category}</div>
                    </div>
                    <div className="text-zinc-400">{ticket.status}</div>
                    <div className="mono-data" style={{ color: priorityPalette[ticket.priority] ?? "#d4d4d8" }}>
                      {ticket.priority}
                    </div>
                    <div className="truncate text-zinc-500">{ticket.assignee}</div>
                  </Link>

                  <Link
                    href={`/tickets/${ticket.ticketId}`}
                    className="ops-ticket-card border-t border-zinc-800/60 bg-black/10 px-4 py-4 transition hover:bg-white/[0.02]"
                  >
                    <div className="flex items-start gap-3">
                      <div
                        className="mt-1 h-10 w-1 rounded-full"
                        style={{ backgroundColor: priorityPalette[ticket.priority] ?? "#71717a" }}
                      />
                      <div className="min-w-0 flex-1">
                        <div className="flex flex-wrap items-center gap-2">
                          <span className="mono-data text-[11px] text-zinc-500">{ticket.ticketId}</span>
                          <span
                            className="rounded-full px-2 py-1 text-[10px] font-medium"
                            style={{
                              color: priorityPalette[ticket.priority] ?? "#d4d4d8",
                              backgroundColor: `${priorityPalette[ticket.priority] ?? "#71717a"}18`,
                            }}
                          >
                            {ticket.priority}
                          </span>
                        </div>
                        <p className="mt-2 text-sm leading-6 text-zinc-100">{ticket.title}</p>
                        <div className="mt-3 flex flex-wrap items-center gap-2 text-xs text-zinc-500">
                          <span>{ticket.status}</span>
                          <span>{ticket.category}</span>
                          <span>{ticket.assignee}</span>
                          <span className="mono-data">{ticket.daysOpen}d</span>
                        </div>
                      </div>
                    </div>
                  </Link>
                </div>
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
            </div>
          </section>
        </>
      )}
    </OpsShell>
  );
}
