"use client";

import { useEffect, useState } from "react";
import { useParams } from "next/navigation";

import { OpsShell } from "@/components/ops-shell";

export default function PortalTicketPage() {
  const params = useParams<{ ticket_id: string }>();
  const id = params?.ticket_id || "";
  const [data, setData] = useState<any>(null);
  const [err, setErr] = useState<string | null>(null);

  useEffect(() => {
    if (!id) return;
    fetch(`/api/portal/tickets/${id}`)
      .then(r => r.ok ? r.json() : Promise.reject(r.status))
      .then(setData)
      .catch(e => setErr(String(e)));
  }, [id]);

  return (
    <OpsShell title={`Portal • ${id}`} subtitle="Public status (limited)">
      <div className="mx-auto max-w-xl ops-card rounded-[22px] p-6">
        {err && <div className="text-rose-400">Error: {err}</div>}
        {!data && !err && <div className="text-zinc-400">Loading status...</div>}
        {data && (
          <div className="space-y-3 text-sm">
            <div className="flex items-center justify-between">
              <span className="text-zinc-400">Ticket ID</span>
              <span className="font-mono text-amber-100">{data.ticket_id}</span>
            </div>
            <div><span className="text-zinc-400">Title</span><div className="mt-0.5 text-zinc-100">{data.title}</div></div>
            <div className="flex gap-4">
              <div><span className="text-zinc-400">Status</span> <span className="text-emerald-200">{data.status}</span></div>
              <div><span className="text-zinc-400">Priority</span> {data.priority}</div>
            </div>
            <div><span className="text-zinc-400">Opened</span> {data.created_at}</div>
            {data.root_cause_hypothesis && <div className="rounded border-l-2 border-amber-500 pl-2 text-amber-100">{data.root_cause_hypothesis}</div>}
            {data.custom_fields && <div className="text-xs text-zinc-400">Custom: {JSON.stringify(data.custom_fields)}</div>}
            <div className="pt-2 text-[11px] text-zinc-500">For full details, actions, and intelligence (graph, bands, recs), log in to the OpsCenter.</div>
          </div>
        )}
      </div>
    </OpsShell>
  );
}
