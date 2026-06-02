"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import {
  useCallback,
  useEffect,
  useMemo,
  useRef,
  useState,
  type DragEvent,
} from "react";
import {
  AlertTriangle,
  Columns3,
  Plus,
  RefreshCw,
  ShieldAlert,
  Sparkles,
} from "lucide-react";

import { OpsShell } from "@/components/ops-shell";
import { SectionEmptyState } from "@/components/command-center/section-empty-state";
import { useToast } from "@/components/notifications";
import { ticketsApi } from "@/lib/api";
import { clearStoredSession } from "@/lib/auth";
import type { Ticket } from "@/types";

import { BoardCard } from "@/components/board/board-card";
import { BoardColumn, type BoardColumnDef } from "@/components/board/board-column";
import { PRIORITIES } from "@/components/board/palette";

const SLA_RISK_HOURS = 24;
const SLA_RISK_WINDOW_MS = SLA_RISK_HOURS * 60 * 60 * 1000;

type FeedStatus = "loading" | "ready" | "error";

const COLUMNS: BoardColumnDef[] = [
  {
    key: "OPEN",
    label: "Open",
    description: "Fresh work and waiting states that still need routing or operator follow-up.",
    accent: "#f59e0b",
    pillTone: "border-amber-500/20 bg-amber-500/8 text-amber-200",
  },
  {
    key: "IN_PROGRESS",
    label: "In Progress",
    description: "Assigned cases with active operator work, execution, or diagnosis underway.",
    accent: "#22b8cf",
    pillTone: "border-cyan-500/20 bg-cyan-500/8 text-cyan-200",
  },
  {
    key: "RESOLVED",
    label: "Resolved",
    description: "Closed or resolved work retained for throughput and historical context.",
    accent: "#22c55e",
    pillTone: "border-emerald-500/20 bg-emerald-500/8 text-emerald-200",
  },
];

const COLUMN_STATUSES: Record<string, string[]> = {
  OPEN: ["Open", "Waiting for Info", "Waiting Info"],
  IN_PROGRESS: ["In Progress"],
  RESOLVED: ["Resolved", "Closed"],
};

const REPRESENTATIVE_STATUS: Record<string, string> = {
  OPEN: "Open",
  IN_PROGRESS: "In Progress",
  RESOLVED: "Resolved",
};

function statusMatchesColumn(status: string, columnKey: string) {
  return COLUMN_STATUSES[columnKey]?.includes(status) ?? false;
}

export default function BoardPage() {
  const router = useRouter();
  const toast = useToast();
  const toastRef = useRef(toast);
  const syncStartRef = useRef(Date.now());
  const mountedRef = useRef(true);

  const [tickets, setTickets] = useState<Ticket[]>([]);
  const [status, setStatus] = useState<FeedStatus>("loading");
  const [errorMessage, setErrorMessage] = useState<string | null>(null);
  const [lastSyncSeconds, setLastSyncSeconds] = useState(0);
  const [isSigningOut, setIsSigningOut] = useState(false);

  const [search, setSearch] = useState("");
  const [activePriorities, setActivePriorities] = useState<Set<string>>(new Set());
  const [slaRiskOnly, setSlaRiskOnly] = useState(false);

  const [dragTicketId, setDragTicketId] = useState<string | null>(null);
  const [dragOverColumn, setDragOverColumn] = useState<string | null>(null);
  const [movingTicketId, setMovingTicketId] = useState<string | null>(null);

  useEffect(() => {
    toastRef.current = toast;
  }, [toast]);

  const loadTickets = useCallback(
    async ({ notifyOnError = false }: { notifyOnError?: boolean } = {}) => {
      if (!mountedRef.current) {
        return;
      }
      setStatus("loading");
      setErrorMessage(null);

      try {
        const response = await ticketsApi.list({ limit: 200 });
        if (!mountedRef.current) {
          return;
        }
        const next = (response.data ?? []) as Ticket[];
        syncStartRef.current = Date.now();
        setTickets(next);
        setStatus("ready");
        setLastSyncSeconds(0);
      } catch (error) {
        if (!mountedRef.current) {
          return;
        }
        const message =
          error instanceof Error ? error.message : "The workflow board could not load the live API.";
        setStatus("error");
        setErrorMessage(message);
        setTickets([]);
        if (notifyOnError) {
          toastRef.current.error("Board unavailable", message);
        }
      }
    },
    [],
  );

  useEffect(() => {
    mountedRef.current = true;
    void loadTickets({ notifyOnError: true });

    const timer = window.setInterval(() => {
      setLastSyncSeconds(Math.floor((Date.now() - syncStartRef.current) / 1000));
    }, 1000);

    return () => {
      mountedRef.current = false;
      window.clearInterval(timer);
    };
  }, [loadTickets]);

  const searchTerm = search.trim().toLowerCase();
  const slaRiskCount = useMemo(() => {
    const cutoff = Date.now() - SLA_RISK_WINDOW_MS;
    return tickets.reduce(
      (count, ticket) =>
        (ticket.priority_raw === "Critical" || ticket.priority_raw === "High") &&
        ticket.created_at &&
        new Date(ticket.created_at).getTime() < cutoff
          ? count + 1
          : count,
      0,
    );
  }, [tickets]);

  const filteredTickets = useMemo(() => {
    if (status === "error") {
      return [];
    }
    const slaCutoff = Date.now() - SLA_RISK_WINDOW_MS;
    return tickets.filter((ticket) => {
      if (activePriorities.size > 0 && !activePriorities.has(ticket.priority_raw)) {
        return false;
      }
      if (slaRiskOnly) {
        const isPriority = ticket.priority_raw === "Critical" || ticket.priority_raw === "High";
        const createdMs = ticket.created_at ? new Date(ticket.created_at).getTime() : NaN;
        if (!isPriority || Number.isNaN(createdMs) || createdMs >= slaCutoff) {
          return false;
        }
      }
      if (searchTerm) {
        const haystack = [
          ticket.ticket_id,
          ticket.title,
          ticket.assignee || "",
        ]
          .join(" ")
          .toLowerCase();
        if (!haystack.includes(searchTerm)) {
          return false;
        }
      }
      return true;
    });
  }, [tickets, activePriorities, slaRiskOnly, searchTerm, status]);

  const grouped = useMemo<Record<string, Ticket[]>>(() => {
    const empty = COLUMNS.reduce<Record<string, Ticket[]>>((acc, column) => {
      acc[column.key] = [];
      return acc;
    }, {});

    filteredTickets.forEach((ticket) => {
      for (const column of COLUMNS) {
        if (statusMatchesColumn(ticket.status, column.key)) {
          empty[column.key].push(ticket);
          return;
        }
      }
    });

    return empty;
  }, [filteredTickets]);

  const totalMatching = filteredTickets.length;

  const togglePriority = useCallback((priority: string) => {
    setActivePriorities((current) => {
      const next = new Set(current);
      if (next.has(priority)) {
        next.delete(priority);
      } else {
        next.add(priority);
      }
      return next;
    });
  }, []);

  const resetFilters = useCallback(() => {
    setSearch("");
    setActivePriorities(new Set());
    setSlaRiskOnly(false);
  }, []);

  const moveTicket = useCallback(
    async (ticketId: string, newStatus: string) => {
      const current = tickets.find((t) => t.ticket_id === ticketId);
      if (!current || current.status === newStatus) {
        return;
      }

      const previousStatus = current.status;
      setMovingTicketId(ticketId);
      setTickets((prev) =>
        prev.map((t) => (t.ticket_id === ticketId ? { ...t, status: newStatus } : t)),
      );

      try {
        await ticketsApi.move(ticketId, { status: newStatus });
        toast.success("Ticket moved", `${ticketId} → ${newStatus}`);
      } catch (error) {
        setTickets((prev) =>
          prev.map((t) =>
            t.ticket_id === ticketId ? { ...t, status: previousStatus } : t,
          ),
        );
        const message = error instanceof Error ? error.message : "Could not move the ticket.";
        toast.error("Move failed", message);
      } finally {
        setMovingTicketId((currentId) => (currentId === ticketId ? null : currentId));
      }
    },
    [tickets, toast],
  );

  const handleDragStart = useCallback((event: DragEvent<HTMLDivElement>, ticketId: string) => {
    event.dataTransfer.effectAllowed = "move";
    event.dataTransfer.setData("text/plain", ticketId);
    setDragTicketId(ticketId);
  }, []);

  const handleDragEnd = useCallback(() => {
    setDragTicketId(null);
    setDragOverColumn(null);
  }, []);

  const handleDragOver = useCallback((event: DragEvent<HTMLDivElement>, columnKey: string) => {
    event.preventDefault();
    event.dataTransfer.dropEffect = "move";
    if (dragOverColumn !== columnKey) {
      setDragOverColumn(columnKey);
    }
  }, [dragOverColumn]);

  const handleDragLeave = useCallback((columnKey: string) => {
    setDragOverColumn((current) => (current === columnKey ? null : current));
  }, []);

  const handleDrop = useCallback(
    (event: DragEvent<HTMLDivElement>, columnKey: string) => {
      event.preventDefault();
      const data = event.dataTransfer.getData("text/plain");
      const ticketId = data || dragTicketId;
      const newStatus = REPRESENTATIVE_STATUS[columnKey];
      setDragTicketId(null);
      setDragOverColumn(null);
      if (ticketId && newStatus) {
        void moveTicket(ticketId, newStatus);
      }
    },
    [dragTicketId, moveTicket],
  );

  const handleLogout = useCallback(async () => {
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
  }, [isSigningOut, router, toast]);

  const statusPill =
    status === "ready"
      ? { kind: "ready" as const, label: "Live" }
      : status === "loading"
        ? { kind: "loading" as const, label: "Loading…" }
        : { kind: "error" as const, label: "Disconnected" };

  const filterCount =
    (searchTerm ? 1 : 0) + activePriorities.size + (slaRiskOnly ? 1 : 0);

  return (
    <OpsShell
      eyebrow="Aether OpsCenter"
      title="Workflow Tracking"
      subtitle="Live ticket board with search, priority filters, SLA focus, desktop drag/drop, and touch-safe move controls."
      statusPill={statusPill}
      lastSyncSeconds={lastSyncSeconds}
      search={{ value: search, onChange: setSearch, placeholder: "Search title, id, or owner" }}
      headerActions={
        <>
          <Link
            href="/tickets/new"
            className="inline-flex items-center gap-2 rounded-xl border border-amber-400/20 bg-amber-500 px-3 py-2 text-sm font-semibold text-black transition hover:bg-amber-400 active:scale-[0.98]"
          >
            <Plus className="h-4 w-4" aria-hidden="true" />
            New ticket
          </Link>
          <button
            type="button"
            onClick={() => void loadTickets({ notifyOnError: true })}
            disabled={status === "loading"}
            className="inline-flex h-9 w-9 items-center justify-center rounded-xl border border-zinc-800 bg-black/20 text-zinc-400 transition hover:border-amber-400/30 hover:text-amber-200 disabled:cursor-not-allowed disabled:opacity-60"
            aria-label="Refresh board"
            title="Refresh board"
          >
            <RefreshCw
              className={`h-4 w-4 ${status === "loading" ? "animate-spin" : ""}`}
              aria-hidden="true"
            />
          </button>
        </>
      }
      onLogout={handleLogout}
      isSigningOut={isSigningOut}
      showNotificationBell
    >
      <div className="mx-auto w-full max-w-[1480px] space-y-5">
        <div className="ops-glass rounded-[28px] px-4 py-4 sm:px-6 sm:py-5">
          <div className="flex flex-col gap-3 xl:flex-row xl:items-center xl:justify-between">
            <div className="flex flex-wrap items-center gap-2 text-[11px] text-zinc-500">
              <span className="mono-data rounded-full border border-zinc-800/70 bg-black/20 px-3 py-1.5 uppercase tracking-[0.24em]">
                {totalMatching} visible
              </span>
              {filterCount > 0 ? (
                <button
                  type="button"
                  onClick={resetFilters}
                  className="mono-data inline-flex items-center gap-1.5 rounded-full border border-amber-400/20 bg-amber-500/10 px-3 py-1.5 text-amber-200 transition hover:bg-amber-500/15"
                >
                  Reset filters
                </button>
              ) : null}
            </div>
          </div>

          <div className="mt-4 flex flex-wrap items-center gap-2">
            <span className="mono-data text-[10px] uppercase tracking-[0.24em] text-zinc-500">
              Priority
            </span>
            {PRIORITIES.map((priority) => {
              const active = activePriorities.has(priority);
              return (
                <button
                  key={priority}
                  type="button"
                  onClick={() => togglePriority(priority)}
                  className={`inline-flex items-center gap-1.5 rounded-full border px-3 py-1.5 text-[11px] font-medium transition ${
                    active
                      ? "border-amber-400/40 bg-amber-500/10 text-amber-100"
                      : "border-zinc-800/70 bg-black/20 text-zinc-400 hover:border-zinc-700"
                  }`}
                  aria-pressed={active}
                >
                  <span
                    className={`h-1.5 w-1.5 rounded-full ${
                      priority === "Critical"
                        ? "bg-rose-400"
                        : priority === "High"
                          ? "bg-orange-400"
                          : priority === "Medium"
                            ? "bg-amber-400"
                            : "bg-zinc-500"
                    }`}
                    aria-hidden="true"
                  />
                  {priority}
                </button>
              );
            })}
            <span className="mx-1 hidden h-4 w-px bg-zinc-800 sm:inline-block" aria-hidden="true" />
            <button
              type="button"
              onClick={() => setSlaRiskOnly((current) => !current)}
              className={`inline-flex items-center gap-1.5 rounded-full border px-3 py-1.5 text-[11px] font-medium transition ${
                slaRiskOnly
                  ? "border-rose-400/40 bg-rose-500/10 text-rose-100"
                  : "border-zinc-800/70 bg-black/20 text-zinc-400 hover:border-zinc-700"
              }`}
              aria-pressed={slaRiskOnly}
              title="Show only Critical/High tickets created more than 24h ago"
            >
              <ShieldAlert className="h-3.5 w-3.5" aria-hidden="true" />
              SLA risk ({slaRiskCount})
            </button>
            {filterCount === 0 ? (
              <span className="text-[11px] text-zinc-500">No filters active.</span>
            ) : null}
          </div>
        </div>

        {status === "loading" ? (
          <BoardSkeleton />
        ) : status === "error" ? (
          <BoardError message={errorMessage || "The board could not load."} onRetry={() => void loadTickets({ notifyOnError: true })} />
        ) : totalMatching === 0 ? (
          <BoardEmpty hasFilters={filterCount > 0} onReset={resetFilters} />
        ) : (
          <div className="flex snap-x snap-mandatory gap-4 overflow-x-auto pb-3 lg:grid lg:grid-cols-3 lg:gap-5 lg:overflow-visible lg:pb-0">
            {COLUMNS.map((column) => {
              const tickets = grouped[column.key];
              return (
                <BoardColumn
                  key={column.key}
                  column={column}
                  count={tickets.length}
                  isDropTarget={dragOverColumn === column.key}
                  onDragOver={handleDragOver}
                  onDragLeave={handleDragLeave}
                  onDrop={handleDrop}
                >
                  {tickets.length === 0 ? (
                    <div className="rounded-[1.15rem] border border-dashed border-zinc-800 bg-zinc-950/45 px-4 py-10 text-center text-sm text-zinc-600">
                      No tickets in this lane.
                    </div>
                  ) : (
                    tickets.map((ticket) => (
                      <BoardCard
                        key={ticket.ticket_id}
                        ticket={ticket}
                        isDragging={dragTicketId === ticket.ticket_id}
                        isMoving={movingTicketId === ticket.ticket_id}
                        onDragStart={handleDragStart}
                        onDragEnd={handleDragEnd}
                        onMove={moveTicket}
                      />
                    ))
                  )}
                </BoardColumn>
              );
            })}
          </div>
        )}
      </div>
    </OpsShell>
  );
}

function BoardSkeleton() {
  return (
    <div className="grid gap-4 lg:grid-cols-3 lg:gap-5">
      {COLUMNS.map((column) => (
        <div key={column.key} className="ops-card rounded-[1.5rem] p-4 sm:p-5">
          <div className="flex items-start justify-between gap-3 border-b border-zinc-800/70 pb-4">
            <div className="space-y-2">
              <div className="h-3 w-24 rounded-full bg-zinc-800/80" />
              <div className="h-3 w-40 rounded-full bg-zinc-900/80" />
            </div>
            <div className="h-6 w-16 rounded-full bg-zinc-900/80" />
          </div>
          <div className="mt-4 space-y-3">
            {Array.from({ length: 3 }).map((_, index) => (
              <div key={index} className="rounded-[1.15rem] border border-zinc-800/60 bg-zinc-950/60 p-4">
                <div className="h-3 w-20 rounded-full bg-zinc-800/80" />
                <div className="mt-3 h-3 w-full rounded-full bg-zinc-900/80" />
                <div className="mt-2 h-3 w-2/3 rounded-full bg-zinc-900/80" />
                <div className="mt-4 flex gap-2">
                  <div className="h-5 w-16 rounded-full bg-zinc-900/80" />
                  <div className="h-5 w-20 rounded-full bg-zinc-900/80" />
                </div>
              </div>
            ))}
          </div>
        </div>
      ))}
    </div>
  );
}

function BoardError({ message, onRetry }: { message: string; onRetry: () => void }) {
  return (
    <div className="ops-card rounded-[26px] border border-rose-500/25 p-6">
      <div className="flex flex-col gap-4 sm:flex-row sm:items-start sm:justify-between">
        <div className="flex gap-4">
          <div className="flex h-11 w-11 shrink-0 items-center justify-center rounded-2xl border border-rose-500/30 bg-rose-500/10 text-rose-200">
            <AlertTriangle className="h-5 w-5" aria-hidden="true" />
          </div>
          <div>
            <p className="mono-data text-[10px] uppercase tracking-[0.28em] text-rose-300">
              Workflow board offline
            </p>
            <h2 className="mt-2 text-xl font-semibold text-white">The live board could not load</h2>
            <p className="mt-2 max-w-2xl text-sm leading-6 text-zinc-400">{message}</p>
          </div>
        </div>
        <div className="flex flex-wrap gap-2">
          <button
            type="button"
            onClick={onRetry}
            className="inline-flex items-center gap-2 rounded-xl border border-amber-400/20 bg-amber-500/10 px-3 py-2 text-sm font-semibold text-amber-100 transition hover:bg-amber-500/15"
          >
            <RefreshCw className="h-4 w-4" aria-hidden="true" />
            Retry load
          </button>
          <Link
            href="/command-center"
            className="inline-flex items-center gap-2 rounded-xl border border-zinc-700 bg-zinc-900/70 px-3 py-2 text-sm font-medium text-zinc-100 transition hover:border-amber-500/30 hover:bg-amber-500/10"
          >
            <Columns3 className="h-4 w-4" aria-hidden="true" />
            Command Center
          </Link>
        </div>
      </div>
    </div>
  );
}

function BoardEmpty({ hasFilters, onReset }: { hasFilters: boolean; onReset: () => void }) {
  return (
    <div className="ops-card rounded-[26px] p-6">
      <SectionEmptyState
        title="No tickets visible"
        message={
          hasFilters
            ? "No tickets matched the current search, priority, or SLA-risk filters."
            : "The live ticket stream is currently empty. New tickets will appear here as they are created."
        }
      />
      {hasFilters ? (
        <div className="mt-5 flex flex-wrap justify-center gap-3">
          <button
            type="button"
            onClick={onReset}
            className="inline-flex items-center gap-2 rounded-xl border border-amber-400/20 bg-amber-500/10 px-3 py-2 text-sm font-semibold text-amber-100 transition hover:bg-amber-500/15"
          >
            <Sparkles className="h-4 w-4" aria-hidden="true" />
            Reset filters
          </button>
          <Link
            href="/command-center"
            className="inline-flex items-center gap-2 rounded-xl border border-zinc-700 bg-zinc-900/70 px-3 py-2 text-sm font-medium text-zinc-100 transition hover:border-amber-500/30 hover:bg-amber-500/10"
          >
            <Columns3 className="h-4 w-4" aria-hidden="true" />
            Open Command Center
          </Link>
        </div>
      ) : null}
    </div>
  );
}
