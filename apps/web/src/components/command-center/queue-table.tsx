"use client";

import { ChevronRight } from "lucide-react";
import { SectionEmptyState } from "./section-empty-state";
import { priorityPalette, statusPalette } from "./palettes";
import type { QueueTicket } from "./types";

export function QueueTable({
  tickets,
  selectedId,
  onSelect,
  searchTerm,
}: {
  tickets: QueueTicket[];
  selectedId: string | null;
  onSelect: (id: string) => void;
  searchTerm: string;
}) {
  return (
    <div className="ops-card rounded-[26px] p-5 sm:p-6">
      <div className="flex flex-col gap-3 border-b border-zinc-800/50 pb-4 sm:flex-row sm:items-end sm:justify-between">
        <div>
          <h2 className="text-2xl font-semibold text-zinc-50">Ranked Queue</h2>
          <p className="mt-1 text-sm text-zinc-400">
            Search, inspect, and route the highest-value live tickets first.
          </p>
        </div>
        <span className="mono-data text-[11px] uppercase tracking-[0.22em] text-amber-300">
          {tickets.length} visible
        </span>
      </div>

      <div className="mt-4 space-y-3">
        {tickets.length ? tickets.map((ticket, index) => (
          <button
            key={ticket.ticketId}
            type="button"
            onClick={() => onSelect(ticket.ticketId)}
            className={`block w-full rounded-[20px] border px-4 py-4 text-left transition ${
              selectedId === ticket.ticketId
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
  );
}
