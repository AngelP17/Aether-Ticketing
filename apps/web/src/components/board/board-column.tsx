"use client";

import type { DragEvent, ReactNode } from "react";

export type BoardColumnDef = {
  key: string;
  label: string;
  description: string;
  accent: string;
  pillTone: string;
};

export function BoardColumn({
  column,
  count,
  isDropTarget,
  onDragOver,
  onDragLeave,
  onDrop,
  children,
}: {
  column: BoardColumnDef;
  count: number;
  isDropTarget: boolean;
  onDragOver: (event: DragEvent<HTMLDivElement>, key: string) => void;
  onDragLeave: (key: string) => void;
  onDrop: (event: DragEvent<HTMLDivElement>, key: string) => void;
  children: ReactNode;
}) {
  return (
    <section
      className={`ops-card flex w-full shrink-0 flex-col rounded-[22px] border transition sm:p-5 ${
        isDropTarget ? "border-amber-400/40 shadow-[0_18px_50px_rgba(245,158,11,0.18)]" : "border-transparent"
      }`}
      style={{ scrollSnapAlign: "start" }}
    >
      <div className="border-b border-zinc-800/70 p-4 sm:p-0 sm:pb-4">
        <div className="flex items-start justify-between gap-3">
          <div>
            <div className="flex items-center gap-3">
              <span className="h-2.5 w-2.5 rounded-full" style={{ backgroundColor: column.accent }} />
              <h2 className="text-lg font-semibold text-white">
                {column.label}{" "}
                <span className="mono-data ml-1 text-[12px] font-normal text-zinc-500">({count})</span>
              </h2>
            </div>
            <p className="mt-2 hidden text-sm leading-6 text-zinc-500 sm:block">{column.description}</p>
          </div>
          <div
            className={`mono-data rounded-full border px-3 py-1 text-[11px] uppercase tracking-[0.24em] ${column.pillTone}`}
            aria-label={`${count} tickets in ${column.label}`}
          >
            {count}
          </div>
        </div>
      </div>

      <div
        role="region"
        aria-label={`${column.label} drop zone`}
        onDragOver={(event) => onDragOver(event, column.key)}
        onDragLeave={() => onDragLeave(column.key)}
        onDrop={(event) => onDrop(event, column.key)}
        className={`min-h-[180px] max-h-[600px] flex-1 space-y-3 overflow-y-auto p-4 sm:p-0 sm:pt-4 ${
          isDropTarget ? "bg-amber-500/[0.04]" : ""
        }`}
      >
        {children}
      </div>
    </section>
  );
}
