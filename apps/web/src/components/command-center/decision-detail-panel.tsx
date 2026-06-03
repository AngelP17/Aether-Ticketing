"use client";

import { useCallback, useEffect, useMemo, useState } from "react";
import Link from "next/link";
import {
  AlertTriangle,
  ArrowUpRight,
  Brain,
  Cpu,
  Clock3,
  Database,
  Hash,
  Network,
  RefreshCcw,
  Users,
} from "lucide-react";

import { actionsApi, decisionsApi, ticketsApi } from "@/lib/api";
import type { Decision, TicketDetailPayload } from "@/types";
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

function bandTone(band?: string | null) {
  if (band === "high_confidence_action") {
    return {
      box: "border-emerald-500/30 bg-emerald-500/5",
      label: "text-emerald-300",
      text: "text-emerald-50",
    };
  }
  if (band === "review_needed") {
    return {
      box: "border-rose-500/30 bg-rose-500/5",
      label: "text-rose-300",
      text: "text-rose-50",
    };
  }
  return {
    box: "border-amber-500/20 bg-amber-500/5",
    label: "text-amber-300",
    text: "text-amber-50",
  };
}

export function DecisionDetailPanel({
  selectedTicket,
  linkedIncident,
}: {
  selectedTicket: QueueTicket | undefined;
  linkedIncident: IncidentCard | undefined;
}) {
  const ticketId = selectedTicket?.ticketId;
  const [detail, setDetail] = useState<TicketDetailPayload | null>(null);
  const [recompute, setRecompute] = useState<{
    status: "idle" | "running" | "ok" | "error";
    message?: string;
  }>({ status: "idle" });
  const [pendingAction, setPendingAction] = useState<string | null>(null);

  useEffect(() => {
    if (!ticketId) {
      setDetail(null);
      return;
    }
    let cancelled = false;
    setDetail(null);
    ticketsApi
      .get(ticketId)
      .then((response) => {
        if (cancelled) {
          return;
        }
        setDetail(response.data as TicketDetailPayload);
      })
      .catch(() => {
        if (cancelled) {
          return;
        }
        setDetail(null);
      });
    return () => {
      cancelled = true;
    };
  }, [ticketId]);

  const decision = detail?.decision ?? null;
  const tone = useMemo(() => bandTone(decision?.decision_band), [decision?.decision_band]);

  const handleRecompute = useCallback(async () => {
    if (!ticketId) {
      return;
    }
    setRecompute({ status: "running" });
    try {
      const response = await decisionsApi.recompute(ticketId);
      const payload = response.data as { decision?: Decision } | undefined;
      if (payload?.decision) {
        setDetail((current) =>
          current ? { ...current, decision: payload.decision as Decision } : current,
        );
      }
      setRecompute({ status: "ok", message: "Decision recomputed" });
    } catch (error: unknown) {
      const message = error instanceof Error ? error.message : "Recompute failed";
      setRecompute({ status: "error", message });
    }
  }, [ticketId]);

  const handleAcceptTop = useCallback(
    async (rec: { id: number; action_type?: string }) => {
      if (!ticketId) {
        return;
      }
      setPendingAction(`accept:${rec.id}`);
      try {
        await actionsApi.apply(rec.id, {
          action_type: rec.action_type,
          confirm: true,
        });
        const refreshed = await ticketsApi.get(ticketId);
        setDetail(refreshed.data as TicketDetailPayload);
      } catch (error: unknown) {
        const message = error instanceof Error ? error.message : "Apply failed";
        setRecompute({ status: "error", message });
      } finally {
        setPendingAction(null);
      }
    },
    [ticketId],
  );

  return (
    <div className="ops-card max-h-[72vh] overflow-y-auto rounded-[22px] p-5 sm:p-6 lg:max-h-[760px]">
      <div className="flex items-start justify-between gap-4">
        <div>
          <h2 className="text-2xl font-semibold text-zinc-50">
            {selectedTicket?.ticketId || "No active ticket"}
          </h2>
          <p className="mt-2 text-sm leading-6 text-zinc-300">
            {selectedTicket?.title || "No ticket is currently selected."}
          </p>
        </div>
        {selectedTicket ? (
          <div className="flex flex-col items-end gap-2">
            <Link
              href={`/tickets/${selectedTicket.ticketId}`}
              className="inline-flex items-center gap-2 rounded-full border border-zinc-700/60 bg-zinc-900/60 px-3 py-2 text-xs font-medium text-zinc-200 transition hover:border-amber-400/30"
            >
              <ArrowUpRight className="h-3.5 w-3.5" />
              Open ticket
            </Link>
            <button
              type="button"
              onClick={handleRecompute}
              disabled={recompute.status === "running"}
              className="inline-flex items-center gap-2 rounded-full border border-amber-500/30 bg-amber-500/10 px-3 py-2 text-xs font-medium text-amber-200 transition hover:border-amber-400/60 disabled:cursor-not-allowed disabled:opacity-60"
            >
              <RefreshCcw
                className={`h-3.5 w-3.5 ${
                  recompute.status === "running" ? "animate-spin" : ""
                }`}
              />
              Recompute decision
            </button>
            {recompute.message ? (
              <span
                className={`mono-data text-[10px] uppercase tracking-[0.22em] ${
                  recompute.status === "error" ? "text-rose-300" : "text-emerald-300"
                }`}
              >
                {recompute.message}
              </span>
            ) : null}
          </div>
        ) : null}
      </div>

      <div className="mt-5 grid gap-3 sm:grid-cols-2">
        <div className="rounded-2xl border border-zinc-800/60 bg-black/20 p-4">
          <div className="mono-data text-3xl font-bold text-zinc-50">
            {selectedTicket ? selectedTicket.score.toFixed(0) : "--"}
          </div>
        </div>
        <div className="rounded-2xl border border-zinc-800/60 bg-black/20 p-4">
          <div className="text-sm font-medium text-zinc-100">
            {linkedIncident?.title || "Standalone case"}
          </div>
          <div className="mono-data mt-1 text-[11px] text-zinc-500">
            {linkedIncident?.id || "No cluster"}
          </div>
        </div>
      </div>

      <div className="mt-5 grid gap-3 text-sm text-zinc-300">
        <div className="flex items-center justify-between rounded-2xl border border-zinc-800/60 bg-black/20 px-4 py-3">
          <div className="flex items-center gap-3">
            <Clock3 className="h-4 w-4 text-zinc-500" />
            <span>Opened</span>
          </div>
          <span className="mono-data text-zinc-400">
            {formatDate(selectedTicket?.createdAt)}
          </span>
        </div>
        <div className="flex items-center justify-between rounded-2xl border border-zinc-800/60 bg-black/20 px-4 py-3">
          <div className="flex items-center gap-3">
            <Users className="h-4 w-4 text-zinc-500" />
            <span>Owner</span>
          </div>
          <span className="mono-data text-zinc-400">
            {selectedTicket?.assignee || "Unassigned"}
          </span>
        </div>
        <div className="flex items-center justify-between rounded-2xl border border-zinc-800/60 bg-black/20 px-4 py-3">
          <div className="flex items-center gap-3">
            <AlertTriangle className="h-4 w-4 text-zinc-500" />
            <span>Request Type</span>
          </div>
          <span className="mono-data text-zinc-400">
            {selectedTicket?.category || "Unknown"}
          </span>
        </div>
      </div>

      {decision ? (
        <div className={`mt-5 rounded-2xl border p-4 text-xs ${tone.box}`}>
          <div className="grid gap-3 sm:grid-cols-2">
            <div className="flex items-center gap-2">
              <Cpu className={`h-3.5 w-3.5 ${tone.label}`} />
              <span className={`mono-data uppercase tracking-[0.18em] ${tone.label}`}>
                engine
              </span>
              <span className={tone.text}>
                {decision.decision_version ?? "v1"} / {decision.rule_version ?? "rules-2026-graph"}
              </span>
            </div>
            <div className="flex items-center gap-2">
              <Brain className={`h-3.5 w-3.5 ${tone.label}`} />
              <span className={`mono-data uppercase tracking-[0.18em] ${tone.label}`}>
                model
              </span>
              <span className={tone.text}>
                {decision.model_version ?? "rules (no trained model)"}
              </span>
            </div>
            <div className="flex items-center gap-2">
              <Database className={`h-3.5 w-3.5 ${tone.label}`} />
              <span className={`mono-data uppercase tracking-[0.18em] ${tone.label}`}>
                priority
              </span>
              <span className={tone.text}>
                {decision.priority_score?.toFixed(1) ?? "—"} · confidence{" "}
                {decision.confidence_score?.toFixed(0) ?? "—"}%
              </span>
            </div>
            <div className="flex items-center gap-2">
              <span className={`mono-data uppercase tracking-[0.18em] ${tone.label}`}>
                band
              </span>
              <span className={`font-mono ${tone.text}`}>
                {decision.decision_band ?? "—"} · interval{" "}
                {decision.priority_interval_low !== null &&
                decision.priority_interval_low !== undefined &&
                decision.priority_interval_high !== null &&
                decision.priority_interval_high !== undefined
                  ? `${decision.priority_interval_low.toFixed(0)}–${decision.priority_interval_high.toFixed(0)}`
                  : "—"}
              </span>
            </div>
            <div className="flex items-center gap-2 sm:col-span-2">
              <Hash className={`h-3.5 w-3.5 ${tone.label}`} />
              <span className={`mono-data uppercase tracking-[0.18em] ${tone.label}`}>
                hash
              </span>
              <span className={`font-mono ${tone.text}`}>
                {decision.decision_hash
                  ? `${decision.decision_hash.slice(0, 16)}…`
                  : "—"}
              </span>
              <Network className={`h-3.5 w-3.5 ${tone.label}`} />
              <span className={`mono-data uppercase tracking-[0.18em] ${tone.label}`}>
                graph
              </span>
              <span className={`font-mono ${tone.text}`}>
                degree {decision.graph_degree ?? 0} · weighted{" "}
                {decision.graph_weighted_degree?.toFixed(2) ?? "0.00"}
              </span>
            </div>
            {/* All sub-scores + graph_centrality + z — now with tiny hairline bars for visual weight (still mono dense, no card clutter). */}
            <div className="sm:col-span-2 grid grid-cols-2 md:grid-cols-5 gap-x-3 gap-y-1 text-[10px] mono-data pt-1 border-t border-white/5">
              {[
                ["sev", decision.severity_score],
                ["urg", decision.urgency_score],
                ["biz", decision.business_impact_score],
                ["sla", decision.sla_risk_score],
                ["rec", decision.recurrence_score],
                ["dep", decision.dependency_criticality_score],
                ["act", decision.actionability_score],
                ["unc", decision.uncertainty_penalty],
                ["z", (decision as any).anomaly_zscore],
                ["graph", (decision as any).graph_centrality_score],
              ].map(([k, v]) => {
                const num = typeof v === "number" ? v : 0;
                const isZ = k === "z";
                const maxRef = isZ ? 3 : 100;
                const w = Math.max(2, Math.min(100, (Math.abs(num) / maxRef) * 100));
                return (
                  <div key={k as string} className="flex items-center gap-1">
                    <span className="text-zinc-500 w-8">{k}</span>
                    <span className={tone.text + " w-8 text-right"}>{isZ ? num.toFixed(2) : (num as number).toFixed(0)}</span>
                    <div className="h-[2px] flex-1 bg-zinc-800/70 rounded overflow-hidden">
                      <div className={`h-full ${k === "graph" ? "bg-amber-500" : "bg-zinc-500"}`} style={{ width: `${w}%` }} />
                    </div>
                  </div>
                );
              })}
            </div>
            {decision.band_rationale ? (
              <div className="sm:col-span-2">
                <span className={`mono-data uppercase tracking-[0.18em] ${tone.label}`}>
                  rationale
                </span>
                <span className={`ml-2 ${tone.text}`}>{decision.band_rationale}</span>
              </div>
            ) : null}
            {decision.operator_action ? (
              <div className="sm:col-span-2">
                <span className={`mono-data uppercase tracking-[0.18em] ${tone.label}`}>
                  operator action
                </span>
                <span className={`ml-2 ${tone.text}`}>{decision.operator_action}</span>
              </div>
            ) : null}
            {decision.graph_reasoning ? (
              <div className="sm:col-span-2">
                <span className={`mono-data uppercase tracking-[0.18em] ${tone.label}`}>
                  graph reasoning
                </span>
                <span className={`ml-2 ${tone.text}`}>{decision.graph_reasoning}</span>
              </div>
            ) : null}
            {decision.explanation_json ? (
              <div className="sm:col-span-2">
                <span className={`mono-data uppercase tracking-[0.18em] ${tone.label}`}>
                  explanation
                </span>
                <div className={`mt-2 space-y-1 ${tone.text}`}>
                  {Object.entries(decision.explanation_json as Record<string, unknown>).map(([key, value]) => {
                    const num = typeof value === "number" ? value : null;
                    const w = num != null ? Math.max(4, Math.min(100, Math.abs(num) * 50)) : 0; // scale for viz
                    return (
                      <div key={key} className="flex items-center gap-2 text-[11px]">
                        <span className="text-zinc-400 w-20 truncate">{key}</span>
                        <span className="mono-data w-10 text-right">{num != null ? num.toFixed(2) : String(value)}</span>
                        {num != null && (
                          <div className="h-[2px] flex-1 bg-zinc-800/70 rounded overflow-hidden">
                            <div className="h-full bg-amber-400/80" style={{ width: `${w}%` }} />
                          </div>
                        )}
                      </div>
                    );
                  })}
                </div>
              </div>
            ) : null}
          </div>
        </div>
      ) : null}

      {detail?.recommendations?.length ? (
        <div className="mt-5 space-y-2">
          {detail.recommendations.slice(0, 3).map((rec) => (
            <div
              key={rec.id}
              className="flex flex-col gap-2 rounded-2xl border border-zinc-800/60 bg-black/20 p-3 text-xs text-zinc-200 sm:flex-row sm:items-center sm:justify-between"
            >
              <div>
                <div className="font-medium text-zinc-100">
                  {rec.action_label || rec.action_type || "Action"}
                </div>
                <div className="text-zinc-400">{rec.rationale || "—"}</div>
              </div>
              <button
                type="button"
                onClick={() => handleAcceptTop(rec)}
                disabled={pendingAction === `accept:${rec.id}`}
                className="inline-flex items-center justify-center rounded-full border border-emerald-500/30 bg-emerald-500/10 px-3 py-1.5 text-[11px] font-medium text-emerald-200 transition hover:border-emerald-400/60 disabled:cursor-not-allowed disabled:opacity-60"
              >
                {pendingAction === `accept:${rec.id}` ? "Applying…" : "Apply"}
              </button>
            </div>
          ))}
        </div>
      ) : null}
    </div>
  );
}
