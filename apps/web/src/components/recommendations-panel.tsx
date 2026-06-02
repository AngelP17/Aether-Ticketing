"use client";

import { useState } from "react";
import {
  AlertCircle,
  Brain,
  Check,
  ChevronDown,
  ChevronUp,
  ClipboardCheck,
  Cpu,
  Database,
  Loader2,
  RotateCcw,
  Sparkles,
  X,
} from "lucide-react";

import { useToast } from "@/components/notifications";
import { actionsApi, decisionsApi, recommendationsApi } from "@/lib/api";
import { canWriteTickets } from "@/lib/auth";
import type {
  ActionRun,
  ApplyRecommendationResponse,
  Decision,
  Feedback,
  Recommendation,
  TicketDetailPayload,
} from "@/types";

type RecommendationsPanelProps = {
  ticketId: string;
  detail: TicketDetailPayload;
  onDetailRefresh: () => Promise<void> | void;
  canMutate: boolean;
};

type PendingKey = string;

function fmtTimestamp(value?: string | null) {
  if (!value) {
    return "—";
  }
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) {
    return value;
  }
  return date.toLocaleString();
}

function describeFeedback(feedback?: Feedback | null) {
  if (!feedback) {
    return null;
  }
  const typeMap: Record<string, string> = {
    accepted: "Accepted",
    rejected: "Rejected",
    overridden: "Overridden",
    not_useful: "Marked not useful",
    duplicate_fix: "Marked duplicate fix",
    wrong_priority: "Wrong priority",
  };
  return {
    label: typeMap[feedback.feedback_type] || feedback.feedback_type,
    note: feedback.feedback_note || null,
    operator: feedback.operator_id || "api-user",
    ts: fmtTimestamp(feedback.feedback_ts),
  };
}

function describeActionRun(run?: ActionRun | null) {
  if (!run) {
    return null;
  }
  return {
    id: run.id,
    actionType: run.action_type,
    status: run.status,
    startedAt: fmtTimestamp(run.started_at),
    finishedAt: fmtTimestamp(run.finished_at),
    rollbackAvailable: run.rollback_available,
    requestedBy: run.requested_by,
    approvedBy: run.approved_by,
    operatorNote: run.operator_note,
  };
}

export function RecommendationsPanel({
  ticketId,
  detail,
  onDetailRefresh,
  canMutate,
}: RecommendationsPanelProps) {
  const toast = useToast();
  const [pending, setPending] = useState<PendingKey | null>(null);
  const [overrideOpen, setOverrideOpen] = useState<number | null>(null);
  const [overrideNote, setOverrideNote] = useState("");
  const [overridePriority, setOverridePriority] = useState<string>("");
  const [confirmOpen, setConfirmOpen] = useState<number | null>(null);
  const [confirmNote, setConfirmNote] = useState("");

  const recommendations = detail.recommendations ?? [];
  const decision: Decision | null | undefined = detail.decision;

  const handleApply = async (
    recommendation: Recommendation,
    options: { confirm?: boolean; note?: string; actionType?: string } = {},
  ) => {
    if (!canMutate) {
      toast.error("You do not have permission to mutate tickets.");
      return;
    }
    if (recommendation.action_type === "auto_resolve" && !options.confirm) {
      setConfirmOpen(recommendation.id);
      setConfirmNote(options.note ?? "");
      return;
    }
    const key = `apply:${recommendation.id}`;
    setPending(key);
    try {
      const response = await actionsApi.apply(recommendation.id, {
        action_type: options.actionType,
        confirm: options.confirm,
        note: options.note,
      });
      const payload = response.data as ApplyRecommendationResponse;
      toast.success(
        options.confirm
          ? `Action run #${payload.action_run.id} applied (${payload.action_run.status})`
          : `Recommendation accepted — action run #${payload.action_run.id} ${payload.action_run.status}`,
      );
      await onDetailRefresh();
    } catch (error: unknown) {
      const message = extractErrorMessage(error);
      toast.error(`Apply failed: ${message}`);
    } finally {
      setPending(null);
    }
  };

  const handleReject = async (recommendation: Recommendation, note: string) => {
    if (!canMutate) {
      toast.error("You do not have permission to mutate tickets.");
      return;
    }
    const key = `reject:${recommendation.id}`;
    setPending(key);
    try {
      await recommendationsApi.reject(recommendation.id, note);
      toast.success("Recommendation rejected and logged.");
      await onDetailRefresh();
    } catch (error: unknown) {
      const message = extractErrorMessage(error);
      toast.error(`Reject failed: ${message}`);
    } finally {
      setPending(null);
    }
  };

  const handleOverride = async (recommendation: Recommendation) => {
    if (!canMutate) {
      toast.error("You do not have permission to mutate tickets.");
      return;
    }
    if (!overrideNote.trim()) {
      toast.error("Override note is required.");
      return;
    }
    const key = `override:${recommendation.id}`;
    setPending(key);
    try {
      const priorityNumber = overridePriority.trim()
        ? Number.parseFloat(overridePriority)
        : undefined;
      await recommendationsApi.override(
        recommendation.id,
        overrideNote.trim(),
        Number.isFinite(priorityNumber) ? priorityNumber : undefined,
      );
      toast.success("Override recorded.");
      setOverrideOpen(null);
      setOverrideNote("");
      setOverridePriority("");
      await onDetailRefresh();
    } catch (error: unknown) {
      const message = extractErrorMessage(error);
      toast.error(`Override failed: ${message}`);
    } finally {
      setPending(null);
    }
  };

  const handleRecompute = async () => {
    const key = "recompute";
    setPending(key);
    try {
      await decisionsApi.recompute(ticketId);
      toast.success("Decision recomputed from the latest ticket state.");
      await onDetailRefresh();
    } catch (error: unknown) {
      const message = extractErrorMessage(error);
      toast.error(`Recompute failed: ${message}`);
    } finally {
      setPending(null);
    }
  };

  return (
    <div className="ops-card rounded-[1.75rem] p-6">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div className="flex items-center gap-3">
          <Sparkles className="h-5 w-5 text-amber-300" />
          <div>
            <div className="text-lg font-semibold text-white">
              Ranked decisions
            </div>
            <div className="mt-1 text-sm text-zinc-500">
              Apply, reject, or override the recommendations the decision engine
              produced for this ticket.
            </div>
          </div>
        </div>
        <button
          type="button"
          onClick={handleRecompute}
          disabled={pending === "recompute"}
          className="inline-flex items-center gap-2 rounded-full border border-cyan-400/20 bg-cyan-500/10 px-3 py-1.5 text-xs font-medium text-cyan-100 transition hover:border-cyan-200/40 disabled:cursor-not-allowed disabled:opacity-60"
        >
          {pending === "recompute" ? (
            <Loader2 className="h-3.5 w-3.5 animate-spin" />
          ) : (
            <RotateCcw className="h-3.5 w-3.5" />
          )}
          Recompute
        </button>
      </div>

      {decision ? (
        <DecisionMetadata decision={decision} />
      ) : (
        <div className="mt-4 rounded-2xl border border-dashed border-zinc-800 bg-zinc-950/50 px-4 py-5 text-sm leading-7 text-zinc-500">
          No decision record yet. Trigger a recompute to generate the priority
          score and ranked actions.
        </div>
      )}

      {recommendations.length === 0 ? (
        <div className="mt-4 rounded-2xl border border-dashed border-zinc-800 bg-zinc-950/50 px-4 py-5 text-sm leading-7 text-zinc-500">
          No recommendations proposed. Recompute the decision to surface them.
        </div>
      ) : (
        <ol className="mt-5 space-y-4">
          {recommendations.map((rec) => (
            <li
              key={rec.id}
              className="rounded-2xl border border-zinc-800 bg-zinc-950/60 p-4"
            >
              <div className="flex flex-wrap items-start justify-between gap-3">
                <div className="min-w-0">
                  <div className="flex items-center gap-2 text-[10px] font-mono uppercase tracking-[0.28em] text-amber-300">
                    <span>Rank {rec.rank}</span>
                    <span aria-hidden>·</span>
                    <span className="text-zinc-500">{rec.action_type}</span>
                    {rec.requires_approval ? (
                      <span className="rounded-full border border-rose-400/30 bg-rose-500/10 px-2 py-0.5 text-[10px] text-rose-200">
                        Approval required
                      </span>
                    ) : null}
                  </div>
                  <h3 className="mt-1 text-base font-semibold text-white">
                    {rec.action_label}
                  </h3>
                  <p className="mt-1 text-sm text-zinc-400">{rec.rationale}</p>
                </div>
                <div className="flex flex-col items-end gap-1 text-right text-[11px] font-mono uppercase tracking-[0.18em] text-zinc-500">
                  <span>Risk · {rec.risk_level}</span>
                  <span>Confidence · {Math.round(rec.confidence * 100)}%</span>
                  {rec.recommended_runbook_id ? (
                    <span>Runbook · {rec.recommended_runbook_id}</span>
                  ) : null}
                </div>
              </div>

              <RecommendationStatus summary={summarizeStatus(rec)} />

              {canMutate ? (
                <div className="mt-4 flex flex-wrap items-center gap-2">
                  <button
                    type="button"
                    onClick={() => handleApply(rec)}
                    disabled={pending === `apply:${rec.id}`}
                    className="inline-flex items-center gap-2 rounded-full bg-amber-500 px-3 py-1.5 text-xs font-semibold text-black transition hover:bg-amber-400 disabled:cursor-not-allowed disabled:opacity-60"
                  >
                    {pending === `apply:${rec.id}` ? (
                      <Loader2 className="h-3.5 w-3.5 animate-spin" />
                    ) : (
                      <Check className="h-3.5 w-3.5" />
                    )}
                    Accept &amp; apply
                  </button>
                  <button
                    type="button"
                    onClick={() => handleReject(rec, "Operator rejected.")}
                    disabled={pending === `reject:${rec.id}`}
                    className="inline-flex items-center gap-2 rounded-full border border-zinc-700 bg-zinc-950/60 px-3 py-1.5 text-xs font-medium text-zinc-200 transition hover:border-rose-400/40 hover:text-rose-100 disabled:cursor-not-allowed disabled:opacity-60"
                  >
                    {pending === `reject:${rec.id}` ? (
                      <Loader2 className="h-3.5 w-3.5 animate-spin" />
                    ) : (
                      <X className="h-3.5 w-3.5" />
                    )}
                    Reject
                  </button>
                  <button
                    type="button"
                    onClick={() =>
                      setOverrideOpen((current) =>
                        current === rec.id ? null : rec.id,
                      )
                    }
                    className="inline-flex items-center gap-2 rounded-full border border-zinc-700 bg-zinc-950/60 px-3 py-1.5 text-xs font-medium text-zinc-200 transition hover:border-cyan-400/40 hover:text-cyan-100"
                  >
                    Override
                    {overrideOpen === rec.id ? (
                      <ChevronUp className="h-3.5 w-3.5" />
                    ) : (
                      <ChevronDown className="h-3.5 w-3.5" />
                    )}
                  </button>
                </div>
              ) : (
                <div className="mt-4 inline-flex items-center gap-2 rounded-full border border-zinc-800 bg-zinc-950/40 px-3 py-1.5 text-[11px] text-zinc-500">
                  <AlertCircle className="h-3.5 w-3.5" />
                  Read-only — agent or admin role required to mutate.
                </div>
              )}

              {overrideOpen === rec.id && canMutate ? (
                <div className="mt-3 rounded-2xl border border-cyan-500/20 bg-cyan-500/5 p-3 text-sm">
                  <label className="block text-[10px] font-mono uppercase tracking-[0.18em] text-cyan-200">
                    Override note (required)
                  </label>
                  <textarea
                    value={overrideNote}
                    onChange={(event) => setOverrideNote(event.target.value)}
                    rows={2}
                    className="mt-1 w-full rounded-xl border border-cyan-500/30 bg-black/40 p-2 text-sm text-white outline-none focus:border-cyan-300/60"
                    placeholder="Why are you overriding the engine's recommendation?"
                  />
                  <label className="mt-3 block text-[10px] font-mono uppercase tracking-[0.18em] text-cyan-200">
                    Override priority score (optional)
                  </label>
                  <input
                    type="number"
                    value={overridePriority}
                    onChange={(event) => setOverridePriority(event.target.value)}
                    min={0}
                    max={100}
                    step={0.1}
                    className="mt-1 w-full rounded-xl border border-cyan-500/30 bg-black/40 p-2 text-sm text-white outline-none focus:border-cyan-300/60"
                    placeholder="e.g. 78.5"
                  />
                  <div className="mt-3 flex items-center gap-2">
                    <button
                      type="button"
                      onClick={() => handleOverride(rec)}
                      disabled={pending === `override:${rec.id}`}
                      className="inline-flex items-center gap-2 rounded-full bg-cyan-500 px-3 py-1.5 text-xs font-semibold text-black transition hover:bg-cyan-400 disabled:cursor-not-allowed disabled:opacity-60"
                    >
                      {pending === `override:${rec.id}` ? (
                        <Loader2 className="h-3.5 w-3.5 animate-spin" />
                      ) : (
                        <ClipboardCheck className="h-3.5 w-3.5" />
                      )}
                      Submit override
                    </button>
                    <button
                      type="button"
                      onClick={() => {
                        setOverrideOpen(null);
                        setOverrideNote("");
                        setOverridePriority("");
                      }}
                      className="text-xs text-zinc-500 underline-offset-2 hover:text-zinc-300 hover:underline"
                    >
                      Cancel
                    </button>
                  </div>
                </div>
              ) : null}

              {confirmOpen === rec.id ? (
                <div className="mt-3 rounded-2xl border border-amber-500/30 bg-amber-500/10 p-3 text-sm text-amber-50">
                  <div className="flex items-center gap-2 text-amber-200">
                    <AlertCircle className="h-4 w-4" />
                    Auto-resolve will set the ticket to Resolved. Type a note
                    and confirm.
                  </div>
                  <textarea
                    value={confirmNote}
                    onChange={(event) => setConfirmNote(event.target.value)}
                    rows={2}
                    className="mt-2 w-full rounded-xl border border-amber-500/40 bg-black/40 p-2 text-sm text-white outline-none focus:border-amber-300/60"
                    placeholder="Closure note (optional)"
                  />
                  <div className="mt-2 flex items-center gap-2">
                    <button
                      type="button"
                      onClick={() => {
                        const next = confirmOpen;
                        setConfirmOpen(null);
                        setConfirmNote("");
                        void handleApply(rec, { confirm: true, note: confirmNote });
                      }}
                      className="inline-flex items-center gap-2 rounded-full bg-amber-500 px-3 py-1.5 text-xs font-semibold text-black transition hover:bg-amber-400"
                    >
                      <Check className="h-3.5 w-3.5" />
                      Confirm auto-resolve
                    </button>
                    <button
                      type="button"
                      onClick={() => {
                        setConfirmOpen(null);
                        setConfirmNote("");
                      }}
                      className="text-xs text-amber-200/80 underline-offset-2 hover:text-amber-100 hover:underline"
                    >
                      Cancel
                    </button>
                  </div>
                </div>
              ) : null}
            </li>
          ))}
        </ol>
      )}
    </div>
  );
}

function RecommendationStatus({
  summary,
}: {
  summary: ReturnType<typeof summarizeStatus>;
}) {
  if (!summary) {
    return null;
  }
  return (
    <div className="mt-3 grid gap-2 text-[11px] sm:grid-cols-2">
      {summary.feedback ? (
        <div className="rounded-xl border border-zinc-800 bg-black/30 px-3 py-2">
          <div className="font-mono uppercase tracking-[0.18em] text-zinc-500">
            Last feedback
          </div>
          <div className="mt-1 text-sm text-zinc-200">
            {summary.feedback.label}{" "}
            <span className="text-zinc-500">by {summary.feedback.operator}</span>
          </div>
          <div className="mt-0.5 text-[10px] text-zinc-500">
            {summary.feedback.ts}
          </div>
          {summary.feedback.note ? (
            <div className="mt-1 text-xs text-zinc-300">
              “{summary.feedback.note}”
            </div>
          ) : null}
        </div>
      ) : null}
      {summary.actionRun ? (
        <div className="rounded-xl border border-zinc-800 bg-black/30 px-3 py-2">
          <div className="font-mono uppercase tracking-[0.18em] text-zinc-500">
            Latest action run
          </div>
          <div className="mt-1 text-sm text-zinc-200">
            #{summary.actionRun.id} · {summary.actionRun.status}
          </div>
          <div className="mt-0.5 text-[10px] text-zinc-500">
            Started {summary.actionRun.startedAt}
            {summary.actionRun.rollbackAvailable
              ? " · rollback available"
              : ""}
          </div>
          {summary.actionRun.operatorNote ? (
            <div className="mt-1 text-xs text-zinc-300">
              “{summary.actionRun.operatorNote}”
            </div>
          ) : null}
        </div>
      ) : null}
    </div>
  );
}

function summarizeStatus(rec: Recommendation) {
  const feedback = describeFeedback(rec.last_feedback);
  const actionRun = describeActionRun(rec.latest_action_run);
  if (!feedback && !actionRun) {
    return null;
  }
  return { feedback, actionRun };
}

function DecisionMetadata({ decision }: { decision: Decision }) {
  const bandTone =
    decision.decision_band === "high_confidence_action"
      ? "border-emerald-500/30 bg-emerald-500/5 text-emerald-100"
      : decision.decision_band === "review_needed"
        ? "border-rose-500/30 bg-rose-500/5 text-rose-100"
        : "border-amber-500/20 bg-amber-500/5 text-amber-100";
  const intervalLow = decision.priority_interval_low ?? null;
  const intervalHigh = decision.priority_interval_high ?? null;
  const intervalText =
    intervalLow !== null && intervalHigh !== null
      ? `${intervalLow.toFixed(0)}–${intervalHigh.toFixed(0)}`
      : "—";
  return (
    <div className={`mt-4 space-y-3 rounded-2xl border p-4 text-xs ${bandTone}`}>
      <div className="grid gap-3 sm:grid-cols-2">
        <div className="flex items-center gap-2">
          <Cpu className="h-3.5 w-3.5 opacity-80" />
          <span className="font-mono uppercase tracking-[0.18em] opacity-70">engine</span>
          <span>{decision.decision_version ?? "v1"} / {decision.rule_version ?? "rules-2024-Q1"}</span>
        </div>
        <div className="flex items-center gap-2">
          <Brain className="h-3.5 w-3.5 opacity-80" />
          <span className="font-mono uppercase tracking-[0.18em] opacity-70">model</span>
          <span>{decision.model_version ?? "rules (no trained model)"}</span>
        </div>
        <div className="flex items-center gap-2">
          <Database className="h-3.5 w-3.5 opacity-80" />
          <span className="font-mono uppercase tracking-[0.18em] opacity-70">priority</span>
          <span>
            {decision.priority_score?.toFixed(1) ?? "—"} · confidence{" "}
            {decision.confidence_score?.toFixed(0) ?? "—"}%
          </span>
        </div>
        <div className="flex items-center gap-2">
          <span className="font-mono uppercase tracking-[0.18em] opacity-70">band</span>
          <span className="font-mono">
            {decision.decision_band ?? "—"} · interval {intervalText}
          </span>
        </div>
        <div className="flex items-center gap-2 sm:col-span-2">
          <span className="font-mono uppercase tracking-[0.18em] opacity-70">hash</span>
          <span className="font-mono">
            {decision.decision_hash ? `${decision.decision_hash.slice(0, 12)}…` : "—"}
          </span>
          <span className="font-mono uppercase tracking-[0.18em] opacity-70">graph</span>
          <span className="font-mono">
            degree {decision.graph_degree ?? 0} · weighted{" "}
            {decision.graph_weighted_degree?.toFixed(2) ?? "0.00"}
          </span>
        </div>
        {decision.band_rationale ? (
          <div className="sm:col-span-2">
            <span className="font-mono uppercase tracking-[0.18em] opacity-70">rationale</span>
            <span className="ml-2">{decision.band_rationale}</span>
          </div>
        ) : null}
        {decision.operator_action ? (
          <div className="sm:col-span-2">
            <span className="font-mono uppercase tracking-[0.18em] opacity-70">operator action</span>
            <span className="ml-2">{decision.operator_action}</span>
          </div>
        ) : null}
        {decision.graph_reasoning ? (
          <div className="sm:col-span-2">
            <span className="font-mono uppercase tracking-[0.18em] opacity-70">graph reasoning</span>
            <span className="ml-2">{decision.graph_reasoning}</span>
          </div>
        ) : null}
      </div>
    </div>
  );
}

function extractErrorMessage(error: unknown): string {
  if (error instanceof Error) {
    return error.message;
  }
  if (typeof error === "object" && error !== null) {
    const maybeResponse = (error as { response?: { data?: { detail?: string } } })
      .response;
    if (maybeResponse?.data?.detail) {
      return maybeResponse.data.detail;
    }
  }
  return "Unknown error";
}

export function canMutateRecommendations(user?: { role?: string | null } | null) {
  return canWriteTickets({ username: "", display_name: "", role: user?.role ?? "viewer" });
}
