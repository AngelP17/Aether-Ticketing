"use client";

import { useMountedFlag } from "./hooks";
import { SectionEmptyState } from "./section-empty-state";
import type { BreakdownItem } from "./types";

export function PriorityStackChart({ data }: { data: BreakdownItem[] }) {
  const mounted = useMountedFlag();
  if (!data.length) {
    return (
      <div className="ops-card rounded-[24px] p-5 sm:p-6">
        <div className="mono-data text-[10px] uppercase tracking-[0.28em] text-zinc-500">
          Priority Breakdown
        </div>
        <div className="mt-4">
          <SectionEmptyState
            title="No priority mix"
            message="Priority distribution will populate after the live queue loads."
          />
        </div>
      </div>
    );
  }

  const total = data.reduce((sum, slice) => sum + slice.value, 0) || 1;
  const lowPriority = data.find((s) => s.label === "Low")?.value || 0;
  const lowPercent = total > 0 ? Math.round((lowPriority / total) * 100) : 0;
  const ariaLabel = data.length
    ? `Priority breakdown chart with ${data.map((slice) => `${slice.label} ${slice.value}`).join(", ")}. Low priority share ${lowPercent} percent.`
    : "Priority breakdown chart with no data.";

  return (
    <div className="ops-card rounded-[24px] p-5 sm:p-6" role="img" aria-label={ariaLabel}>
      <div className="mono-data text-[10px] uppercase tracking-[0.28em] text-zinc-500">
        Priority Breakdown
      </div>
      <div className="mt-5 flex h-3 rounded-md overflow-hidden">
        {data.map((slice) => (
          <div
            key={slice.label}
            className="transition-all duration-300 hover:brightness-125"
            style={{
              width: mounted ? `${(slice.value / total) * 100}%` : "0%",
              backgroundColor: slice.color,
            }}
            title={`${slice.label}: ${slice.value}`}
          />
        ))}
      </div>
      <div className="mt-5 space-y-3">
        {data.map((slice) => (
          <div key={slice.label} className="flex items-center gap-2.5">
            <span className="h-2.5 w-2.5 rounded-full shrink-0" style={{ backgroundColor: slice.color }} />
            <span className="w-16 shrink-0 text-[12px] text-zinc-300">{slice.label}</span>
            <div className="h-1 flex-1 rounded-full bg-zinc-900/80 overflow-hidden">
              <div
                className="h-full rounded-full transition-all duration-1000"
                style={{
                  width: mounted ? `${Math.max((slice.value / total) * 100, 2)}%` : "0%",
                  backgroundColor: slice.color,
                }}
              />
            </div>
            <span className="mono-data text-[12px] text-zinc-400 w-7 text-right shrink-0">
              {slice.value}
            </span>
            <span className="mono-data text-[10px] text-zinc-600 w-8 text-right shrink-0">
              {Math.round((slice.value / total) * 100)}%
            </span>
          </div>
        ))}
      </div>
      <div className="mt-4 pt-3 border-t border-zinc-800/30 flex items-center gap-2">
        <svg className="w-3.5 h-3.5 text-emerald-500 shrink-0" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth="2">
          <path strokeLinecap="round" strokeLinejoin="round" d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z" />
        </svg>
        <span className="text-[10px] text-zinc-500">{lowPercent}% low priority, healthy distribution</span>
      </div>
    </div>
  );
}
