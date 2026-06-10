"use client";

export default function GlobalError({
  error,
  reset,
}: {
  error: Error & { digest?: string };
  reset: () => void;
}) {
  return (
    <html lang="en">
      <body>
        <main className="min-h-screen bg-[#050505] px-6 py-16 text-zinc-100">
          <section className="mx-auto flex max-w-xl flex-col gap-5 rounded-[22px] border border-white/10 bg-zinc-950/90 p-6 shadow-2xl">
            <div>
              <p className="font-mono text-xs uppercase tracking-[0.16em] text-amber-300">Application Error</p>
              <h1 className="mt-3 text-2xl font-semibold text-white">The workspace could not render.</h1>
              <p className="mt-2 text-sm leading-6 text-zinc-400">
                Refresh the session or return to the login screen if the problem persists.
              </p>
            </div>
            {error.digest ? <p className="font-mono text-xs text-zinc-500">Digest {error.digest}</p> : null}
            <button
              type="button"
              onClick={reset}
              className="inline-flex h-11 items-center justify-center rounded-xl bg-amber-400 px-5 text-sm font-semibold text-black transition hover:bg-amber-300"
            >
              Try again
            </button>
          </section>
        </main>
      </body>
    </html>
  );
}
