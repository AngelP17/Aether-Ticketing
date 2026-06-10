"use client";

import Link from "next/link";
import { useCallback, useState } from "react";
import {
  ArrowRight,
  FileSpreadsheet,
  FileText,
  Plus,
  Radar,
  Shield,
  ShieldCheck,
  Zap,
} from "lucide-react";

import { OpsShell } from "@/components/ops-shell";
import { useToast } from "@/components/notifications";
import { reportsApi } from "@/lib/api";
import { parseFilename } from "@/lib/export-utils";

const workbookTabs = [
  {
    name: "Executive Summary",
    description: "Queue totals, SLA pressure, and incident counts.",
    accent: "#f59e0b",
  },
  {
    name: "Operational Queue",
    description: "Ranked ticket sheet with priority bands, confidence, assignment, and recommended action.",
    accent: "#06b6d4",
  },
  {
    name: "Incident Clusters",
    description: "Grouped operational patterns with common cause, scope, and impact summary.",
    accent: "#8b5cf6",
  },
  {
    name: "Decision Review",
    description: "Score breakdowns, root-cause notes, and recommended actions per case.",
    accent: "#22c55e",
  },
  {
    name: "Audit Extract",
    description: "Decision history, recommendation outcomes, and operator feedback trace.",
    accent: "#f43f5e",
  },
];

const reportHighlights = [
  {
    label: "Workbook",
    note: "5-tab styled Excel export",
    color: "#f59e0b",
    icon: FileSpreadsheet,
  },
  {
    label: "Audit extract",
    note: "Replay and trace preserved",
    color: "#22c55e",
    icon: ShieldCheck,
  },
  {
    label: "Ops handoff",
    note: "Queue and decision review",
    color: "#06b6d4",
    icon: Radar,
  },
];

type ExportFormat = "xlsx" | "csv";

export default function ReportsPage() {
  const toast = useToast();
  const [activeFormat, setActiveFormat] = useState<ExportFormat | null>(null);

  const handleDownload = useCallback(
    async (format: ExportFormat) => {
      if (activeFormat) {
        return;
      }

      setActiveFormat(format);

      try {
        const response = await reportsApi.excel({ report_type: format });

        if (response.status !== 200) {
          const data = response.data as any;
          const msg = data?.detail || data?.message || `Export failed with status ${response.status}`;
          throw new Error(msg);
        }

        const blob = response.data as Blob;
        if (blob.size === 0) {
          throw new Error("The export was empty.");
        }

        const filename = parseFilename(
          response.headers["content-disposition"] as string | null,
          format === "csv" ? "aether_report.csv" : "aether_report.xlsx",
        );
        const url = URL.createObjectURL(blob);

        const anchor = document.createElement("a");
        anchor.href = url;
        anchor.download = filename;
        anchor.rel = "noopener";
        document.body.appendChild(anchor);
        anchor.click();
        anchor.remove();

        window.setTimeout(() => URL.revokeObjectURL(url), 1000);
        toast.success(
          format === "csv" ? "CSV download started" : "Workbook download started",
          filename,
        );
      } catch (error) {
        const message =
          error instanceof Error ? error.message : "Could not generate export.";
        toast.error("Export failed", message);
      } finally {
        setActiveFormat(null);
      }
    },
    [activeFormat, toast],
  );

  const handleWorkbookDownload = useCallback(
    () => handleDownload("xlsx"),
    [handleDownload],
  );
  const handleCsvDownload = useCallback(
    () => handleDownload("csv"),
    [handleDownload],
  );

  const isDownloading = activeFormat !== null;

  return (
    <OpsShell
      eyebrow="Aether OpsCenter"
      title="Reports & Export"
      subtitle="Download the styled Excel workbook or the CSV extract for queue review, incident analysis, and audit delivery."
      statusPill={{ kind: "ready", label: "Live" }}
      headerActions={
        <>
          <Link
            href="/command-center"
            className="inline-flex items-center gap-2 rounded-2xl border border-zinc-700 bg-zinc-900/70 px-4 py-2.5 text-sm font-medium text-zinc-100 transition hover:border-amber-500/30 hover:bg-amber-500/10"
          >
            <Radar size={16} />
            Command Center
          </Link>
          <button
            type="button"
            onClick={handleCsvDownload}
            disabled={isDownloading}
            aria-busy={isDownloading && activeFormat === "csv"}
            className="inline-flex items-center gap-2 rounded-2xl border border-zinc-700 bg-zinc-900/70 px-4 py-2.5 text-sm font-medium text-zinc-100 transition hover:border-cyan-500/30 hover:bg-cyan-500/10 disabled:cursor-not-allowed disabled:opacity-70"
          >
            <FileText size={16} />
            {activeFormat === "csv" ? "Preparing CSV..." : "Download CSV"}
          </button>
          <button
            type="button"
            onClick={handleWorkbookDownload}
            disabled={isDownloading}
            aria-busy={isDownloading && activeFormat === "xlsx"}
            className="inline-flex items-center gap-2 rounded-2xl bg-amber-500 px-4 py-2.5 text-sm font-semibold text-black transition hover:bg-amber-400 disabled:cursor-not-allowed disabled:opacity-70"
          >
            <FileSpreadsheet size={16} />
            {activeFormat === "xlsx" ? "Preparing workbook..." : "Download Workbook"}
          </button>
        </>
      }
      exportButton={{
        isExporting: isDownloading && activeFormat === "xlsx",
        onClick: handleWorkbookDownload,
        label: "Download workbook",
      }}
      showNotificationBell
    >
      <div className="mx-auto max-w-[1500px]">
        <div className="ops-glass rounded-[2rem] overflow-hidden">
          <div className="border-b border-zinc-800/70 bg-black/20 px-5 py-5 sm:px-8">
            <div className="max-w-2xl">
              <h1 className="text-2xl font-semibold tracking-tight text-white sm:text-3xl">
                Reports &amp; Export
              </h1>
              <p className="mt-2 text-sm leading-6 text-zinc-400">
                Download the styled Excel workbook or the matching CSV extract for queue review, incident analysis, and audit delivery.
              </p>
            </div>
          </div>

          <div className="grid gap-4 border-b border-zinc-800/70 px-5 py-5 sm:grid-cols-3 sm:px-8">
            {reportHighlights.map((item) => {
              const Icon = item.icon;
              return (
                <div key={item.label} className="ops-card rounded-2xl p-5">
                  <div className="flex items-center justify-between">
                    <div className="text-sm font-medium text-zinc-300">{item.label}</div>
                    <div className="flex h-10 w-10 items-center justify-center rounded-2xl border border-white/5 bg-black/20">
                      <Icon size={16} style={{ color: item.color }} />
                    </div>
                  </div>
                  <div className="mt-4 text-lg font-semibold text-white">{item.note}</div>
                </div>
              );
            })}
          </div>

          <div className="grid gap-6 px-5 py-5 sm:px-8 xl:grid-cols-[1.1fr,0.9fr]">
            <section className="ops-card rounded-[22px] p-5 sm:p-6">
              <div className="flex items-center justify-between gap-4 border-b border-zinc-800/70 pb-4">
                <div>
                  <h2 className="text-xl font-semibold text-white">Workbook Contents</h2>
                  <p className="mt-2 text-sm leading-6 text-zinc-500">
                    Each tab covers a specific review step.
                  </p>
                </div>
                <div className="mono-data rounded-full border border-zinc-700 bg-zinc-900/70 px-3 py-1 text-[11px] uppercase tracking-[0.24em] text-zinc-300">
                  5 tabs
                </div>
              </div>

              <div className="mt-5 space-y-3">
                {workbookTabs.map((tab, index) => (
                  <div key={tab.name} className="rounded-2xl border border-zinc-800 bg-zinc-950/55 p-4 sm:p-5">
                    <div className="flex items-start gap-4">
                      <div
                        className="mono-data flex h-10 w-10 items-center justify-center rounded-2xl border text-sm font-semibold"
                        style={{
                          color: tab.accent,
                          borderColor: `${tab.accent}35`,
                          backgroundColor: `${tab.accent}14`,
                        }}
                      >
                        {index + 1}
                      </div>
                      <div className="min-w-0">
                        <div className="text-base font-semibold text-zinc-100">{tab.name}</div>
                        <div className="mt-2 text-sm leading-6 text-zinc-500">{tab.description}</div>
                      </div>
                    </div>
                  </div>
                ))}
              </div>
            </section>

            <section className="space-y-5">
              <div className="ops-card rounded-[22px] p-5 sm:p-6">
                <div className="mt-5 space-y-4 text-sm leading-7 text-zinc-300">
                  <p>Executives get a formatted summary sheet.</p>
                  <p>Operators keep ranked queue context, recommendations, and incident grouping together.</p>
                  <p>Audit and replay data are exported as a separate sheet.</p>
                </div>
              </div>

              <div className="ops-card rounded-[22px] p-5 sm:p-6">
              <div className="mt-5 grid gap-3">
                  <Link
                    href="/tickets/new"
                    className="flex items-center justify-between rounded-2xl border border-zinc-800 bg-zinc-950/60 px-4 py-3 text-sm text-zinc-200 transition hover:border-amber-500/20 hover:bg-zinc-900/80"
                  >
                    <span>Create a new ticket</span>
                    <Plus size={16} className="text-zinc-500" />
                  </Link>
                  <Link
                    href="/command-center"
                    className="flex items-center justify-between rounded-2xl border border-zinc-800 bg-zinc-950/60 px-4 py-3 text-sm text-zinc-200 transition hover:border-amber-500/20 hover:bg-zinc-900/80"
                  >
                    <span>Return to live queue</span>
                    <ArrowRight size={16} className="text-zinc-500" />
                  </Link>
                  <Link
                    href="/board"
                    className="flex items-center justify-between rounded-2xl border border-zinc-800 bg-zinc-950/60 px-4 py-3 text-sm text-zinc-200 transition hover:border-amber-500/20 hover:bg-zinc-900/80"
                  >
                    <span>Open workflow board</span>
                    <ArrowRight size={16} className="text-zinc-500" />
                  </Link>
                  <Link
                    href="/admin"
                    className="flex items-center justify-between rounded-2xl border border-zinc-800 bg-zinc-950/60 px-4 py-3 text-sm text-zinc-200 transition hover:border-amber-500/20 hover:bg-zinc-900/80"
                  >
                    <span>Open admin console</span>
                    <Shield size={16} className="text-zinc-500" />
                  </Link>
                </div>
              </div>

              <div className="rounded-[22px] border border-amber-500/20 bg-amber-500/10 p-5 sm:p-6">
                <p className="text-sm leading-7 text-amber-100">
                  If the backend is unavailable, the download fails without breaking the page. Both the workbook and CSV reflect the latest data.
                </p>
              </div>

              <div className="rounded-[22px] border border-zinc-800 bg-zinc-950/60 p-5 sm:p-6">
                <div className="flex items-center gap-3">
                  <div className="flex h-11 w-11 items-center justify-center rounded-2xl bg-amber-500/10 text-amber-300">
                    <Zap size={18} />
                  </div>
                  <div>
                    <div className="text-base font-semibold text-white">Export quality</div>
                    <div className="mt-1 text-sm text-zinc-500">
                      Exports are formatted for direct use in reviews and audits.
                    </div>
                  </div>
                </div>
              </div>
            </section>
          </div>
        </div>
      </div>
    </OpsShell>
  );
}
