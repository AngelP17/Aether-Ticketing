"use client";

import { useEffect } from "react";
import Link from "next/link";

export default function GlobalError({
  error,
  reset,
}: {
  error: Error & { digest?: string };
  reset: () => void;
}) {
  useEffect(() => {
    // Log to a real sink (Sentry/Datadog) once configured; keep console
    // for now so dev surfaces it and prod never silences it.
    console.error("Aether route error boundary caught:", error);
  }, [error]);

  return (
    <div className="min-h-[100dvh] flex items-center justify-center bg-[var(--bg-deep)] px-4">
      <div className="ops-card w-full max-w-md rounded-2xl border border-rose-500/20 p-6 shadow-2xl shadow-black/30 sm:p-8">
        <p className="text-xs uppercase tracking-[0.28em] text-rose-300">
          Route error
        </p>
        <h1 className="mt-3 text-2xl font-semibold tracking-tight text-white sm:text-3xl">
          Something broke rendering this page
        </h1>
        <p className="mt-3 text-sm leading-6 text-slate-400">
          {error.message || "An unexpected error occurred. The data backing this view is unchanged."}
        </p>
        {error.digest ? (
          <p className="mt-2 mono-data text-[11px] text-slate-500">
            ref: {error.digest}
          </p>
        ) : null}
        <div className="mt-6 flex flex-wrap gap-3">
          <button
            type="button"
            onClick={reset}
            className="rounded-2xl border border-amber-400/30 bg-amber-500/10 px-4 py-2.5 text-sm font-semibold text-amber-100 transition hover:bg-amber-500/20"
          >
            Retry
          </button>
          <Link
            href="/command-center"
            className="rounded-2xl border border-white/10 bg-white/5 px-4 py-2.5 text-sm font-medium text-slate-200 transition hover:border-cyan-300/40 hover:bg-cyan-400/10 hover:text-white"
          >
            Back to command center
          </Link>
        </div>
      </div>
    </div>
  );
}
