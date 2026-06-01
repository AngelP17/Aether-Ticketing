"use client";

import Link from "next/link";
import { AlertTriangle, ArrowUpRight, Clock3, Users } from "lucide-react";
import type { IncidentCard, QueueTicket } from "./types";

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

export function DecisionDetailPanel({
  selectedTicket,
  linkedIncident,
}: {
  selectedTicket: QueueTicket | undefined;
  linkedIncident: IncidentCard | undefined;
}) {
  return (
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
  );
}
