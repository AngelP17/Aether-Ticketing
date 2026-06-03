"use client";

import Link from "next/link";
import { useState, type DragEvent } from "react";
import { ChevronRight, GripVertical } from "lucide-react";

import type { Ticket } from "@/types";

import { priorityTone } from "./palette";
import { StatusPill } from "./status-pill";

const MOVE_OPTIONS = [
  { value: "Open", label: "Open" },
  { value: "In Progress", label: "In Progress" },
  { value: "Waiting for Info", label: "Waiting" },
  { value: "Resolved", label: "Resolved" },
  { value: "Closed", label: "Closed" },
] as const;

export function BoardCard({
  ticket,
  isDragging,
  isMoving,
  onDragStart,
  onDragEnd,
  onMove,
}: {
  ticket: Ticket;
  isDragging: boolean;
  isMoving: boolean;
  onDragStart: (event: DragEvent<HTMLDivElement>, ticketId: string) => void;
  onDragEnd: () => void;
  onMove: (ticketId: string, status: string) => void;
}) {
  const tone = priorityTone(ticket.priority_raw);
  const [moveOpen, setMoveOpen] = useState(false);

  const handleSelect = (value: string) => {
    setMoveOpen(false);
    if (value && value !== ticket.status) {
      onMove(ticket.ticket_id, value);
    }
  };

  return (
    <div
      draggable
      onDragStart={(event) => onDragStart(event, ticket.ticket_id)}
      onDragEnd={onDragEnd}
      className={`group relative rounded-2xl border border-zinc-800 bg-zinc-950/60 p-4 transition ${
        isDragging
          ? "cursor-grabbing border-amber-400/40 opacity-60 shadow-[0_18px_40px_rgba(0,0,0,0.35)]"
          : isMoving
            ? "cursor-progress border-amber-400/30 opacity-80"
            : "cursor-grab hover:border-amber-500/25 hover:bg-zinc-900/80"
      }`}
      aria-grabbed={isDragging}
      aria-busy={isMoving}
    >
      <div className="flex items-center justify-between gap-3">
        <div className="flex items-center gap-2">
          <GripVertical
            className="h-3.5 w-3.5 shrink-0 text-zinc-600 transition group-hover:text-amber-300/70"
            aria-hidden="true"
          />
          <div className="mono-data text-[11px] uppercase tracking-[0.24em] text-zinc-500">
            {ticket.ticket_id}
          </div>
        </div>
        <span
          className={`rounded-full border px-2.5 py-1 text-[11px] font-medium ${tone.border} ${tone.bg} ${tone.text}`}
        >
          {ticket.priority_raw}
        </span>
      </div>

      <Link
        href={`/tickets/${ticket.ticket_id}`}
        className="mt-3 block text-sm leading-6 text-zinc-100 transition hover:text-amber-200"
        onClick={(event) => {
          if (isDragging || isMoving) {
            event.preventDefault();
          }
        }}
        draggable={false}
      >
        {ticket.title}
      </Link>

      <div className="mt-4 flex flex-wrap items-center gap-2">
        <StatusPill status={ticket.status} />
        <span className="rounded-full border border-zinc-800 bg-zinc-900/70 px-2.5 py-1 text-[11px] text-zinc-400">
          {ticket.assignee || "Unassigned"}
        </span>
        <span className="mono-data rounded-full border border-zinc-800 bg-zinc-900/70 px-2.5 py-1 text-[11px] text-zinc-500">
          {ticket.days_open}d open
        </span>
      </div>

      <div className="mt-3 flex items-center justify-between gap-2 border-t border-zinc-800/60 pt-3">
        {moveOpen ? (
          <select
            autoFocus
            defaultValue=""
            onBlur={(event) => {
              handleSelect(event.target.value);
            }}
            onChange={(event) => handleSelect(event.target.value)}
            disabled={isMoving}
            className="w-full rounded-lg border border-amber-400/30 bg-black/40 px-2 py-1.5 text-[11px] text-zinc-100 outline-none focus:border-amber-400/50"
            aria-label={`Move ${ticket.ticket_id} to status`}
          >
            <option value="" disabled>
              Move to…
            </option>
            {MOVE_OPTIONS.map((option) => (
              <option key={option.value} value={option.value}>
                {option.label}
              </option>
            ))}
          </select>
        ) : (
          <>
            <span className="text-[10px] uppercase tracking-[0.24em] text-zinc-600">
              {isMoving ? "Moving…" : "Move"}
            </span>
            <button
              type="button"
              onClick={() => setMoveOpen(true)}
              disabled={isMoving}
              className="inline-flex items-center gap-1 rounded-lg border border-zinc-800 bg-black/30 px-2.5 py-1 text-[11px] font-medium text-amber-300 transition hover:border-amber-400/30 hover:text-amber-200 disabled:cursor-not-allowed disabled:opacity-60"
              aria-label={`Move ${ticket.ticket_id}`}
            >
              Move
              <ChevronRight className="h-3 w-3" aria-hidden="true" />
            </button>
          </>
        )}
      </div>
    </div>
  );
}
