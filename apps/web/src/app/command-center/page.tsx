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
  AlertTriangle,
  CheckCircle2,
  ChevronRight,
  Clock3,
  Columns3,
  Download,
  FileSpreadsheet,
  Filter,
  Gauge,
  Layers3,
  LogOut,
  MoreHorizontal,
  Plus,
  Radar,
  Search,
  Shield,
  ShieldAlert,
  Ticket as TicketIcon,
} from "lucide-react";

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

type RailItem =
  | {
      label: string;
      action: () => void;
      icon: ComponentType<{ className?: string }>;
    }
  | {
      label: string;
      href: "/board" | "/reports" | "/admin";
      icon: ComponentType<{ className?: string }>;
    };

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

function formatSync(seconds: number) {
  if (seconds < 60) {
    return `${seconds}s ago`;
  }
  const minutes = Math.floor(seconds / 60);
  if (minutes < 60) {
    return `${minutes}m ago`;
  }
  const hours = Math.floor(minutes / 60);
  return `${hours}h ago`;
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
    id: incident.id,
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


export default function CommandCenterPage() {
  const router = useRouter();
  const toast = useToast();
  const toastRef = useRef(toast);
  const [feed, setFeed] = useState<FeedState>(initialFeed);
  const [selectedTicketId, setSelectedTicketId] = useState<string | null>(null);
  const [search, setSearch] = useState("");
  const [ticketFilter, setTicketFilter] = useState<TicketFilter>("all");
  const [lastSyncSeconds, setLastSyncSeconds] = useState(0);
  const [moreOpen, setMoreOpen] = useState(false);
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

  function scrollToSection(id: string) {
    document.getElementById(id)?.scrollIntoView({ behavior: "smooth", block: "start" });
    setMoreOpen(false);
  }

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

  const railItems: RailItem[] = [
    { label: "Overview", action: () => scrollToSection("overview"), icon: Gauge },
    { label: "Command", action: () => scrollToSection("decision"), icon: Radar },
    { label: "Tickets", action: () => scrollToSection("tickets"), icon: TicketIcon },
    { label: "Board", href: "/board", icon: Columns3 },
    { label: "Reports", href: "/reports", icon: FileSpreadsheet },
    { label: "Admin", href: "/admin", icon: Shield },
  ];

  return (
    <div className="ops-grid relative min-h-[100dvh] bg-[var(--bg-deep)]">
      <div className="scan-line" />

      <button
        type="button"
        onClick={handleWorkbookDownload}
        disabled={isExporting}
        className="ops-floating-export inline-flex h-12 w-12 items-center justify-center rounded-2xl border border-amber-400/20 bg-amber-500 text-black shadow-[0_16px_36px_rgba(245,158,11,0.28)] transition hover:scale-[1.03] hover:bg-amber-400"
        title="Export workbook"
        aria-label={isExporting ? "Preparing workbook export" : "Export workbook"}
      >
        <Download className="h-4 w-4" />
      </button>

      <div className="relative z-10 grid min-h-[100dvh] lg:grid-cols-[72px,minmax(0,1fr)]">
        <aside className="ops-rail ops-shell z-20 hidden border-r border-zinc-800/50 px-2 py-4 lg:sticky lg:top-0 lg:flex lg:h-[100dvh] lg:flex-col">
          <div className="mx-auto flex h-11 w-11 items-center justify-center rounded-2xl border border-amber-400/20 bg-amber-500/10 text-amber-300">
            <Radar className="h-5 w-5" />
          </div>

          <nav className="mt-6 flex flex-1 flex-col justify-center gap-2">
            {railItems.map((item) => {
              const Icon = item.icon;
              const className =
                "group flex items-center gap-3 rounded-xl border border-transparent px-4 py-3 text-zinc-500 transition hover:border-zinc-700/60 hover:bg-zinc-900/60 hover:text-zinc-100";

              if ("href" in item) {
                return (
                  <Link key={item.label} href={item.href} className={className}>
                    <Icon className="h-4 w-4 shrink-0" />
                    <span className="ops-rail-label text-sm font-medium">{item.label}</span>
                  </Link>
                );
              }

              return (
                <button key={item.label} type="button" onClick={item.action} className={className}>
                  <Icon className="h-4 w-4 shrink-0" />
                  <span className="ops-rail-label text-sm font-medium">{item.label}</span>
                </button>
              );
            })}
          </nav>

          <div className="px-2 pb-2 pt-6">
            <div className="mx-auto flex h-10 w-10 items-center justify-center rounded-full bg-gradient-to-br from-amber-400 to-orange-600 text-xs font-bold text-black">
              AP
            </div>
          </div>
        </aside>

        <main className="ops-safe-bottom px-4 py-4 sm:px-6 lg:px-8 lg:py-6">
          <div className="ops-glass rounded-[28px] px-4 py-4 sm:px-6 sm:py-6">
            <header className="border-b border-zinc-800/50 pb-5">
              <div className="flex flex-col gap-4 xl:flex-row xl:items-start xl:justify-between">
                <div className="max-w-4xl">
                  <div className="flex flex-wrap items-center gap-3">
                    <p className="mono-data text-[10px] uppercase tracking-[0.32em] text-amber-300">
                      Aether OpsCenter
                    </p>
                    <div
                      className={`inline-flex items-center gap-2 rounded-full border px-3 py-1.5 text-[11px] ${
                        feed.status === "ready"
                          ? "border-emerald-500/20 bg-emerald-500/8 text-emerald-200"
                          : feed.status === "loading"
                            ? "border-cyan-500/20 bg-cyan-500/8 text-cyan-100"
                            : "border-rose-500/20 bg-rose-500/10 text-rose-100"
                      }`}
                    >
                      <span
                        className="h-2 w-2 rounded-full"
                        style={{
                          backgroundColor:
                            feed.status === "ready"
                              ? "#22c55e"
                              : feed.status === "loading"
                                ? "#22d3ee"
                                : "#fb7185",
                        }}
                      />
                      {feed.status === "ready"
                        ? "Live data active"
                        : feed.status === "loading"
                          ? "Syncing live data"
                          : "Live data unavailable"}
                    </div>
                  </div>
                </div>

                {/* Desktop action row */}
                <div className="hidden xl:flex flex-wrap gap-3">
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
                <div className="flex xl:hidden items-center gap-2">
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
              </div>

              <div className="mt-5 flex flex-col gap-3 lg:flex-row lg:items-center lg:justify-between">
                <div className="flex flex-wrap items-center gap-3 text-sm text-zinc-500">
                  <div className="inline-flex items-center gap-2 rounded-full border border-zinc-800/70 bg-black/20 px-3 py-2">
                    <Clock3 className="h-3.5 w-3.5" />
                    <span>
                      {feed.status === "ready"
                        ? `Last sync ${formatSync(lastSyncSeconds)}`
                        : feed.status === "loading"
                          ? "Waiting for first sync"
                          : "Last sync unavailable"}
                    </span>
                  </div>
                  {feed.warnings.map((warning) => (
                    <div
                      key={warning}
                      className="inline-flex items-center gap-2 rounded-full border border-amber-400/20 bg-amber-500/10 px-3 py-2 text-amber-100"
                    >
                      <AlertTriangle className="h-3.5 w-3.5" />
                      <span>{warning}</span>
                    </div>
                  ))}
                </div>

                <label className="relative block w-full max-w-md">
                  <Search className="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-zinc-600" />
                  <input
                    value={search}
                    onChange={(event) => setSearch(event.target.value)}
                    placeholder="Search queue, owner, category, or ticket"
                    className="w-full rounded-2xl border border-zinc-800 bg-black/20 py-3 pl-10 pr-4 text-sm text-zinc-100 outline-none transition placeholder:text-zinc-600 focus:border-amber-400/30"
                  />
                </label>
              </div>
            </header>

            {feed.status === "loading" ? (
              <div className="mt-6 grid gap-4">
                <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-4">
                  {Array.from({ length: 4 }).map((_, index) => (
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

                <div className="mt-5 grid gap-4 md:grid-cols-2 xl:grid-cols-4">
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
            <section id="overview" className="mt-6 grid gap-4 md:grid-cols-2 xl:grid-cols-4">
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

          </div>
        </main>
      </div>

      <nav className="ops-mobile-nav lg:hidden">
        <button type="button" onClick={() => scrollToSection("overview")} className="ops-mobile-item active">
          <Gauge className="h-4 w-4" />
          <span className="text-[9px] font-semibold uppercase tracking-[0.2em]">Overview</span>
        </button>
        <button type="button" onClick={() => scrollToSection("decision")} className="ops-mobile-item">
          <Radar className="h-4 w-4" />
          <span className="text-[9px] font-semibold uppercase tracking-[0.2em]">Queue</span>
        </button>
        <button type="button" onClick={() => scrollToSection("tickets")} className="ops-mobile-item">
          <TicketIcon className="h-4 w-4" />
          <span className="text-[9px] font-semibold uppercase tracking-[0.2em]">Tickets</span>
        </button>
        <Link href="/board" className="ops-mobile-item">
          <Columns3 className="h-4 w-4" />
          <span className="text-[9px] font-semibold uppercase tracking-[0.2em]">Board</span>
        </Link>
        <button type="button" onClick={() => setMoreOpen(true)} className="ops-mobile-item">
          <MoreHorizontal className="h-4 w-4" />
          <span className="text-[9px] font-semibold uppercase tracking-[0.2em]">More</span>
        </button>
      </nav>

      <div className="ops-mobile-sheet lg:hidden" data-open={moreOpen ? "true" : "false"}>
        <button
          type="button"
          aria-label="Close sheet"
          className="absolute inset-0 bg-black/60"
          onClick={() => setMoreOpen(false)}
        />
        <div className="ops-mobile-sheet-panel px-4 pb-[calc(1.5rem+env(safe-area-inset-bottom))] pt-3">
          <div className="mx-auto mb-4 h-1.5 w-12 rounded-full bg-zinc-700" />
          <div className="space-y-2">
            <button
              type="button"
              onClick={handleWorkbookDownload}
              disabled={isExporting}
              className="flex items-center justify-between rounded-2xl border border-zinc-800/70 bg-black/20 px-4 py-4 text-sm text-zinc-100"
            >
              <span className="flex items-center gap-3">
                <Download className="h-4 w-4 text-amber-300" />
                {isExporting ? "Preparing export..." : "Export workbook"}
              </span>
              <ChevronRight className="h-4 w-4 text-zinc-600" />
            </button>
            <Link
              href="/reports"
              className="flex items-center justify-between rounded-2xl border border-zinc-800/70 bg-black/20 px-4 py-4 text-sm text-zinc-100"
            >
              <span className="flex items-center gap-3">
                <Activity className="h-4 w-4 text-cyan-300" />
                Reports
              </span>
              <ChevronRight className="h-4 w-4 text-zinc-600" />
            </Link>
            <Link
              href="/board"
              className="flex items-center justify-between rounded-2xl border border-zinc-800/70 bg-black/20 px-4 py-4 text-sm text-zinc-100"
            >
              <span className="flex items-center gap-3">
                <Columns3 className="h-4 w-4 text-zinc-300" />
                Workflow board
              </span>
              <ChevronRight className="h-4 w-4 text-zinc-600" />
            </Link>
            <button
              type="button"
              onClick={() => scrollToSection("decision")}
              className="flex w-full items-center justify-between rounded-2xl border border-zinc-800/70 bg-black/20 px-4 py-4 text-sm text-zinc-100"
            >
              <span className="flex items-center gap-3">
                <ShieldAlert className="h-4 w-4 text-rose-300" />
                Incident clusters
              </span>
              <span className="mono-data text-xs text-zinc-500">{incidentCards.length}</span>
            </button>
            <button
              type="button"
              onClick={handleLogout}
              disabled={isSigningOut}
              className="flex w-full items-center justify-between rounded-2xl border border-zinc-800/70 bg-black/20 px-4 py-4 text-sm text-zinc-100 disabled:cursor-not-allowed disabled:opacity-70"
            >
              <span className="flex items-center gap-3">
                <LogOut className="h-4 w-4 text-rose-300" />
                {isSigningOut ? "Signing out..." : "Logout"}
              </span>
              <ChevronRight className="h-4 w-4 text-zinc-600" />
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}
