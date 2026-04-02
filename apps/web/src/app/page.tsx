import Link from "next/link";

const entrances = [
  {
    title: "Command Center",
    href: "/command-center",
    eyebrow: "Primary view",
    description:
      "Open the ranked queue, review live decisions, and move from triage to action without extra clicks.",
  },
  {
    title: "Incident Board",
    href: "/board",
    eyebrow: "Ops board",
    description:
      "Jump straight into the operational board for the current ticket stream, clustering cues, and queue pressure.",
  },
  {
    title: "New Ticket",
    href: "/tickets/new",
    eyebrow: "Transactional",
    description:
      "Create and manage real tickets, attach files, and keep the new Aether design tied to actual operational work.",
  },
  {
    title: "Reports",
    href: "/reports",
    eyebrow: "Exports",
    description:
      "Download the styled Excel workbook and review the operational summary in a format stakeholders actually use.",
  },
  {
    title: "Admin Console",
    href: "/admin",
    eyebrow: "Management",
    description:
      "Manage users, privileges, categories, labels, and your own password inside the new control plane.",
  },
  {
    title: "Sign In",
    href: "/login",
    eyebrow: "Authentication",
    description:
      "Access the OpsCenter with your credentials to manage tickets and view reports.",
  },
];

export default function Home() {
  return (
    <main className="min-h-screen bg-slate-950 px-4 py-6 text-slate-50 sm:px-6 lg:px-8">
      <div className="mx-auto flex min-h-[calc(100vh-3rem)] w-full max-w-6xl flex-col justify-center">
        <div className="overflow-hidden rounded-[2rem] border border-slate-800 bg-slate-900/70 shadow-2xl shadow-cyan-950/20">
          <div className="grid gap-0 lg:grid-cols-[1.2fr,0.8fr]">
            <section className="relative p-6 sm:p-8 lg:p-10">
              <div className="absolute inset-0 bg-[radial-gradient(circle_at_top_left,_rgba(34,211,238,0.12),_transparent_35%),radial-gradient(circle_at_bottom_right,_rgba(14,165,233,0.08),_transparent_32%)]" />
              <div className="relative">
                <p className="text-xs font-medium uppercase tracking-[0.35em] text-cyan-300">
                  Aether Ops
                </p>
                <h1 className="mt-4 max-w-2xl text-4xl font-semibold tracking-tight text-white sm:text-5xl">
                  One front door for ranked tickets, incident context, and report exports.
                </h1>
                <p className="mt-4 max-w-2xl text-sm leading-6 text-slate-300 sm:text-base">
                  Start where you need to work, then move into the command center or the board view without losing the thread. The layout is built to stay readable on mobile and spacious on larger screens.
                </p>

                <div className="mt-8 flex flex-wrap gap-3">
                  <Link
                    href="/command-center"
                    className="inline-flex items-center justify-center rounded-full bg-cyan-400 px-5 py-3 text-sm font-medium text-slate-950 transition hover:bg-cyan-300"
                  >
                    Open Command Center
                  </Link>
                  <Link
                    href="/tickets/new"
                    className="inline-flex items-center justify-center rounded-full border border-slate-700 px-5 py-3 text-sm font-medium text-slate-100 transition hover:border-slate-500 hover:bg-slate-800"
                  >
                    Create Ticket
                  </Link>
                </div>
              </div>
            </section>

            <aside className="border-t border-slate-800 bg-slate-950/60 p-6 sm:p-8 lg:border-l lg:border-t-0 lg:p-10">
              <div className="space-y-4">
                {entrances.map((entrance) => (
                  <Link
                    key={entrance.title}
                    href={entrance.href}
                    className="group block rounded-2xl border border-slate-800 bg-slate-900/90 p-4 transition hover:border-cyan-400/50 hover:bg-slate-800"
                  >
                    <div className="flex items-start justify-between gap-4">
                      <div>
                        <p className="text-[11px] uppercase tracking-[0.25em] text-slate-400">
                          {entrance.eyebrow}
                        </p>
                        <h2 className="mt-1 text-lg font-medium text-white">{entrance.title}</h2>
                      </div>
                      <span className="mt-1 text-cyan-300 transition group-hover:translate-x-0.5">
                        →
                      </span>
                    </div>
                    <p className="mt-3 text-sm leading-6 text-slate-300">{entrance.description}</p>
                  </Link>
                ))}
              </div>
            </aside>
          </div>
        </div>
      </div>
    </main>
  );
}
