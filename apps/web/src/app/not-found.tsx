import Link from "next/link";

export default function NotFound() {
  return (
    <div className="min-h-[100dvh] flex items-center justify-center bg-[var(--bg-deep)] px-4">
      <div className="ops-card w-full max-w-md rounded-2xl border border-zinc-800 p-6 shadow-2xl shadow-black/30 sm:p-8 text-center">
        <p className="mono-data text-sm text-amber-300">404</p>
        <h1 className="mt-2 text-2xl font-semibold tracking-tight text-white sm:text-3xl">
          Page not found
        </h1>
        <p className="mt-3 text-sm leading-6 text-slate-400">
          This URL is not a valid OpsCenter route. Return to the command center.
        </p>
        <div className="mt-6 flex flex-wrap justify-center gap-3">
          <Link
            href="/command-center"
            className="rounded-2xl border border-amber-400/30 bg-amber-500/10 px-4 py-2.5 text-sm font-semibold text-amber-100 transition hover:bg-amber-500/20"
          >
            Open command center
          </Link>
          <Link
            href="/board"
            className="rounded-2xl border border-white/10 bg-white/5 px-4 py-2.5 text-sm font-medium text-slate-200 transition hover:border-cyan-300/40 hover:bg-cyan-400/10 hover:text-white"
          >
            Open workflow board
          </Link>
        </div>
      </div>
    </div>
  );
}
