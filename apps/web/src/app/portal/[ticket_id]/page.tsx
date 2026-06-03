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
        {!data && !err && <div>Loading...</div>}
        {data && (
          <div className="space-y-2 text-sm">
            <div><span className="text-zinc-500">Ticket:</span> <span className="font-mono">{data.ticket_id}</span></div>
            <div><span className="text-zinc-500">Title:</span> {data.title}</div>
            <div><span className="text-zinc-500">Status:</span> {data.status} • Priority {data.priority}</div>
            <div><span className="text-zinc-500">Opened:</span> {data.created_at}</div>
            {data.root_cause_hypothesis && <div><span className="text-zinc-500">Likely cause:</span> {data.root_cause_hypothesis}</div>}
            <div className="pt-2 text-xs text-zinc-500">For full details and actions, log in as agent.</div>
          </div>
        )}
      </div>
    </OpsShell>
  );
}
