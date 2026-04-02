import Link from "next/link";
import { ArrowRight, Columns3, Radar, Ticket, Zap } from "lucide-react";

import { getServerApiUrl } from "@/lib/server-api";
import type { Ticket as TicketType } from "@/types";

export const dynamic = "force-dynamic";

type BoardColumn = {
  key: string;
  label: string;
  description: string;
  accent: string;
  tone: string;
};

type TicketsFeed =
  | {
      status: "ready";
      tickets: TicketType[];
    }
  | {
      status: "error";
      message: string;
    };

const columns: BoardColumn[] = [
  {
    key: "TO DO",
    label: "To Do",
    description: "Fresh work that still needs routing, triage, or better intake detail.",
    accent: "#71717a",
    tone: "border-zinc-700/60 bg-zinc-900/45 text-zinc-300",
  },
  {
    key: "IN PROGRESS",
    label: "In Progress",
    description: "Assigned cases with active operator work, execution, or diagnosis underway.",
    accent: "#f59e0b",
    tone: "border-amber-500/20 bg-amber-500/8 text-amber-200",
  },
  {
    key: "IN REVIEW",
    label: "In Review",
    description: "Waiting on customer confirmation, validation steps, or a final check before close.",
    accent: "#06b6d4",
    tone: "border-cyan-500/20 bg-cyan-500/8 text-cyan-200",
  },
  {
    key: "DONE",
    label: "Done",
    description: "Resolved and closed work retained for throughput and historical context.",
    accent: "#22c55e",
    tone: "border-emerald-500/20 bg-emerald-500/8 text-emerald-200",
  },
];

async function getTickets(): Promise<TicketsFeed> {
  try {
    const response = await fetch(getServerApiUrl("/api/tickets?limit=200"), {
      cache: "no-store",
    });
    if (!response.ok) {
      return {
        status: "error",
        message: `Ticket board API returned ${response.status} ${response.statusText || "without a status message"}.`,
      };
    }
    return {
      status: "ready",
      tickets: (await response.json()) as TicketType[],
    };
  } catch (error) {
    return {
      status: "error",
      message: error instanceof Error ? error.message : "Unable to reach the ticket board API.",
    };
  }
}

function statusToColumn(status: string) {
  switch (status) {
    case "In Progress":
      return "IN PROGRESS";
    case "Waiting for Info":
    case "Waiting Info":
      return "IN REVIEW";
    case "Resolved":
    case "Closed":
      return "DONE";
    default:
      return "TO DO";
  }
}

function priorityTone(priority: string) {
  switch (priority.toLowerCase()) {
    case "critical":
      return "border-rose-500/20 bg-rose-500/10 text-rose-200";
    case "high":
      return "border-orange-500/20 bg-orange-500/10 text-orange-200";
    case "medium":
      return "border-amber-500/20 bg-amber-500/10 text-amber-200";
    default:
      return "border-zinc-700/60 bg-zinc-800/70 text-zinc-200";
  }
}

export default async function BoardPage() {
  const feed = await getTickets();

  if (feed.status === "error") {
    return (
      <div className="ops-shell relative min-h-screen overflow-hidden text-white">
        <div className="ops-grid absolute inset-0 opacity-70" />
        <div className="absolute right-[-6rem] top-[-6rem] h-[24rem] w-[24rem] rounded-full bg-amber-500/10 blur-[120px]" />
        <div className="relative z-10 mx-auto flex min-h-screen max-w-[1680px] items-center px-4 py-5 sm:px-6 lg:px-8">
          <div className="ops-card w-full rounded-[2rem] border border-rose-500/20 bg-black/40 p-8 text-center">
            <div className="mono-data text-[11px] uppercase tracking-[0.32em] text-rose-300">Board unavailable</div>
            <h1 className="mt-3 text-3xl font-semibold tracking-tight text-white">The live board could not load</h1>
            <p className="mx-auto mt-4 max-w-2xl text-sm leading-7 text-zinc-400">{feed.message}</p>
            <div className="mt-6 flex flex-wrap justify-center gap-3">
              <Link
                href="/board"
                className="inline-flex items-center gap-2 rounded-2xl bg-rose-500 px-4 py-2.5 text-sm font-semibold text-white transition hover:bg-rose-400"
              >
                Retry board load
              </Link>
              <Link
                href="/command-center"
                className="inline-flex items-center gap-2 rounded-2xl border border-zinc-700 bg-zinc-900/70 px-4 py-2.5 text-sm font-medium text-zinc-100 transition hover:border-amber-500/30 hover:bg-amber-500/10"
              >
                Command Center
              </Link>
            </div>
          </div>
        </div>
      </div>
    );
  }

  const grouped = columns.reduce<Record<string, TicketType[]>>((accumulator, column) => {
    accumulator[column.key] = [];
    return accumulator;
  }, {});

  feed.tickets.forEach((ticket) => {
    grouped[statusToColumn(ticket.status)].push(ticket);
  });

  const openCount = feed.tickets.filter((ticket) => !["Resolved", "Closed"].includes(ticket.status)).length;
  const activeCount = grouped["IN PROGRESS"].length;
  const reviewCount = grouped["IN REVIEW"].length;
  const throughputCount = grouped["DONE"].length;

  return (
    <div className="ops-shell relative min-h-screen overflow-hidden text-white">
      <div className="ops-grid absolute inset-0 opacity-70" />
      <div className="absolute right-[-6rem] top-[-6rem] h-[24rem] w-[24rem] rounded-full bg-amber-500/10 blur-[120px]" />
      <div className="absolute bottom-[-8rem] left-[8%] h-[20rem] w-[20rem] rounded-full bg-cyan-500/10 blur-[120px]" />

      <div className="relative z-10 mx-auto max-w-[1680px] px-4 py-5 sm:px-6 lg:px-8">
        <div className="ops-glass rounded-[2rem] overflow-hidden">
          <div className="border-b border-zinc-800/70 bg-black/20 px-5 py-5 sm:px-8">
            <div className="flex flex-col gap-5 xl:flex-row xl:items-center xl:justify-between">
              <div className="max-w-4xl">
                <div className="mono-data text-[11px] uppercase tracking-[0.32em] text-amber-300">Workflow Tracking</div>
                <h1 className="mt-2 text-3xl font-semibold tracking-tight text-white sm:text-4xl">
                  Board view for actual operational flow
                </h1>
                <p className="mt-3 text-sm leading-7 text-zinc-400">
                  This restores the board-style visibility from the original system, but inside the same amber-accented
                  ops-center language as the new Aether cockpit. It should feel like one product now, not a polished
                  command center next to a leftover page.
                </p>
              </div>

              <div className="flex flex-wrap items-center gap-3">
                <Link
                  href="/command-center"
                  className="inline-flex items-center gap-2 rounded-2xl border border-zinc-700 bg-zinc-900/70 px-4 py-2.5 text-sm font-medium text-zinc-100 transition hover:border-amber-500/30 hover:bg-amber-500/10"
                >
                  <Radar size={16} />
                  Command Center
                </Link>
                <Link
                  href="/reports"
                  className="inline-flex items-center gap-2 rounded-2xl bg-amber-500 px-4 py-2.5 text-sm font-semibold text-black transition hover:bg-amber-400"
                >
                  <Zap size={16} />
                  Reports
                </Link>
              </div>
            </div>
          </div>

          <div className="grid gap-4 border-b border-zinc-800/70 px-5 py-5 sm:grid-cols-2 xl:grid-cols-4 sm:px-8">
            {[
              {
                label: "Open Queue",
                value: openCount,
                note: "Cases still requiring active handling",
                icon: Ticket,
                color: "#06b6d4",
              },
              {
                label: "In Progress",
                value: activeCount,
                note: "Cases in execution right now",
                icon: Columns3,
                color: "#f59e0b",
              },
              {
                label: "Awaiting Review",
                value: reviewCount,
                note: "Waiting on detail, customer input, or validation",
                icon: Radar,
                color: "#8b5cf6",
              },
              {
                label: "Throughput",
                value: throughputCount,
                note: "Resolved or closed work in the current board",
                icon: ArrowRight,
                color: "#22c55e",
              },
            ].map((card) => {
              const Icon = card.icon;
              return (
                <div key={card.label} className="ops-card rounded-[1.25rem] p-5">
                  <div className="flex items-center justify-between">
                    <div className="mono-data text-[11px] uppercase tracking-[0.28em] text-zinc-500">{card.label}</div>
                    <div className="flex h-10 w-10 items-center justify-center rounded-2xl border border-white/5 bg-black/20">
                      <Icon size={16} style={{ color: card.color }} />
                    </div>
                  </div>
                  <div className="mono-data mt-4 text-4xl font-bold tracking-tight text-white">{card.value}</div>
                  <div className="mt-3 text-xs leading-6 text-zinc-500">{card.note}</div>
                </div>
              );
            })}
          </div>

          {feed.tickets.length === 0 ? (
            <div className="border-b border-zinc-800/70 px-5 py-5 sm:px-8">
              <div className="rounded-[1.25rem] border border-dashed border-zinc-700 bg-zinc-950/50 px-5 py-6 text-sm leading-7 text-zinc-400">
                The API returned no tickets, so this board is genuinely empty right now.
              </div>
            </div>
          ) : null}

          <div className="px-5 py-5 sm:px-8">
            <div className="grid gap-5 xl:grid-cols-4">
              {columns.map((column) => (
                <section
                  key={column.key}
                  className="ops-card rounded-[1.5rem] p-4 sm:p-5"
                >
                  <div className="border-b border-zinc-800/70 pb-4">
                    <div className="flex items-start justify-between gap-4">
                      <div>
                        <div className="flex items-center gap-3">
                          <span className="h-2.5 w-2.5 rounded-full" style={{ backgroundColor: column.accent }} />
                          <h2 className="text-lg font-semibold text-white">{column.label}</h2>
                        </div>
                        <p className="mt-2 text-sm leading-6 text-zinc-500">{column.description}</p>
                      </div>
                      <div className={`mono-data rounded-full border px-3 py-1 text-[11px] uppercase tracking-[0.24em] ${column.tone}`}>
                        {grouped[column.key].length}
                      </div>
                    </div>
                  </div>

                  <div className="mt-4 space-y-3">
                    {grouped[column.key].length === 0 ? (
                      <div className="rounded-[1.15rem] border border-dashed border-zinc-800 bg-zinc-950/45 px-4 py-10 text-center text-sm text-zinc-600">
                        No tickets in this lane.
                      </div>
                    ) : (
                      grouped[column.key].map((ticket) => (
                        <Link
                          key={ticket.ticket_id}
                          href={`/tickets/${ticket.ticket_id}`}
                          className="block rounded-[1.15rem] border border-zinc-800 bg-zinc-950/60 p-4 transition hover:border-amber-500/20 hover:bg-zinc-900/80"
                        >
                          <div className="flex items-center justify-between gap-3">
                            <div className="mono-data text-[11px] uppercase tracking-[0.24em] text-zinc-500">
                              {ticket.ticket_id}
                            </div>
                            <span className={`rounded-full border px-2.5 py-1 text-[11px] font-medium ${priorityTone(ticket.priority_raw)}`}>
                              {ticket.priority_raw}
                            </span>
                          </div>

                          <p className="mt-3 text-sm leading-6 text-zinc-100">{ticket.title}</p>

                          <div className="mt-4 flex flex-wrap gap-2">
                            <span className="rounded-full border border-zinc-800 bg-zinc-900/70 px-2.5 py-1 text-[11px] text-zinc-400">
                              {ticket.assignee || "Unassigned"}
                            </span>
                            <span className="rounded-full border border-zinc-800 bg-zinc-900/70 px-2.5 py-1 text-[11px] text-zinc-400">
                              {ticket.status}
                            </span>
                            <span className="mono-data rounded-full border border-zinc-800 bg-zinc-900/70 px-2.5 py-1 text-[11px] text-zinc-500">
                              {ticket.days_open}d open
                            </span>
                          </div>
                        </Link>
                      ))
                    )}
                  </div>
                </section>
              ))}
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
