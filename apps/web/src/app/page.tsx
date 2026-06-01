import Link from "next/link";
import { Activity, Columns3, FileBarChart, Gauge, Plus, Shield } from "lucide-react";

const entrances = [
  {
    title: "Command Center",
    href: "/command-center",
    icon: Gauge,
    accent: "amber",
  },
  {
    title: "Incident Board",
    href: "/board",
    icon: Columns3,
    accent: "cyan",
  },
  {
    title: "Reports",
    href: "/reports",
    icon: FileBarChart,
    accent: "emerald",
  },
  {
    title: "Admin Console",
    href: "/admin",
    icon: Shield,
    accent: "violet",
  },
];

export default function Home() {
  return (
    <main className="ops-grid relative flex min-h-[100dvh] items-center justify-center px-4 py-8">
      <div className="absolute inset-0 pointer-events-none">
        <div className="absolute top-0 right-0 h-96 w-96 rounded-full bg-amber-500/8 blur-[140px]" />
        <div className="absolute bottom-0 left-0 h-80 w-80 rounded-full bg-cyan-500/8 blur-[120px]" />
      </div>

      <div className="relative z-10 w-full max-w-5xl">
        <div className="ops-glass rounded-[2rem] overflow-hidden">
          <div className="grid lg:grid-cols-[1.15fr,0.85fr]">

            {/* Left panel */}
            <section className="px-7 py-9 sm:px-10 sm:py-12 lg:px-12 lg:py-14">
              <div className="mono-data text-[10px] uppercase tracking-[0.36em] text-amber-300">
                Aether OpsCenter
              </div>
              <h1 className="mt-5 text-3xl font-semibold tracking-tight text-white sm:text-4xl lg:text-[2.6rem] lg:leading-[1.12]">
                Ranked tickets, incident context, and report exports in one view.
              </h1>
              <p className="mt-4 max-w-lg text-sm leading-7 text-zinc-400">
                Open where you need to work, then move between the command center, board, and reports without losing context.
              </p>

              <div className="mt-8 flex flex-wrap gap-3">
                <Link
                  href="/command-center"
                  className="inline-flex items-center gap-2 rounded-2xl bg-amber-500 px-5 py-3 text-sm font-semibold text-black transition hover:bg-amber-400 active:scale-[0.98]"
                >
                  <Activity className="h-4 w-4" />
                  Open Command Center
                </Link>
                <Link
                  href="/tickets/new"
                  className="inline-flex items-center gap-2 rounded-2xl border border-zinc-700/70 bg-zinc-900/60 px-5 py-3 text-sm font-medium text-zinc-100 transition hover:border-zinc-500 hover:bg-zinc-800/70 active:scale-[0.98]"
                >
                  <Plus className="h-4 w-4" />
                  New ticket
                </Link>
              </div>

              <div className="mt-10 border-t border-zinc-800/60 pt-7">
                <Link
                  href="/login"
                  className="inline-flex items-center gap-2 text-sm text-zinc-500 transition hover:text-zinc-300"
                >
                  Sign in to your account
                  <span aria-hidden="true" className="text-zinc-600">→</span>
                </Link>
              </div>
            </section>

            {/* Right panel */}
            <aside className="border-t border-zinc-800/60 bg-black/25 px-6 py-8 lg:border-l lg:border-t-0 lg:px-8 lg:py-10">
              <p className="mono-data text-[10px] uppercase tracking-[0.32em] text-zinc-500 mb-5">
                Quick access
              </p>
              <div className="grid gap-2.5">
                {entrances.map((item) => {
                  const Icon = item.icon;
                  const accentMap: Record<string, string> = {
                    amber: "border-amber-500/20 bg-amber-500/8 hover:border-amber-500/35 hover:bg-amber-500/14",
                    cyan: "border-cyan-500/20 bg-cyan-500/8 hover:border-cyan-500/35 hover:bg-cyan-500/14",
                    emerald: "border-emerald-500/20 bg-emerald-500/8 hover:border-emerald-500/35 hover:bg-emerald-500/14",
                    violet: "border-violet-500/20 bg-violet-500/8 hover:border-violet-500/35 hover:bg-violet-500/14",
                  };
                  const iconMap: Record<string, string> = {
                    amber: "text-amber-300",
                    cyan: "text-cyan-300",
                    emerald: "text-emerald-300",
                    violet: "text-violet-300",
                  };
                  return (
                    <Link
                      key={item.title}
                      href={item.href}
                      className={`group flex items-center justify-between rounded-2xl border px-4 py-4 transition active:scale-[0.99] ${accentMap[item.accent]}`}
                    >
                      <span className="flex items-center gap-3">
                        <Icon className={`h-4 w-4 shrink-0 ${iconMap[item.accent]}`} />
                        <span className="text-sm font-medium text-zinc-100">{item.title}</span>
                      </span>
                      <span className="text-zinc-600 transition group-hover:translate-x-0.5 group-hover:text-zinc-400" aria-hidden="true">
                        →
                      </span>
                    </Link>
                  );
                })}
              </div>
            </aside>
          </div>
        </div>
      </div>
    </main>
  );
}
