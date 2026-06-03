"use client";

import Link from "next/link";
import { SectionEmptyState } from "./section-empty-state";
import type { IncidentCard } from "./types";

export function IncidentList({ incidents }: { incidents: IncidentCard[] }) {
  return (
    <div className="ops-card rounded-[22px] p-5 sm:p-6">
      <div className="flex items-start justify-between gap-3">
        <div>
          <h2 className="text-xl font-semibold text-zinc-50">Incident clusters</h2>
          <p className="mt-1 text-sm text-zinc-400">Linked incidents from the live queue.</p>
        </div>
        <span className="mono-data rounded-full border border-zinc-800 bg-black/20 px-2.5 py-1 text-[11px] text-cyan-300">
          {incidents.length}
        </span>
      </div>
      <div className="mt-4 space-y-3">
        {incidents.length ? incidents.map((incident) => (
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
  );
}
