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
  AlertTriangle,
  ArrowUpRight,
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
  Radar,
  Search,
  ShieldAlert,
  Ticket as TicketIcon,
  Users,
} from "lucide-react";

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

type BreakdownItem = {
  label: string;
  value: number;
  color: string;
};

type QueueTicket = {
  ticketId: string;
  title: string;
  status: string;
  priority: string;
  score: number;
  assignee: string;
  category: string;
  daysOpen: number;
  createdAt?: string;
  incidentId?: string;
  recommendation: string;
  requester?: string;
};

type ActivityItem = {
  id: string;
  text: string;
  subtext: string;
  color: string;
};

type IncidentCard = {
  id: string;
  title: string;
  rootCause: string;
  ticketCount: number;
  confidence: number;
  impact: number;
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
      href: "/board" | "/reports";
      icon: ComponentType<{ className?: string }>;
    };

const statusPalette: Record<string, string> = {
  Closed: "#22c55e",
  Resolved: "#06b6d4",
  "In Progress": "#f59e0b",
  "Waiting for Info": "#8b5cf6",
  Open: "#f97316",
};

const priorityPalette: Record<string, string> = {
  Critical: "#f43f5e",
  High: "#f97316",
  Medium: "#f59e0b",
  Low: "#71717a",
};

const chartPalette = [
  "#f59e0b",
  "#06b6d4",
  "#8b5cf6",
  "#f97316",
  "#22c55e",
  "#ec4899",
  "#38bdf8",
  "#eab308",
];

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

function formatDate(value?: string) {
  if (!value) {
    return "--";
  }
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) {
    return value;
  }
  return new Intl.DateTimeFormat("en-US", {
    month: "short",
    day: "numeric",
    hour: "numeric",
    minute: "2-digit",
  }).format(date);
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

function useMountedFlag() {
  const [mounted, setMounted] = useState(false);

  useEffect(() => {
    const raf = window.requestAnimationFrame(() => setMounted(true));
    return () => window.cancelAnimationFrame(raf);
  }, []);

  return mounted;
}

function useElementWidth<T extends HTMLElement = HTMLDivElement>(fallbackWidth = 400, minWidth = 280) {
  const ref = useRef<T | null>(null);
  const [width, setWidth] = useState(fallbackWidth);

  useEffect(() => {
    const node = ref.current;
    if (!node) {
      return;
    }

    const update = () => {
      const next = Math.max(minWidth, Math.floor(node.getBoundingClientRect().width));
      setWidth(next);
    };

    update();

    if (typeof ResizeObserver === "undefined") {
      window.addEventListener("resize", update);
      return () => window.removeEventListener("resize", update);
    }

    const observer = new ResizeObserver(() => update());
    observer.observe(node);

    return () => observer.disconnect();
  }, [fallbackWidth, minWidth]);

  return { ref, width };
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

function SectionEmptyState({
  title,
  message,
}: {
  title: string;
  message: string;
}) {
  return (
    <div className="rounded-[20px] border border-dashed border-zinc-800/70 bg-black/15 px-4 py-8 text-center">
      <div className="mono-data text-[10px] uppercase tracking-[0.28em] text-zinc-500">{title}</div>
      <p className="mt-2 text-sm leading-6 text-zinc-400">{message}</p>
    </div>
  );
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

function CompactStatusChart({ data }: { data: BreakdownItem[] }) {
  const mounted = useMountedFlag();
  if (!data.length) {
    return (
      <div className="ops-card rounded-[24px] p-5 sm:p-6">
        <div className="mono-data text-[10px] uppercase tracking-[0.28em] text-zinc-500">
          Status Distribution
        </div>
        <div className="mt-4">
          <SectionEmptyState
            title="No ticket distribution"
            message="Status segments will appear once live tickets are available."
          />
        </div>
      </div>
    );
  }

  const total = data.reduce((sum, slice) => sum + slice.value, 0) || 1;
  const radius = 52;
  const strokeWidth = 10;
  const circumference = 2 * Math.PI * radius;
  const gap = 10;
  const available = circumference - gap * data.length;
  let offset = 0;

  const closedResolved = data
    .filter((s) => ["Closed", "Resolved"].includes(s.label))
    .reduce((sum, s) => sum + s.value, 0);
  const resolutionRate = total > 0 ? ((closedResolved / total) * 100).toFixed(1) : "0";
  const ariaLabel = data.length
    ? `Status distribution chart with ${data
        .map((slice) => `${slice.label} ${slice.value}`)
        .join(", ")}. Resolution rate ${resolutionRate} percent.`
    : "Status distribution chart with no data.";

  return (
    <div className="ops-card rounded-[24px] p-5 sm:p-6" role="img" aria-label={ariaLabel}>
      <div className="mono-data text-[10px] uppercase tracking-[0.28em] text-zinc-500">
        Status Distribution
      </div>
      <div className="mt-4 flex flex-col gap-5 md:flex-row md:items-center md:gap-6">
        <svg
          viewBox="0 0 140 140"
          className="mx-auto h-28 w-28 shrink-0 sm:h-32 sm:w-32 md:mx-0"
          aria-hidden="true"
          focusable="false"
        >
          <circle cx="70" cy="70" r={radius} fill="none" stroke="rgba(63,63,70,0.35)" strokeWidth={strokeWidth} />
          {data.map((slice) => {
            const length = (slice.value / total) * available;
            const displayLength = mounted ? length : 0;
            const node = (
              <circle
                key={slice.label}
                cx="70"
                cy="70"
                r={radius}
                fill="none"
                stroke={slice.color}
                strokeWidth={strokeWidth}
                strokeLinecap="round"
                strokeDasharray={`${displayLength} ${circumference}`}
                strokeDashoffset={-offset}
                transform="rotate(-90 70 70)"
                style={{
                  opacity: mounted ? 1 : 0.75,
                  transition: "stroke-dasharray 1.2s cubic-bezier(0.22,1,0.36,1), opacity 0.5s ease",
                }}
              />
            );
            offset += length + gap;
            return node;
          })}
          <text x="70" y="66" textAnchor="middle" className="fill-zinc-50 text-[20px] font-bold">
            {total}
          </text>
          <text x="70" y="82" textAnchor="middle" className="fill-zinc-500 text-[7px]" style={{ fontFamily: "var(--font-mono), monospace", letterSpacing: "0.2em" }}>
            TOTAL
          </text>
        </svg>
        <div className="w-full space-y-3">
          {data.map((slice) => (
            <div key={slice.label} className="flex items-center gap-2.5">
              <span className="h-2.5 w-2.5 rounded-full shrink-0" style={{ backgroundColor: slice.color }} />
              <span className="w-[76px] shrink-0 text-[12px] text-zinc-300 sm:w-[84px]">{slice.label}</span>
              <div className="h-1 flex-1 rounded-full bg-zinc-900/80 overflow-hidden">
                <div
                  className="h-full rounded-full transition-all duration-1000 ease-out"
                  style={{
                    width: mounted ? `${Math.max((slice.value / total) * 100, 2)}%` : "0%",
                    backgroundColor: slice.color,
                  }}
                />
              </div>
              <span className="mono-data text-[12px] text-zinc-400 w-6 text-right shrink-0">
                {slice.value}
              </span>
            </div>
          ))}
        </div>
      </div>
      <div className="mt-4 flex items-center gap-2 border-t border-zinc-800/30 pt-3">
        <span className="text-[9px] mono-data text-zinc-600 uppercase tracking-wider">Resolution Rate</span>
        <span className="text-sm mono-data font-semibold text-emerald-400">{resolutionRate}%</span>
      </div>
    </div>
  );
}

function PriorityStackChart({ data }: { data: BreakdownItem[] }) {
  const mounted = useMountedFlag();
  if (!data.length) {
    return (
      <div className="ops-card rounded-[24px] p-5 sm:p-6">
        <div className="mono-data text-[10px] uppercase tracking-[0.28em] text-zinc-500">
          Priority Breakdown
        </div>
        <div className="mt-4">
          <SectionEmptyState
            title="No priority mix"
            message="Priority distribution will populate after the live queue loads."
          />
        </div>
      </div>
    );
  }

  const total = data.reduce((sum, slice) => sum + slice.value, 0) || 1;
  const lowPriority = data.find((s) => s.label === "Low")?.value || 0;
  const lowPercent = total > 0 ? Math.round((lowPriority / total) * 100) : 0;
  const ariaLabel = data.length
    ? `Priority breakdown chart with ${data.map((slice) => `${slice.label} ${slice.value}`).join(", ")}. Low priority share ${lowPercent} percent.`
    : "Priority breakdown chart with no data.";

  return (
    <div className="ops-card rounded-[24px] p-5 sm:p-6" role="img" aria-label={ariaLabel}>
      <div className="mono-data text-[10px] uppercase tracking-[0.28em] text-zinc-500">
        Priority Breakdown
      </div>
      <div className="mt-5 flex h-3 rounded-md overflow-hidden">
        {data.map((slice) => (
          <div
            key={slice.label}
            className="transition-all duration-300 hover:brightness-125"
            style={{
              width: mounted ? `${(slice.value / total) * 100}%` : "0%",
              backgroundColor: slice.color,
            }}
            title={`${slice.label}: ${slice.value}`}
          />
        ))}
      </div>
      <div className="mt-5 space-y-3">
        {data.map((slice) => (
          <div key={slice.label} className="flex items-center gap-2.5">
            <span className="h-2.5 w-2.5 rounded-full shrink-0" style={{ backgroundColor: slice.color }} />
            <span className="w-16 shrink-0 text-[12px] text-zinc-300">{slice.label}</span>
            <div className="h-1 flex-1 rounded-full bg-zinc-900/80 overflow-hidden">
              <div
                className="h-full rounded-full transition-all duration-1000"
                style={{
                  width: mounted ? `${Math.max((slice.value / total) * 100, 2)}%` : "0%",
                  backgroundColor: slice.color,
                }}
              />
            </div>
            <span className="mono-data text-[12px] text-zinc-400 w-7 text-right shrink-0">
              {slice.value}
            </span>
            <span className="mono-data text-[10px] text-zinc-600 w-8 text-right shrink-0">
              {Math.round((slice.value / total) * 100)}%
            </span>
          </div>
        ))}
      </div>
      <div className="mt-4 pt-3 border-t border-zinc-800/30 flex items-center gap-2">
        <svg className="w-3.5 h-3.5 text-emerald-500 shrink-0" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth="2">
          <path strokeLinecap="round" strokeLinejoin="round" d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z" />
        </svg>
        <span className="text-[10px] text-zinc-500">{lowPercent}% low priority — healthy distribution</span>
      </div>
    </div>
  );
}

type TrendData = {
  labels: string[];
  created: number[];
  resolved: number[];
};

function computeTrendData(tickets: Ticket[]): TrendData {
  const now = new Date();
  const days = 14;
  const labels: string[] = [];
  const created: number[] = [];
  const resolved: number[] = [];

  for (let i = days - 1; i >= 0; i--) {
    const date = new Date(now);
    date.setDate(date.getDate() - i);
    const dateStr = date.toLocaleDateString("en-US", { month: "short", day: "numeric" });
    labels.push(dateStr);

    const dayStart = new Date(date);
    dayStart.setHours(0, 0, 0, 0);
    const dayEnd = new Date(date);
    dayEnd.setHours(23, 59, 59, 999);

    const dayCreated = tickets.filter((t) => {
      if (!t.created_at) return false;
      const createdDate = new Date(t.created_at);
      return createdDate >= dayStart && createdDate <= dayEnd;
    }).length;

    const dayResolved = tickets.filter((t) => {
      if (!t.resolved_at) return false;
      const resolvedDate = new Date(t.resolved_at);
      return resolvedDate >= dayStart && resolvedDate <= dayEnd;
    }).length;

    created.push(dayCreated);
    resolved.push(dayResolved);
  }

  return { labels, created, resolved };
}

function TrendChart({ tickets }: { tickets: Ticket[] }) {
  const mounted = useMountedFlag();
  const { ref: chartWrapRef, width: chartWidth } = useElementWidth<HTMLDivElement>(400, 280);
  const trend = useMemo(() => computeTrendData(tickets), [tickets]);
  const total14dCreated = trend.created.reduce((a, b) => a + b, 0);
  const total14dResolved = trend.resolved.reduce((a, b) => a + b, 0);
  const netBacklog = total14dCreated - total14dResolved;
  const isEmpty = total14dCreated === 0 && total14dResolved === 0;
  const [hoveredIndex, setHoveredIndex] = useState<number | null>(null);

  const svgWidth = Math.max(chartWidth, 280);
  const svgHeight = chartWidth < 360 ? 168 : 152;
  const pad = { l: 8, r: 8, t: 12, b: 28 };
  const cW = svgWidth - pad.l - pad.r;
  const cH = svgHeight - pad.t - pad.b;
  const xS = trend.labels.length > 1 ? cW / (trend.labels.length - 1) : cW;
  const maxV = Math.max(...trend.created, ...trend.resolved, 1);

  const yP = (v: number) => pad.t + cH - (v / maxV) * cH;
  const xP = (i: number) => pad.l + i * xS;
  const activeIndex = hoveredIndex ?? -1;

  const activePoint =
    activeIndex >= 0
      ? {
          index: activeIndex,
          label: trend.labels[activeIndex],
          created: trend.created[activeIndex],
          resolved: trend.resolved[activeIndex],
          x: xP(activeIndex),
          createdY: yP(trend.created[activeIndex]),
          resolvedY: yP(trend.resolved[activeIndex]),
        }
      : null;

  function crPath(pts: [number, number][]) {
    if (pts.length < 2) return "";
    let d = `M ${pts[0][0].toFixed(1)},${pts[0][1].toFixed(1)}`;
    for (let i = 0; i < pts.length - 1; i++) {
      const p0 = pts[Math.max(0, i - 1)];
      const p1 = pts[i];
      const p2 = pts[i + 1];
      const p3 = pts[Math.min(pts.length - 1, i + 2)];
      d += ` C ${(p1[0] + (p2[0] - p0[0]) / 6).toFixed(1)},${(p1[1] + (p2[1] - p0[1]) / 6).toFixed(1)} ${(p2[0] - (p3[0] - p1[0]) / 6).toFixed(1)},${(p2[1] - (p3[1] - p1[1]) / 6).toFixed(1)} ${p2[0].toFixed(1)},${p2[1].toFixed(1)}`;
    }
    return d;
  }

  const cPts = trend.created.map((v, i) => [xP(i), yP(v)] as [number, number]);
  const rPts = trend.resolved.map((v, i) => [xP(i), yP(v)] as [number, number]);
  const cLine = crPath(cPts);
  const rLine = crPath(rPts);
  const cArea = `${cLine} L ${xP(trend.labels.length - 1).toFixed(1)},${(pad.t + cH).toFixed(1)} L ${xP(0).toFixed(1)},${(pad.t + cH).toFixed(1)} Z`;
  const rArea = `${rLine} L ${xP(trend.labels.length - 1).toFixed(1)},${(pad.t + cH).toFixed(1)} L ${xP(0).toFixed(1)},${(pad.t + cH).toFixed(1)} Z`;
  const hasMeaningfulData = !isEmpty;
  const labelStep = chartWidth < 360 ? 3 : 2;
  const tooltipLeft = activePoint ? Math.min(svgWidth - 24, Math.max(activePoint.x, 24)) : 0;
  const tooltipTop = activePoint ? Math.max(Math.min(activePoint.createdY, activePoint.resolvedY) - 10, 8) : 0;
  const daySegmentBounds = trend.labels.map((_, index) => {
    const center = xP(index);
    const left = index === 0 ? pad.l : (xP(index - 1) + center) / 2;
    const right = index === trend.labels.length - 1 ? svgWidth - pad.r : (center + xP(index + 1)) / 2;
    return { left, width: Math.max(right - left, 1) };
  });

  if (!hasMeaningfulData) {
    return (
      <div className="ops-card rounded-[24px] p-5 sm:p-6" role="img" aria-label="14-day trend chart. No ticket activity in the last 14 days.">
        <div className="flex items-start justify-between gap-4">
          <div className="mono-data text-[10px] uppercase tracking-[0.28em] text-zinc-500">14-Day Trend</div>
          <div className="flex items-center gap-4">
            <div className="flex items-center gap-1.5">
              <span className="h-[2px] w-3 rounded-full bg-amber-500" />
              <span className="mono-data text-[10px] text-zinc-500">Created</span>
            </div>
            <div className="flex items-center gap-1.5">
              <span className="h-[2px] w-3 rounded-full bg-emerald-500" />
              <span className="mono-data text-[10px] text-zinc-500">Resolved</span>
            </div>
          </div>
        </div>

        <div className="mt-3 flex h-[168px] items-center justify-center rounded-[20px] border border-dashed border-zinc-800/70 bg-black/15 px-4 text-center">
          <div>
            <div className="mono-data text-[10px] uppercase tracking-[0.28em] text-zinc-500">No ticket activity</div>
            <p className="mt-2 text-sm leading-6 text-zinc-400">
              The last 14 days are empty, so there is no trend line to draw yet.
            </p>
          </div>
        </div>

        <div className="mt-4 pt-3 border-t border-zinc-800/30 flex items-center justify-between">
          <div className="flex items-center gap-4">
            <div>
              <span className="text-[9px] mono-data text-zinc-600 uppercase tracking-wider">14d Created</span>
              <div className="mono-data text-[13px] font-semibold text-zinc-300 mt-0.5">0</div>
            </div>
            <div>
              <span className="text-[9px] mono-data text-zinc-600 uppercase tracking-wider">14d Resolved</span>
              <div className="mono-data text-[13px] font-semibold text-zinc-300 mt-0.5">0</div>
            </div>
          </div>
          <div className="text-right">
            <span className="text-[9px] mono-data text-zinc-600 uppercase tracking-wider">Net</span>
            <div className="mono-data mt-0.5 text-[13px] font-semibold text-emerald-400">
              0 <span className="text-[10px] font-normal text-zinc-600">backlog</span>
            </div>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="ops-card rounded-[24px] p-5 sm:p-6">
      <div className="flex flex-col gap-3 sm:flex-row sm:items-start sm:justify-between">
        <div className="mono-data text-[10px] uppercase tracking-[0.28em] text-zinc-500">14-Day Trend</div>
        <div className="flex flex-wrap items-center gap-4">
          <div className="flex items-center gap-1.5">
            <span className="w-3 h-[2px] rounded-full bg-amber-500" />
            <span className="text-[10px] mono-data text-zinc-500">Created</span>
          </div>
          <div className="flex items-center gap-1.5">
            <span className="w-3 h-[2px] rounded-full bg-emerald-500" />
            <span className="text-[10px] mono-data text-zinc-500">Resolved</span>
          </div>
        </div>
      </div>

      <div ref={chartWrapRef} className="mt-3 relative" style={{ height: svgHeight }}>
        <svg
          width="100%"
          height="100%"
          viewBox={`0 0 ${svgWidth} ${svgHeight}`}
          preserveAspectRatio="xMidYMid meet"
          role="img"
          aria-label={`14-day created and resolved trend chart. ${trend.labels[0]} through ${trend.labels[trend.labels.length - 1]}.`}
        >
          <defs>
            <linearGradient id="grad-c" x1="0" y1="0" x2="0" y2="1">
              <stop offset="0%" stopColor="#f59e0b" stopOpacity="0.25" />
              <stop offset="100%" stopColor="#f59e0b" stopOpacity="0.01" />
            </linearGradient>
            <linearGradient id="grad-r" x1="0" y1="0" x2="0" y2="1">
              <stop offset="0%" stopColor="#22c55e" stopOpacity="0.2" />
              <stop offset="100%" stopColor="#22c55e" stopOpacity="0.01" />
            </linearGradient>
          </defs>

          {[2, 4, 6, 8].map((v) => (
            <line
              key={v}
              x1={pad.l}
              y1={yP(v)}
              x2={svgWidth - pad.r}
              y2={yP(v)}
              stroke="rgba(63,63,70,0.18)"
              strokeWidth="1"
              strokeDasharray="4 4"
            />
          ))}

          <path
            d={cArea}
            fill="url(#grad-c)"
            className="transition-opacity duration-700 ease-out"
            style={{ opacity: mounted ? 0.6 : 0 }}
          />
          <path
            d={rArea}
            fill="url(#grad-r)"
            className="transition-opacity duration-700 ease-out"
            style={{ opacity: mounted ? 0.6 : 0 }}
          />
          <path
            d={cLine}
            fill="none"
            stroke="#f59e0b"
            strokeWidth="2"
            strokeLinecap="round"
            strokeLinejoin="round"
            pathLength={100}
            strokeDasharray="100 100"
            strokeDashoffset={mounted ? 0 : 100}
            className="transition-[stroke-dashoffset] duration-1000 ease-out"
          />
          <path
            d={rLine}
            fill="none"
            stroke="#22c55e"
            strokeWidth="2"
            strokeLinecap="round"
            strokeLinejoin="round"
            pathLength={100}
            strokeDasharray="100 100"
            strokeDashoffset={mounted ? 0 : 100}
            className="transition-[stroke-dashoffset] duration-1000 ease-out"
          />

          {activePoint && (
            <>
              <line
                x1={activePoint.x}
                y1={pad.t}
                x2={activePoint.x}
                y2={pad.t + cH}
                stroke="rgba(245, 158, 11, 0.35)"
                strokeWidth="1"
                strokeDasharray="4 4"
              />
              <circle cx={activePoint.x} cy={activePoint.createdY} r="3.5" fill="#f59e0b" stroke="#09090b" strokeWidth="2" />
              <circle cx={activePoint.x} cy={activePoint.resolvedY} r="3.5" fill="#22c55e" stroke="#09090b" strokeWidth="2" />
            </>
          )}

          {daySegmentBounds.map((segment, index) => (
            <rect
              key={trend.labels[index]}
              x={segment.left}
              y={pad.t}
              width={segment.width}
              height={cH}
              fill="transparent"
              tabIndex={0}
              role="button"
              aria-label={`${trend.labels[index]}: created ${trend.created[index]}, resolved ${trend.resolved[index]}`}
              onFocus={() => setHoveredIndex(index)}
              onBlur={() => setHoveredIndex((current) => (current === index ? null : current))}
              onMouseEnter={() => setHoveredIndex(index)}
              onMouseMove={() => setHoveredIndex(index)}
              onMouseLeave={() => setHoveredIndex((current) => (current === index ? null : current))}
              onClick={() => setHoveredIndex(index)}
              onKeyDown={(event) => {
                if (event.key === "Escape") {
                  setHoveredIndex(null);
                }
              }}
            />
          ))}
        </svg>

        {activePoint && (
          <div
            className="pointer-events-none absolute z-20 min-w-40 rounded-2xl border border-zinc-700/70 bg-[#0a0a0d]/95 px-3 py-2 shadow-2xl backdrop-blur-xl"
            style={{
              left: `${(tooltipLeft / svgWidth) * 100}%`,
              top: `${(tooltipTop / svgHeight) * 100}%`,
              transform: "translate(-50%, -100%)",
            }}
          >
            <div className="mono-data text-[10px] uppercase tracking-[0.24em] text-zinc-500">{activePoint.label}</div>
            <div className="mt-2 space-y-1.5 text-[11px] text-zinc-300">
              <div className="flex items-center justify-between gap-4">
                <span className="text-zinc-500">Created</span>
                <span className="mono-data text-amber-300">{activePoint.created}</span>
              </div>
              <div className="flex items-center justify-between gap-4">
                <span className="text-zinc-500">Resolved</span>
                <span className="mono-data text-emerald-300">{activePoint.resolved}</span>
              </div>
            </div>
          </div>
        )}
      </div>

      <div className="flex justify-between mt-1.5 px-0.5">
        {trend.labels.map((label, i) => (
          <span key={label} className="mono-data text-[9px] text-zinc-600">
            {i % labelStep !== 0 && i !== trend.labels.length - 1 ? "" : label.split(" ")[1]}
          </span>
        ))}
      </div>

      <div className="mt-4 pt-3 border-t border-zinc-800/30 flex items-center justify-between">
        <div className="flex items-center gap-4">
          <div>
            <span className="text-[9px] mono-data text-zinc-600 uppercase tracking-wider">14d Created</span>
            <div className="mono-data text-[13px] text-zinc-300 font-semibold mt-0.5">{total14dCreated}</div>
          </div>
          <div>
            <span className="text-[9px] mono-data text-zinc-600 uppercase tracking-wider">14d Resolved</span>
            <div className="mono-data text-[13px] text-zinc-300 font-semibold mt-0.5">{total14dResolved}</div>
          </div>
        </div>
        <div className="text-right">
          <span className="text-[9px] mono-data text-zinc-600 uppercase tracking-wider">Net</span>
          <div className={`mono-data text-[13px] font-semibold mt-0.5 ${netBacklog >= 0 ? "text-amber-400" : "text-emerald-400"}`}>
            {netBacklog >= 0 ? "+" : ""}{netBacklog} <span className="text-[10px] text-zinc-600 font-normal">backlog</span>
          </div>
        </div>
      </div>
    </div>
  );
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
  ];

  return (
    <div className="ops-grid relative min-h-screen bg-[var(--bg-deep)]">
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

      <div className="relative z-10 grid min-h-screen lg:grid-cols-[72px,minmax(0,1fr)]">
        <aside className="ops-rail ops-shell z-20 hidden border-r border-zinc-800/50 px-2 py-4 lg:sticky lg:top-0 lg:flex lg:h-screen lg:flex-col">
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

                <div className="flex flex-wrap gap-3">
                  <button
                    type="button"
                    onClick={handleWorkbookDownload}
                    disabled={isExporting}
                    className="inline-flex items-center gap-2 rounded-full border border-amber-400/20 bg-amber-500/10 px-4 py-2.5 text-sm font-medium text-amber-100 transition hover:bg-amber-500/20"
                  >
                    <FileSpreadsheet className="h-4 w-4" />
                    {isExporting ? "Preparing export..." : "Export workbook"}
                  </button>
                  <Link
                    href="/board"
                    className="inline-flex items-center gap-2 rounded-full border border-zinc-700/60 bg-zinc-900/60 px-4 py-2.5 text-sm font-medium text-zinc-200 transition hover:border-zinc-500"
                  >
                    <Columns3 className="h-4 w-4" />
                    Workflow board
                  </Link>
                  <Link
                    href="/reports"
                    className="inline-flex items-center gap-2 rounded-full border border-zinc-700/60 bg-zinc-900/60 px-4 py-2.5 text-sm font-medium text-zinc-200 transition hover:border-zinc-500"
                  >
                    <Activity className="h-4 w-4" />
                    Reports
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
              <div className="ops-card rounded-[26px] p-5 sm:p-6">
                <div className="flex flex-col gap-3 border-b border-zinc-800/50 pb-4 sm:flex-row sm:items-end sm:justify-between">
                  <div>
                    <h2 className="text-2xl font-semibold text-zinc-50">Ranked Queue</h2>
                    <p className="mt-1 text-sm text-zinc-400">
                      Search, inspect, and route the highest-value live tickets first.
                    </p>
                  </div>
                  <span className="mono-data text-[11px] uppercase tracking-[0.22em] text-amber-300">
                    {filteredQueue.length} visible
                  </span>
                </div>

                <div className="mt-4 space-y-3">
                  {filteredQueue.length ? filteredQueue.map((ticket, index) => (
                    <button
                      key={ticket.ticketId}
                      type="button"
                      onClick={() => setSelectedTicketId(ticket.ticketId)}
                      className={`block w-full rounded-[20px] border px-4 py-4 text-left transition ${
                        selectedTicket?.ticketId === ticket.ticketId
                          ? "border-amber-400/30 bg-amber-500/[0.06]"
                          : "border-zinc-800/60 bg-black/20 hover:border-amber-400/20 hover:bg-amber-500/[0.03]"
                      }`}
                    >
                      <div className="grid gap-4 xl:grid-cols-[48px,minmax(0,1fr),124px] xl:items-center">
                        <div className="mono-data flex h-12 w-12 items-center justify-center rounded-2xl border border-zinc-800 bg-zinc-950 text-sm text-zinc-300">
                          #{index + 1}
                        </div>

                        <div className="min-w-0">
                          <div className="flex flex-wrap items-center gap-2">
                            <span className="mono-data text-[11px] uppercase tracking-[0.22em] text-zinc-500">
                              {ticket.ticketId}
                            </span>
                            <span
                              className="rounded-full px-2.5 py-1 text-[11px] font-medium"
                              style={{
                                color: priorityPalette[ticket.priority] ?? "#d4d4d8",
                                backgroundColor: `${priorityPalette[ticket.priority] ?? "#71717a"}18`,
                              }}
                            >
                              {ticket.priority}
                            </span>
                            <span
                              className="rounded-full px-2.5 py-1 text-[11px] font-medium"
                              style={{
                                color: statusPalette[ticket.status] ?? "#d4d4d8",
                                backgroundColor: `${statusPalette[ticket.status] ?? "#52525b"}18`,
                              }}
                            >
                              {ticket.status}
                            </span>
                          </div>
                          <p className="mt-2 text-sm leading-6 text-zinc-100">{ticket.title}</p>
                          <div className="mt-3 flex flex-wrap gap-3 text-xs text-zinc-500">
                            <span>{ticket.category}</span>
                            <span>{ticket.assignee}</span>
                            <span>{ticket.daysOpen}d open</span>
                          </div>
                        </div>

                        <div className="text-left xl:text-right">
                          <div className="mono-data text-3xl font-bold tracking-tight text-zinc-50">
                            {ticket.score.toFixed(0)}
                          </div>
                          <div className="mt-1 inline-flex items-center gap-1 text-xs text-zinc-500">
                            Decision score
                            <ChevronRight className="h-3.5 w-3.5" />
                          </div>
                        </div>
                      </div>
                    </button>
                  )) : (
                    <SectionEmptyState
                      title="No queue matches"
                      message={
                        searchTerm
                          ? "No open tickets matched the current search query."
                          : "There are no active tickets in the live queue right now."
                      }
                    />
                  )}
                </div>
              </div>

              <div className="space-y-6">
                <div className="ops-card rounded-[26px] p-5 sm:p-6">
                  <div className="flex items-start justify-between gap-4">
                    <div>
                      <div className="mono-data text-[10px] uppercase tracking-[0.28em] text-amber-300">
                        Case Inspector
                      </div>
                      <h2 className="mt-2 text-2xl font-semibold text-zinc-50">
                        {selectedTicket?.ticketId || "No active ticket"}
                      </h2>
                      <p className="mt-2 text-sm leading-6 text-zinc-300">
                        {selectedTicket?.title || "No ticket is currently selected."}
                      </p>
                    </div>
                    {selectedTicket ? (
                      <Link
                        href={`/tickets/${selectedTicket.ticketId}`}
                        className="inline-flex items-center gap-2 rounded-full border border-zinc-700/60 bg-zinc-900/60 px-3 py-2 text-xs font-medium text-zinc-200 transition hover:border-amber-400/30"
                      >
                        <ArrowUpRight className="h-3.5 w-3.5" />
                        Open ticket
                      </Link>
                    ) : null}
                  </div>

                  <div className="mt-5 grid gap-3 sm:grid-cols-2">
                    <div className="rounded-2xl border border-zinc-800/60 bg-black/20 p-4">
                      <div className="mono-data text-[10px] uppercase tracking-[0.22em] text-zinc-500">Decision Score</div>
                      <div className="mono-data mt-3 text-3xl font-bold text-zinc-50">
                        {selectedTicket ? selectedTicket.score.toFixed(0) : "--"}
                      </div>
                    </div>
                    <div className="rounded-2xl border border-zinc-800/60 bg-black/20 p-4">
                      <div className="mono-data text-[10px] uppercase tracking-[0.22em] text-zinc-500">Linked Incident</div>
                      <div className="mt-3 text-sm font-medium text-zinc-100">
                        {linkedIncident?.title || "Standalone case"}
                      </div>
<div className="mono-data mt-1 text-[11px] text-zinc-500">{linkedIncident?.id || "No cluster"}</div>
                  </div>
                </div>

                <div className="mt-5 grid gap-3 text-sm text-zinc-300">
                    <div className="flex items-center justify-between rounded-2xl border border-zinc-800/60 bg-black/20 px-4 py-3">
                      <div className="flex items-center gap-3">
                        <Clock3 className="h-4 w-4 text-zinc-500" />
                        <span>Opened</span>
                      </div>
                      <span className="mono-data text-zinc-400">{formatDate(selectedTicket?.createdAt)}</span>
                    </div>
                    <div className="flex items-center justify-between rounded-2xl border border-zinc-800/60 bg-black/20 px-4 py-3">
                      <div className="flex items-center gap-3">
                        <Users className="h-4 w-4 text-zinc-500" />
                        <span>Owner</span>
                      </div>
                      <span className="mono-data text-zinc-400">{selectedTicket?.assignee || "Unassigned"}</span>
                    </div>
                    <div className="flex items-center justify-between rounded-2xl border border-zinc-800/60 bg-black/20 px-4 py-3">
                      <div className="flex items-center gap-3">
                        <AlertTriangle className="h-4 w-4 text-zinc-500" />
                        <span>Request Type</span>
                      </div>
                      <span className="mono-data text-zinc-400">{selectedTicket?.category || "Unknown"}</span>
                    </div>
                  </div>
                </div>

                <div className="ops-card rounded-[26px] p-5 sm:p-6">
                  <div className="flex items-center justify-between">
                    <div className="mono-data text-[10px] uppercase tracking-[0.28em] text-zinc-500">
                      Active Clusters
                    </div>
                    <span className="mono-data text-[11px] text-cyan-300">{incidentCards.length}</span>
                  </div>
                  <div className="mt-4 space-y-3">
                    {incidentCards.length ? incidentCards.map((incident) => (
                      <Link
                        key={incident.id}
                        href={`/incidents/${incident.id}`}
                        className="block rounded-2xl border border-zinc-800/60 bg-black/20 px-4 py-4 transition hover:border-cyan-400/30"
                      >
                        <div className="flex items-center justify-between gap-3">
                          <div>
                            <div className="text-sm font-semibold text-zinc-100">{incident.title}</div>
                            <div className="mono-data mt-1 text-[11px] text-zinc-500">{incident.id}</div>
                          </div>
                          <div className="mono-data text-sm text-cyan-200">
                            {Math.round(incident.confidence * 100)}%
                          </div>
                        </div>
                        <div className="mt-3 flex flex-wrap gap-3 text-xs text-zinc-500">
                          <span>{incident.ticketCount} linked tickets</span>
                          <span>{incident.rootCause}</span>
                          <span>Impact {incident.impact}</span>
                        </div>
                      </Link>
                    )) : (
                      <SectionEmptyState
                        title="No incident clusters"
                        message="No live incident clusters are currently linked to the queue."
                      />
                    )}
                  </div>
                </div>
              </div>
            </section>

            <section className="mt-6 grid gap-6 xl:grid-cols-[1fr,1fr]">
              <div className="ops-card rounded-[24px] p-5 sm:p-6">
                <div className="mono-data text-[10px] uppercase tracking-[0.28em] text-zinc-500">
                  Top Request Types
                </div>
                <div className="mt-5 space-y-4">
                  {requestTypeSlices.length ? requestTypeSlices.map((slice) => {
                    const width = `${Math.max((slice.value / (requestTypeSlices[0]?.value || 1)) * 100, 9)}%`;
                    return (
                      <div key={slice.label}>
                        <div className="mb-2 flex items-center justify-between text-sm">
                          <span className="text-zinc-300">{slice.label}</span>
                          <span className="mono-data text-zinc-500">{slice.value}</span>
                        </div>
                        <div className="h-2.5 rounded-full bg-zinc-900/80">
                          <div
                            className="h-2.5 rounded-full"
                            style={{
                              width,
                              background: `linear-gradient(90deg, ${slice.color}, rgba(255,255,255,0.16))`,
                            }}
                          />
                        </div>
                      </div>
                    );
                  }) : (
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
                  {assigneeSlices.length ? assigneeSlices.map((slice) => {
                    const width = `${Math.max((slice.value / (assigneeSlices[0]?.value || 1)) * 100, 10)}%`;
                    return (
                      <div key={slice.label}>
                        <div className="mb-2 flex items-center justify-between text-sm">
                          <span className="text-zinc-300">{slice.label}</span>
                          <span className="mono-data text-zinc-500">{slice.value}</span>
                        </div>
                        <div className="h-2.5 rounded-full bg-zinc-900/80">
                          <div
                            className="h-2.5 rounded-full bg-gradient-to-r from-cyan-400 to-amber-400"
                            style={{ width }}
                          />
                        </div>
                      </div>
                    );
                  }) : (
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
