export default function Loading() {
  return (
    <div
      className="min-h-[100dvh] flex items-center justify-center bg-[var(--bg-deep)] text-sm text-zinc-400"
      aria-busy="true"
      aria-live="polite"
    >
      <div className="flex flex-col items-center gap-3">
        <div
          className="h-7 w-7 rounded-full border-2 border-amber-500/25 border-t-amber-400 animate-spin"
          aria-hidden="true"
        />
        <div>Loading…</div>
      </div>
    </div>
  );
}
