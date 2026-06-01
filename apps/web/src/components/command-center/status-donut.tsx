"use client";

import { useMountedFlag } from "./hooks";
import { SectionEmptyState } from "./section-empty-state";
import type { BreakdownItem } from "./types";

export function CompactStatusChart({ data }: { data: BreakdownItem[] }) {
  const mounted = useMountedFlag();
  if (!data.length) {
    return (
      <div className="ops-card rounded-[24px] p-5 sm:p-6">
        <div className="mono-data text-[10px] uppercase tracking-[0.28em] text-zinc-500">
          Status Distribution
        </div>
        <div className="mt-4">
          <SectionEmptyState
            title="No ticket distribution"
            message="Status segments will appear once live tickets are available."
          />
        </div>
      </div>
    );
  }

  const total = data.reduce((sum, slice) => sum + slice.value, 0) || 1;
  const radius = 52;
  const strokeWidth = 10;
  const circumference = 2 * Math.PI * radius;
  const gap = 10;
  const available = circumference - gap * data.length;
  let offset = 0;

  const closedResolved = data
    .filter((s) => ["Closed", "Resolved"].includes(s.label))
    .reduce((sum, s) => sum + s.value, 0);
  const resolutionRate = total > 0 ? ((closedResolved / total) * 100).toFixed(1) : "0";
  const ariaLabel = data.length
    ? `Status distribution chart with ${data
        .map((slice) => `${slice.label} ${slice.value}`)
        .join(", ")}. Resolution rate ${resolutionRate} percent.`
    : "Status distribution chart with no data.";

  return (
    <div className="ops-card rounded-[24px] p-5 sm:p-6" role="img" aria-label={ariaLabel}>
      <div className="mono-data text-[10px] uppercase tracking-[0.28em] text-zinc-500">
        Status Distribution
      </div>
      <div className="mt-4 flex flex-col gap-5 md:flex-row md:items-center md:gap-6">
        <svg
          viewBox="0 0 140 140"
          className="mx-auto h-28 w-28 shrink-0 sm:h-32 sm:w-32 md:mx-0"
          aria-hidden="true"
          focusable="false"
        >
          <circle cx="70" cy="70" r={radius} fill="none" stroke="rgba(63,63,70,0.35)" strokeWidth={strokeWidth} />
          {data.map((slice) => {
            const length = (slice.value / total) * available;
            const displayLength = mounted ? length : 0;
            const node = (
              <circle
                key={slice.label}
                cx="70"
                cy="70"
                r={radius}
                fill="none"
                stroke={slice.color}
                strokeWidth={strokeWidth}
                strokeLinecap="round"
                strokeDasharray={`${displayLength} ${circumference}`}
                strokeDashoffset={-offset}
                transform="rotate(-90 70 70)"
                style={{
                  opacity: mounted ? 1 : 0.75,
                  transition: "stroke-dasharray 1.2s cubic-bezier(0.22,1,0.36,1), opacity 0.5s ease",
                }}
              />
            );
            offset += length + gap;
            return node;
          })}
          <text x="70" y="66" textAnchor="middle" className="fill-zinc-50 text-[20px] font-bold">
            {total}
          </text>
          <text x="70" y="82" textAnchor="middle" className="fill-zinc-500 text-[7px]" style={{ fontFamily: "var(--font-mono), monospace", letterSpacing: "0.2em" }}>
            TOTAL
          </text>
        </svg>
        <div className="w-full space-y-3">
          {data.map((slice) => (
            <div key={slice.label} className="flex items-center gap-2.5">
              <span className="h-2.5 w-2.5 rounded-full shrink-0" style={{ backgroundColor: slice.color }} />
              <span className="w-[76px] shrink-0 text-[12px] text-zinc-300 sm:w-[84px]">{slice.label}</span>
              <div className="h-1 flex-1 rounded-full bg-zinc-900/80 overflow-hidden">
                <div
                  className="h-full rounded-full transition-all duration-1000 ease-out"
                  style={{
                    width: mounted ? `${Math.max((slice.value / total) * 100, 2)}%` : "0%",
                    backgroundColor: slice.color,
                  }}
                />
              </div>
              <span className="mono-data text-[12px] text-zinc-400 w-6 text-right shrink-0">
                {slice.value}
              </span>
            </div>
          ))}
        </div>
      </div>
      <div className="mt-4 flex items-center gap-2 border-t border-zinc-800/30 pt-3">
        <span className="text-[9px] mono-data text-zinc-600 uppercase tracking-wider">Resolution Rate</span>
        <span className="text-sm mono-data font-semibold text-emerald-400">{resolutionRate}%</span>
      </div>
    </div>
  );
}
