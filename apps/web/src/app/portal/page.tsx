"use client";

import { useState } from "react";
import Link from "next/link";

import { OpsShell } from "@/components/ops-shell";
import { readAccessToken } from "@/lib/auth";

export default function PortalPage() {
  const [form, setForm] = useState({ title: "", description: "", requester: "", custom_fields: { site: "", asset: "" } as any });
  const [result, setResult] = useState<any>(null);
  const [loading, setLoading] = useState(false);

  const submit = async (e: React.FormEvent) => {
    e.preventDefault();
    setLoading(true);
    try {
      const token = readAccessToken();
      const res = await fetch("/api/portal/tickets", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          ...(token ? { Authorization: `Bearer ${token}` } : {}),
        },
        body: JSON.stringify(form),
      });
      const data = await res.json();
      setResult(data);
    } catch (err: any) {
      setResult({ error: err.message || "Submit failed" });
    } finally {
      setLoading(false);
    }
  };

  return (
    <OpsShell title="Customer Portal" subtitle="Submit or check ticket status">
      <div className="mx-auto max-w-xl ops-card rounded-[22px] p-6">
        <h2 className="text-xl font-semibold">Submit a request</h2>
        <form onSubmit={submit} className="mt-4 space-y-3">
          <input className="w-full rounded-[12px] border border-zinc-800 bg-black/20 p-3 text-sm mono-data" placeholder="Title" value={form.title} onChange={e=>setForm({...form,title:e.target.value})} required />
          <textarea className="w-full rounded-[12px] border border-zinc-800 bg-black/20 p-3 text-sm" placeholder="Description" value={form.description} onChange={e=>setForm({...form,description:e.target.value})} rows={4} required />
          <input className="w-full rounded-[12px] border border-zinc-800 bg-black/20 p-3 text-sm mono-data" placeholder="Your email or name" value={form.requester} onChange={e=>setForm({...form,requester:e.target.value})} />
          <input className="w-full rounded-[12px] border border-zinc-800 bg-black/20 p-3 text-sm mono-data" placeholder="Site / location (custom)" value={form.custom_fields?.site || ''} onChange={e=>setForm({...form, custom_fields: {...form.custom_fields, site: e.target.value}})} />
          <button disabled={loading} className="w-full rounded-[12px] bg-amber-500 px-4 py-2 text-sm font-medium text-black disabled:opacity-50 active:scale-[0.98] transition">{loading ? "Sending..." : "Submit request"}</button>
        </form>

        {result && (
          <div className="mt-4 rounded border p-3 text-sm">
            {result.ticket_id ? (
              <div>
                Received. Your ticket: <span className="font-mono">{result.ticket_id}</span>.{" "}
                <Link href={`/portal/${result.ticket_id}`} className="text-amber-400 underline">Check status</Link>
              </div>
            ) : (
              <pre className="whitespace-pre-wrap">{JSON.stringify(result, null, 2)}</pre>
            )}
          </div>
        )}

        <p className="mt-4 text-xs text-zinc-500">Agent view in Command Center / Board. Limited public access for status.</p>
      </div>
    </OpsShell>
  );
}
