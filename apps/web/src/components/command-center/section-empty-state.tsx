export function SectionEmptyState({
  title,
  message,
}: {
  title: string;
  message: string;
}) {
  return (
    <div className="rounded-[22px] border border-dashed border-zinc-800/70 bg-black/15 px-4 py-8 text-center">
      <div className="text-sm font-medium text-zinc-300">{title}</div>
      <p className="mt-2 text-sm leading-6 text-zinc-400">{message}</p>
    </div>
  );
}
