export function SectionEmptyState({
  title,
  message,
}: {
  title: string;
  message: string;
}) {
  return (
    <div className="rounded-[20px] border border-dashed border-zinc-800/70 bg-black/15 px-4 py-8 text-center">
      <div className="mono-data text-[10px] uppercase tracking-[0.28em] text-zinc-500">{title}</div>
      <p className="mt-2 text-sm leading-6 text-zinc-400">{message}</p>
    </div>
  );
}
