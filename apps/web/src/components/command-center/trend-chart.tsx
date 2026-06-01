"use client";

import { useMemo, useState } from "react";
import type { Ticket } from "@/types";
import { useMountedFlag, useElementWidth } from "./hooks";
import { SectionEmptyState } from "./section-empty-state";
import type { TrendData } from "./types";

function computeTrendData(tickets: Ticket[]): TrendData {
  const now = new Date();
  const days = 14;
  const labels: string[] = [];
  const created: number[] = [];
  const resolved: number[] = [];

  for (let i = days - 1; i >= 0; i--) {
    const date = new Date(now);
    date.setDate(date.getDate() - i);
    const dateStr = date.toLocaleDateString("en-US", { month: "short", day: "numeric" });
    labels.push(dateStr);

    const dayStart = new Date(date);
    dayStart.setHours(0, 0, 0, 0);
    const dayEnd = new Date(date);
    dayEnd.setHours(23, 59, 59, 999);

    const dayCreated = tickets.filter((t) => {
      if (!t.created_at) return false;
      const createdDate = new Date(t.created_at);
      return createdDate >= dayStart && createdDate <= dayEnd;
    }).length;

    const dayResolved = tickets.filter((t) => {
      if (!t.resolved_at) return false;
      const resolvedDate = new Date(t.resolved_at);
      return resolvedDate >= dayStart && resolvedDate <= dayEnd;
    }).length;

    created.push(dayCreated);
    resolved.push(dayResolved);
  }

  return { labels, created, resolved };
}

export function TrendChart({ tickets }: { tickets: Ticket[] }) {
  const mounted = useMountedFlag();
  const { ref: chartWrapRef, width: chartWidth } = useElementWidth<HTMLDivElement>(400, 280);
  const trend = useMemo(() => computeTrendData(tickets), [tickets]);
  const total14dCreated = trend.created.reduce((a, b) => a + b, 0);
  const total14dResolved = trend.resolved.reduce((a, b) => a + b, 0);
  const netBacklog = total14dCreated - total14dResolved;
  const isEmpty = total14dCreated === 0 && total14dResolved === 0;
  const [hoveredIndex, setHoveredIndex] = useState<number | null>(null);

  const svgWidth = Math.max(chartWidth, 280);
  const svgHeight = chartWidth < 360 ? 168 : 152;
  const pad = { l: 8, r: 8, t: 12, b: 28 };
  const cW = svgWidth - pad.l - pad.r;
  const cH = svgHeight - pad.t - pad.b;
  const xS = trend.labels.length > 1 ? cW / (trend.labels.length - 1) : cW;
  const maxV = Math.max(...trend.created, ...trend.resolved, 1);

  const yP = (v: number) => pad.t + cH - (v / maxV) * cH;
  const xP = (i: number) => pad.l + i * xS;
  const activeIndex = hoveredIndex ?? -1;

  const activePoint =
    activeIndex >= 0
      ? {
          index: activeIndex,
          label: trend.labels[activeIndex],
          created: trend.created[activeIndex],
          resolved: trend.resolved[activeIndex],
          x: xP(activeIndex),
          createdY: yP(trend.created[activeIndex]),
          resolvedY: yP(trend.resolved[activeIndex]),
        }
      : null;

  function crPath(pts: [number, number][]) {
    if (pts.length < 2) return "";
    let d = `M ${pts[0][0].toFixed(1)},${pts[0][1].toFixed(1)}`;
    for (let i = 0; i < pts.length - 1; i++) {
      const p0 = pts[Math.max(0, i - 1)];
      const p1 = pts[i];
      const p2 = pts[i + 1];
      const p3 = pts[Math.min(pts.length - 1, i + 2)];
      d += ` C ${(p1[0] + (p2[0] - p0[0]) / 6).toFixed(1)},${(p1[1] + (p2[1] - p0[1]) / 6).toFixed(1)} ${(p2[0] - (p3[0] - p1[0]) / 6).toFixed(1)},${(p2[1] - (p3[1] - p1[1]) / 6).toFixed(1)} ${p2[0].toFixed(1)},${p2[1].toFixed(1)}`;
    }
    return d;
  }

  const cPts = trend.created.map((v, i) => [xP(i), yP(v)] as [number, number]);
  const rPts = trend.resolved.map((v, i) => [xP(i), yP(v)] as [number, number]);
  const cLine = crPath(cPts);
  const rLine = crPath(rPts);
  const cArea = `${cLine} L ${xP(trend.labels.length - 1).toFixed(1)},${(pad.t + cH).toFixed(1)} L ${xP(0).toFixed(1)},${(pad.t + cH).toFixed(1)} Z`;
  const rArea = `${rLine} L ${xP(trend.labels.length - 1).toFixed(1)},${(pad.t + cH).toFixed(1)} L ${xP(0).toFixed(1)},${(pad.t + cH).toFixed(1)} Z`;
  const hasMeaningfulData = !isEmpty;
  const labelStep = chartWidth < 360 ? 3 : 2;
  const tooltipLeft = activePoint ? Math.min(svgWidth - 24, Math.max(activePoint.x, 24)) : 0;
  const tooltipTop = activePoint ? Math.max(Math.min(activePoint.createdY, activePoint.resolvedY) - 10, 8) : 0;
  const daySegmentBounds = trend.labels.map((_, index) => {
    const center = xP(index);
    const left = index === 0 ? pad.l : (xP(index - 1) + center) / 2;
    const right = index === trend.labels.length - 1 ? svgWidth - pad.r : (center + xP(index + 1)) / 2;
    return { left, width: Math.max(right - left, 1) };
  });

  if (!hasMeaningfulData) {
    return (
      <div className="ops-card rounded-[24px] p-5 sm:p-6" role="img" aria-label="14-day trend chart. No ticket activity in the last 14 days.">
        <div className="flex items-start justify-between gap-4">
          <div className="flex items-center gap-4">
            <div className="flex items-center gap-1.5">
              <span className="h-[2px] w-3 rounded-full bg-amber-500" />
              <span className="mono-data text-[10px] text-zinc-500">Created</span>
            </div>
            <div className="flex items-center gap-1.5">
              <span className="h-[2px] w-3 rounded-full bg-emerald-500" />
              <span className="mono-data text-[10px] text-zinc-500">Resolved</span>
            </div>
          </div>
        </div>

        <div className="mt-3 flex h-[168px] items-center justify-center rounded-[20px] border border-dashed border-zinc-800/70 bg-black/15 px-4 text-center">
          <SectionEmptyState
            title="No ticket activity"
            message="The last 14 days are empty, so there is no trend line to draw yet."
          />
        </div>

        {/*
          Section 4.7 ops-tiles exception: 14d Created, 14d Resolved, and
          Net backlog below are mono data labels, not section eyebrows. They
          communicate state for the active tile, not section topic, and stay
          uppercase mono by design.
        */}
        <div className="mt-4 pt-3 border-t border-zinc-800/30 flex items-center justify-between">
          <div className="flex items-center gap-4">
            <div>
              <span className="text-[9px] mono-data text-zinc-600 uppercase tracking-wider">14d Created</span>
              <div className="mono-data text-[13px] font-semibold text-zinc-300 mt-0.5">0</div>
            </div>
            <div>
              <span className="text-[9px] mono-data text-zinc-600 uppercase tracking-wider">14d Resolved</span>
              <div className="mono-data text-[13px] font-semibold text-zinc-300 mt-0.5">0</div>
            </div>
          </div>
          <div className="text-right">
            <span className="text-[9px] mono-data text-zinc-600 uppercase tracking-wider">Net</span>
            <div className="mono-data mt-0.5 text-[13px] font-semibold text-emerald-400">
              0 <span className="text-[10px] font-normal text-zinc-600">backlog</span>
            </div>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="ops-card rounded-[24px] p-5 sm:p-6">
      <div className="flex flex-col gap-3 sm:flex-row sm:items-start sm:justify-between">
        <div className="mono-data text-[10px] uppercase tracking-[0.28em] text-zinc-500">14-Day Trend</div>
        <div className="flex flex-wrap items-center gap-4">
          <div className="flex items-center gap-1.5">
            <span className="w-3 h-[2px] rounded-full bg-amber-500" />
            <span className="text-[10px] mono-data text-zinc-500">Created</span>
          </div>
          <div className="flex items-center gap-1.5">
            <span className="w-3 h-[2px] rounded-full bg-emerald-500" />
            <span className="text-[10px] mono-data text-zinc-500">Resolved</span>
          </div>
        </div>
      </div>

      <div ref={chartWrapRef} className="mt-3 relative" style={{ height: svgHeight }}>
        <svg
          width="100%"
          height="100%"
          viewBox={`0 0 ${svgWidth} ${svgHeight}`}
          preserveAspectRatio="xMidYMid meet"
          role="img"
          aria-label={`14-day created and resolved trend chart. ${trend.labels[0]} through ${trend.labels[trend.labels.length - 1]}.`}
        >
          <defs>
            <linearGradient id="grad-c" x1="0" y1="0" x2="0" y2="1">
              <stop offset="0%" stopColor="#f59e0b" stopOpacity="0.25" />
              <stop offset="100%" stopColor="#f59e0b" stopOpacity="0.01" />
            </linearGradient>
            <linearGradient id="grad-r" x1="0" y1="0" x2="0" y2="1">
              <stop offset="0%" stopColor="#22c55e" stopOpacity="0.2" />
              <stop offset="100%" stopColor="#22c55e" stopOpacity="0.01" />
            </linearGradient>
          </defs>

          {[2, 4, 6, 8].map((v) => (
            <line
              key={v}
              x1={pad.l}
              y1={yP(v)}
              x2={svgWidth - pad.r}
              y2={yP(v)}
              stroke="rgba(63,63,70,0.18)"
              strokeWidth="1"
              strokeDasharray="4 4"
            />
          ))}

          <path
            d={cArea}
            fill="url(#grad-c)"
            className="transition-opacity duration-700 ease-out"
            style={{ opacity: mounted ? 0.6 : 0 }}
          />
          <path
            d={rArea}
            fill="url(#grad-r)"
            className="transition-opacity duration-700 ease-out"
            style={{ opacity: mounted ? 0.6 : 0 }}
          />
          <path
            d={cLine}
            fill="none"
            stroke="#f59e0b"
            strokeWidth="2"
            strokeLinecap="round"
            strokeLinejoin="round"
            pathLength={100}
            strokeDasharray="100 100"
            strokeDashoffset={mounted ? 0 : 100}
            className="transition-[stroke-dashoffset] duration-1000 ease-out"
          />
          <path
            d={rLine}
            fill="none"
            stroke="#22c55e"
            strokeWidth="2"
            strokeLinecap="round"
            strokeLinejoin="round"
            pathLength={100}
            strokeDasharray="100 100"
            strokeDashoffset={mounted ? 0 : 100}
            className="transition-[stroke-dashoffset] duration-1000 ease-out"
          />

          {activePoint && (
            <>
              <line
                x1={activePoint.x}
                y1={pad.t}
                x2={activePoint.x}
                y2={pad.t + cH}
                stroke="rgba(245, 158, 11, 0.35)"
                strokeWidth="1"
                strokeDasharray="4 4"
              />
              <circle cx={activePoint.x} cy={activePoint.createdY} r="3.5" fill="#f59e0b" stroke="#09090b" strokeWidth="2" />
              <circle cx={activePoint.x} cy={activePoint.resolvedY} r="3.5" fill="#22c55e" stroke="#09090b" strokeWidth="2" />
            </>
          )}

          {daySegmentBounds.map((segment, index) => (
            <rect
              key={trend.labels[index]}
              x={segment.left}
              y={pad.t}
              width={segment.width}
              height={cH}
              fill="transparent"
              tabIndex={0}
              role="button"
              aria-label={`${trend.labels[index]}: created ${trend.created[index]}, resolved ${trend.resolved[index]}`}
              onFocus={() => setHoveredIndex(index)}
              onBlur={() => setHoveredIndex((current) => (current === index ? null : current))}
              onMouseEnter={() => setHoveredIndex(index)}
              onMouseMove={() => setHoveredIndex(index)}
              onMouseLeave={() => setHoveredIndex((current) => (current === index ? null : current))}
              onClick={() => setHoveredIndex(index)}
              onKeyDown={(event) => {
                if (event.key === "Escape") {
                  setHoveredIndex(null);
                }
              }}
            />
          ))}
        </svg>

        {activePoint && (
          <div
            className="pointer-events-none absolute z-20 min-w-40 rounded-2xl border border-zinc-700/70 bg-[#0a0a0d]/95 px-3 py-2 shadow-2xl backdrop-blur-xl"
            style={{
              left: `${(tooltipLeft / svgWidth) * 100}%`,
              top: `${(tooltipTop / svgHeight) * 100}%`,
              transform: "translate(-50%, -100%)",
            }}
          >
            <div className="mono-data text-[10px] uppercase tracking-[0.24em] text-zinc-500">{activePoint.label}</div>
            <div className="mt-2 space-y-1.5 text-[11px] text-zinc-300">
              <div className="flex items-center justify-between gap-4">
                <span className="text-zinc-500">Created</span>
                <span className="mono-data text-amber-300">{activePoint.created}</span>
              </div>
              <div className="flex items-center justify-between gap-4">
                <span className="text-zinc-500">Resolved</span>
                <span className="mono-data text-emerald-300">{activePoint.resolved}</span>
              </div>
            </div>
          </div>
        )}
      </div>

      <div className="flex justify-between mt-1.5 px-0.5">
        {trend.labels.map((label, i) => (
          <span key={label} className="mono-data text-[9px] text-zinc-600">
            {i % labelStep !== 0 && i !== trend.labels.length - 1 ? "" : label.split(" ")[1]}
          </span>
        ))}
      </div>

      {/*
        Section 4.7 ops-tiles exception: 14d Created, 14d Resolved, and
        Net backlog below are mono data labels, not section eyebrows. They
        communicate state for the active tile, not section topic, and stay
        uppercase mono by design.
      */}
      <div className="mt-4 pt-3 border-t border-zinc-800/30 flex items-center justify-between">
        <div className="flex items-center gap-4">
          <div>
            <span className="text-[9px] mono-data text-zinc-600 uppercase tracking-wider">14d Created</span>
            <div className="mono-data text-[13px] text-zinc-300 font-semibold mt-0.5">{total14dCreated}</div>
          </div>
          <div>
            <span className="text-[9px] mono-data text-zinc-600 uppercase tracking-wider">14d Resolved</span>
            <div className="mono-data text-[13px] text-zinc-300 font-semibold mt-0.5">{total14dResolved}</div>
          </div>
        </div>
        <div className="text-right">
          <span className="text-[9px] mono-data text-zinc-600 uppercase tracking-wider">Net</span>
          <div className={`mono-data text-[13px] font-semibold mt-0.5 ${netBacklog >= 0 ? "text-amber-400" : "text-emerald-400"}`}>
            {netBacklog >= 0 ? "+" : ""}{netBacklog} <span className="text-[10px] text-zinc-600 font-normal">backlog</span>
          </div>
        </div>
      </div>
    </div>
  );
}
