import Link from "next/link";
import { Activity, Columns3, FileBarChart, Gauge, Plus, Shield } from "lucide-react";

const entrances = [
  {
    title: "Command Center",
    href: "/command-center",
    description: "Ranked queue, live ops.",
    icon: Gauge,
  },
  {
    title: "Workflow Board",
    href: "/board",
    description: "Lane-based ticket board.",
    icon: Columns3,
  },
  {
    title: "Reports",
    href: "/reports",
    description: "Excel + CSV exports.",
    icon: FileBarChart,
  },
  {
    title: "Admin Console",
    href: "/admin",
    description: "Users, roles, taxonomy.",
    icon: Shield,
  },
];

export default function Home() {
  return (
    <main className="ops-grid relative flex min-h-[100dvh] items-center justify-center px-4 py-8">
      <div className="absolute inset-0 pointer-events-none">
        <div className="absolute top-0 right-0 h-96 w-96 rounded-full bg-amber-500/[0.08] blur-[140px]" />
        <div className="absolute bottom-0 left-0 h-80 w-80 rounded-full bg-amber-500/[0.06] blur-[120px]" />
      </div>

      <div className="relative z-10 w-full max-w-5xl">
        <div className="ops-glass rounded-2xl overflow-hidden sm:rounded-[2rem]">
          <div className="grid lg:grid-cols-[1.15fr,0.85fr]">

            {/* Left panel */}
            <section className="px-7 py-9 sm:px-10 sm:py-12 lg:px-12 lg:py-14">
              <div className="aether-eyebrow text-amber-300">
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

            {/* Right panel — one accent (amber) only, differentiate by icon + label + zebra surface */}
            <aside className="border-t border-zinc-800/60 bg-black/25 px-6 py-8 lg:border-l lg:border-t-0 lg:px-8 lg:py-10">
              <p className="aether-eyebrow mb-5">
                Quick access
              </p>
              <div className="grid gap-2.5">
                {entrances.map((item) => {
                  const Icon = item.icon;
                  return (
                    <Link
                      key={item.title}
                      href={item.href}
                      className="group flex items-center justify-between rounded-2xl border border-zinc-800/80 bg-black/20 px-4 py-4 transition hover:border-amber-400/30 hover:bg-amber-500/[0.06] active:scale-[0.99]"
                    >
                      <span className="flex min-w-0 items-center gap-3">
                        <Icon className="h-4 w-4 shrink-0 text-amber-300" />
                        <span className="min-w-0">
                          <span className="block text-sm font-medium text-zinc-100">
                            {item.title}
                          </span>
                          <span className="block truncate text-[11px] text-zinc-500">
                            {item.description}
                          </span>
                        </span>
                      </span>
                      <span
                        className="text-zinc-600 transition group-hover:translate-x-0.5 group-hover:text-amber-300"
                        aria-hidden="true"
                      >
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
