"use client";

import Image from "next/image";
import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import {
  useCallback,
  useEffect,
  useState,
  type ComponentType,
  type ReactNode,
} from "react";
import {
  Activity,
  ChevronRight,
  Columns3,
  Download,
  FileSpreadsheet,
  Gauge,
  LogOut,
  MoreHorizontal,
  Plus,
  Shield,
  ShieldAlert,
  Ticket as TicketIcon,
  X,
} from "lucide-react";

import { NotificationBell, useToast } from "@/components/notifications";
import { clearStoredSession, readStoredUser, type AuthUser } from "@/lib/auth";

type RailItem =
  | {
      kind: "link";
      href: string;
      label: string;
      icon: ComponentType<{ className?: string }>;
    }
  | {
      kind: "action";
      onClick: () => void;
      label: string;
      icon: ComponentType<{ className?: string }>;
    };

type SheetItem =
  | { kind: "link"; href: string; label: string; icon: ComponentType<{ className?: string }>; tone?: "default" | "amber" | "cyan" | "rose" | "zinc" }
  | { kind: "action"; onClick: () => void; label: string; icon: ComponentType<{ className?: string }>; tone?: "default" | "amber" | "cyan" | "rose" | "zinc" };

type StatusPill = {
  kind: "ready" | "loading" | "error";
  label: string;
};

const PRIMARY_NAV_LINKS: Array<Extract<RailItem, { kind: "link" }>> = [
  { kind: "link", href: "/command-center", label: "Command Center", icon: Gauge },
  { kind: "link", href: "/board", label: "Workflow Tracking", icon: Columns3 },
  { kind: "link", href: "/incidents", label: "Incidents", icon: ShieldAlert },
  { kind: "link", href: "/reports", label: "Reports", icon: FileSpreadsheet },
  { kind: "link", href: "/admin", label: "Admin", icon: Shield },
];

type OpsShellProps = {
  children: ReactNode;
  eyebrow?: string;
  title?: string;
  subtitle?: string;
  statusPill?: StatusPill;
  lastSyncSeconds?: number;
  warnings?: string[];
  search?: {
    value: string;
    onChange: (value: string) => void;
    placeholder?: string;
  };
  railItems?: RailItem[];
  sheetItems?: SheetItem[];
  headerActions?: ReactNode;
  exportButton?: {
    isExporting: boolean;
    onClick: () => void;
    label?: string;
  };
  showNotificationBell?: boolean;
  onLogout?: () => void;
  isSigningOut?: boolean;
  className?: string;
};

const toneClass: Record<NonNullable<SheetItem["tone"]>, string> = {
  default: "text-zinc-100",
  amber: "text-amber-300",
  cyan: "text-cyan-300",
  rose: "text-rose-300",
  zinc: "text-zinc-300",
};

function defaultRailItems(): RailItem[] {
  return PRIMARY_NAV_LINKS;
}

function defaultSheetItems(onExport: (() => void) | undefined, isExporting: boolean): SheetItem[] {
  const items: SheetItem[] = [
    { kind: "link", href: "/tickets/new", label: "New ticket", icon: Plus, tone: "amber" },
    { kind: "link", href: "/command-center", label: "Queue overview", icon: TicketIcon },
    { kind: "link", href: "/incidents", label: "Incident intelligence", icon: ShieldAlert, tone: "rose" },
    { kind: "link", href: "/board", label: "Workflow board", icon: Columns3 },
    { kind: "link", href: "/reports", label: "Reports", icon: Activity, tone: "cyan" },
  ];
  if (onExport) {
    items.push({
      kind: "action",
      onClick: onExport,
      label: isExporting ? "Preparing export..." : "Export workbook",
      icon: Download,
      tone: "amber",
    });
  }
  return items;
}

function formatSync(seconds: number) {
  if (seconds < 60) {
    return `${seconds}s ago`;
  }
  const minutes = Math.floor(seconds / 60);
  if (minutes < 60) {
    return `${minutes}m ago`;
  }
  const hours = Math.floor(minutes / 60);
  return `${hours}h ago`;
}

function userInitials(user: AuthUser | null) {
  if (!user) {
    return "OP";
  }
  const source = user.display_name || user.username || "";
  const parts = source.trim().split(/\s+/).filter(Boolean);
  if (parts.length === 0) {
    return (user.username || "OP").slice(0, 2).toUpperCase();
  }
  const first = parts[0]?.[0] ?? "";
  const second = parts[1]?.[0] ?? "";
  return `${first}${second}`.toUpperCase() || (user.username || "OP").slice(0, 2).toUpperCase();
}

function OpsStatusPill({ pill }: { pill?: StatusPill }) {
  if (!pill) {
    return null;
  }
  const palette =
    pill.kind === "ready"
      ? "border-emerald-500/20 bg-emerald-500/8 text-emerald-200"
      : pill.kind === "loading"
        ? "border-cyan-500/20 bg-cyan-500/8 text-cyan-100"
        : "border-rose-500/20 bg-rose-500/10 text-rose-100";
  const dotColor =
    pill.kind === "ready" ? "#22c55e" : pill.kind === "loading" ? "#22d3ee" : "#fb7185";

  return (
    <div
      className={`inline-flex items-center gap-2 rounded-full border px-3 py-1.5 text-[11px] ${palette}`}
    >
      <span className="h-2 w-2 rounded-full" style={{ backgroundColor: dotColor }} />
      {pill.label}
    </div>
  );
}

function routeTitle(pathname: string | null) {
  if (!pathname) {
    return "OpsCenter";
  }
  if (pathname === "/command-center") {
    return "Command Center";
  }
  if (pathname === "/board") {
    return "Workflow Tracking";
  }
  if (pathname === "/incidents") {
    return "Incident Intelligence";
  }
  if (pathname.startsWith("/incidents/")) {
    return "Incident Detail";
  }
  if (pathname === "/reports") {
    return "Reports & Export";
  }
  if (pathname === "/admin") {
    return "Administration";
  }
  if (pathname === "/tickets/new") {
    return "New Ticket";
  }
  if (pathname.startsWith("/tickets/")) {
    return "Ticket Detail";
  }
  if (pathname.startsWith("/replay/")) {
    return "Replay & Audit";
  }
  return "OpsCenter";
}

export function OpsShell({
  children,
  eyebrow,
  title,
  subtitle,
  statusPill,
  lastSyncSeconds,
  warnings = [],
  search,
  railItems,
  sheetItems,
  headerActions,
  exportButton,
  showNotificationBell = false,
  onLogout,
  isSigningOut = false,
  className,
}: OpsShellProps) {
  const router = useRouter();
  const pathname = usePathname();
  const toast = useToast();
  const [moreOpen, setMoreOpen] = useState(false);
  const [user, setUser] = useState<AuthUser | null>(null);

  useEffect(() => {
    setUser(readStoredUser());
  }, []);

  const handleLogout = useCallback(async () => {
    if (onLogout) {
      onLogout();
      return;
    }
    try {
      await fetch("/api/auth/logout", { method: "POST", cache: "no-store" }).catch(() => null);
    } finally {
      clearStoredSession();
      toast.success("Signed out successfully");
      router.replace("/login");
    }
  }, [onLogout, router, toast]);

  const rail = railItems ?? defaultRailItems();
  const navigationLinks = PRIMARY_NAV_LINKS;
  const currentTitle = title ?? routeTitle(pathname);
  const sheet =
    sheetItems ??
    defaultSheetItems(exportButton?.onClick, Boolean(exportButton?.isExporting));

  return (
    <div className={`ops-grid relative min-h-[100dvh] overflow-hidden bg-[var(--bg-deep)] ${className ?? ""}`}>
      <div className="ops-cockpit-aura" aria-hidden="true" />
      <div className="scan-line" />

      {exportButton ? (
        <button
          type="button"
          onClick={exportButton.onClick}
          disabled={exportButton.isExporting}
          className="ops-floating-export inline-flex h-12 w-12 items-center justify-center rounded-2xl border border-amber-400/20 bg-amber-500 text-black shadow-[0_16px_36px_rgba(245,158,11,0.28)] transition hover:scale-[1.03] hover:bg-amber-400 disabled:cursor-not-allowed disabled:opacity-70"
          title={exportButton.label ?? "Export workbook"}
          aria-label={
            exportButton.isExporting
              ? "Preparing workbook export"
              : exportButton.label ?? "Export workbook"
          }
        >
          <Download className="h-4 w-4" />
        </button>
      ) : null}

      <div className="relative z-10 grid min-h-[100dvh] lg:grid-cols-[260px,minmax(0,1fr)]">
        <aside className="ops-rail ops-shell z-20 hidden border-r border-zinc-800/50 px-4 py-4 lg:sticky lg:top-0 lg:flex lg:h-[100dvh] lg:flex-col">
          <Link
            href="/command-center"
            className="flex items-center gap-3 rounded-2xl border border-amber-400/20 bg-amber-500/10 px-3 py-3 text-amber-100 shadow-[0_0_36px_rgba(245,158,11,0.12)] transition hover:border-amber-200/40"
            aria-label="Aether OpsCenter"
          >
            <span className="flex h-10 w-10 shrink-0 items-center justify-center rounded-xl bg-black/40 p-1">
              <Image
                src="/logo.png"
                alt=""
                width={32}
                height={32}
                priority
                unoptimized
                className="h-8 w-8 rounded-lg"
              />
            </span>
            <span className="min-w-0">
              <span className="mono-data block text-[10px] uppercase tracking-[0.28em] text-amber-300">
                Aether
              </span>
              <span className="block truncate text-sm font-semibold text-white">OpsCenter</span>
            </span>
          </Link>

          <nav className="mt-6 flex flex-1 flex-col gap-2" aria-label="Primary navigation">
            {rail.map((item) => {
              const Icon = item.icon;
              const isActive =
                item.kind === "link" &&
                (pathname === item.href ||
                  (item.href !== "/command-center" && pathname.startsWith(`${item.href}/`)) ||
                  (item.href === "/command-center" && pathname === "/command-center"));
              const className = `group flex items-center gap-3 rounded-xl border px-4 py-3 text-sm transition ${
                isActive
                  ? "border-amber-400/25 bg-amber-500/10 text-amber-100"
                  : "border-transparent text-zinc-500 hover:border-zinc-700/60 hover:bg-zinc-900/60 hover:text-zinc-100"
              }`;

              if (item.kind === "link") {
                return (
                  <Link key={item.label} href={item.href} className={className}>
                    <Icon className="h-4 w-4 shrink-0" />
                    <span className="ops-rail-label text-sm font-medium">{item.label}</span>
                  </Link>
                );
              }
              return (
                <button
                  key={item.label}
                  type="button"
                  onClick={item.onClick}
                  className={className}
                >
                  <Icon className="h-4 w-4 shrink-0" />
                  <span className="ops-rail-label text-sm font-medium">{item.label}</span>
                </button>
              );
            })}
          </nav>

          <div className="px-2 pb-2 pt-6">
            <div
              className="flex items-center gap-3 rounded-2xl border border-zinc-800 bg-black/20 px-3 py-3"
              aria-label={user?.display_name || user?.username || "Operator"}
            >
              <span className="flex h-10 w-10 shrink-0 items-center justify-center rounded-full bg-gradient-to-br from-amber-400 to-orange-600 text-xs font-bold text-black">
                {userInitials(user)}
              </span>
              <span className="min-w-0">
                <span className="block truncate text-sm font-semibold text-zinc-100">
                  {user?.display_name || user?.username || "Operator"}
                </span>
                <span className="mono-data text-[10px] uppercase tracking-[0.2em] text-zinc-500">
                  Active session
                </span>
              </span>
            </div>
          </div>
        </aside>

        <main className="ops-safe-bottom px-4 py-4 sm:px-6 lg:px-8 lg:py-6">
          <div className="ops-topbar mb-5 rounded-[28px] px-4 py-4 sm:px-6 sm:py-5">
            <div className="flex flex-col gap-4 xl:flex-row xl:items-start xl:justify-between">
              <div className="min-w-0">
                <div className="flex flex-wrap items-center gap-3">
                  <p className="mono-data text-[10px] uppercase tracking-[0.32em] text-amber-300">
                    {eyebrow ?? "Aether OpsCenter"}
                  </p>
                  <OpsStatusPill pill={statusPill} />
                  {lastSyncSeconds !== undefined ? (
                    <span className="mono-data rounded-full border border-zinc-800/70 bg-black/20 px-3 py-1.5 text-[10px] uppercase tracking-[0.18em] text-zinc-500">
                      {statusPill?.kind === "ready"
                        ? `Synced ${formatSync(lastSyncSeconds)}`
                        : statusPill?.kind === "loading"
                          ? "Sync pending"
                          : "Sync offline"}
                    </span>
                  ) : null}
                </div>
                <h1 className="mt-3 truncate text-2xl font-semibold tracking-tight text-white sm:text-3xl">
                  {currentTitle}
                </h1>
                {subtitle ? (
                  <p className="mt-2 max-w-3xl text-sm leading-6 text-zinc-400">{subtitle}</p>
                ) : null}
              </div>

              {headerActions ? (
                <div className="flex flex-wrap gap-2">{headerActions}</div>
              ) : null}
            </div>

            {(warnings.length > 0 || search) && (
              <div className="mt-4 flex flex-col gap-3 lg:flex-row lg:items-center lg:justify-between">
                  <div className="flex flex-wrap items-center gap-3 text-sm text-zinc-500">
                    {warnings.map((warning) => (
                      <div
                        key={warning}
                        className="inline-flex items-center gap-2 rounded-full border border-amber-400/20 bg-amber-500/10 px-3 py-2 text-amber-100"
                      >
                        <ShieldAlert className="h-3.5 w-3.5" />
                        <span>{warning}</span>
                      </div>
                    ))}
                  </div>

                  {search ? (
                    <label className="relative block w-full max-w-md">
                      <input
                        value={search.value}
                        onChange={(event) => search.onChange(event.target.value)}
                        placeholder={search.placeholder ?? "Search"}
                        className="w-full rounded-2xl border border-zinc-800 bg-black/20 px-4 py-2.5 text-sm text-zinc-100 outline-none transition placeholder:text-zinc-600 focus:border-amber-400/30"
                      />
                    </label>
                  ) : null}
              </div>
            )}

            <nav className="mt-4 flex gap-2 overflow-x-auto pb-1" aria-label="Route shortcuts">
              {navigationLinks.map((item) => {
                const Icon = item.icon;
                const isActive =
                  pathname === item.href ||
                  (item.href !== "/command-center" && pathname.startsWith(`${item.href}/`));
                return (
                  <Link
                    key={item.href}
                    href={item.href}
                    className={`inline-flex shrink-0 items-center gap-2 rounded-full border px-3 py-2 text-xs font-medium transition ${
                      isActive
                        ? "border-amber-400/30 bg-amber-500/12 text-amber-100"
                        : "border-zinc-800/80 bg-black/20 text-zinc-400 hover:border-zinc-700 hover:text-zinc-100"
                    }`}
                    aria-current={isActive ? "page" : undefined}
                  >
                    <Icon className="h-3.5 w-3.5" aria-hidden="true" />
                    {item.label}
                  </Link>
                );
              })}
              <Link
                href="/tickets/new"
                className="inline-flex shrink-0 items-center gap-2 rounded-full border border-amber-400/25 bg-amber-500 px-3 py-2 text-xs font-semibold text-black transition hover:bg-amber-400"
              >
                <Plus className="h-3.5 w-3.5" aria-hidden="true" />
                New Ticket
              </Link>
            </nav>
          </div>

          {children}
        </main>
      </div>

      <nav className="ops-mobile-nav lg:hidden" aria-label="Mobile operations navigation">
        {navigationLinks.slice(0, 4).map((item) => {
          const Icon = item.icon;
          const isActive =
            pathname === item.href ||
            (item.href !== "/command-center" && pathname.startsWith(`${item.href}/`)) ||
            (item.href === "/command-center" && pathname === "/command-center");
          return (
            <Link
              key={item.href}
              href={item.href}
              className={`ops-mobile-item ${isActive ? "active" : ""}`}
              aria-current={isActive ? "page" : undefined}
            >
              <Icon className="h-5 w-5" aria-hidden="true" />
              <span>{item.label}</span>
            </Link>
          );
        })}
        <button
          type="button"
          className="ops-mobile-item"
          aria-expanded={moreOpen}
          aria-controls="ops-mobile-sheet"
          onClick={() => setMoreOpen(true)}
        >
          <MoreHorizontal className="h-5 w-5" aria-hidden="true" />
          <span>More</span>
        </button>
        {showNotificationBell ? (
          <span className="ops-mobile-item">
            <NotificationBell />
          </span>
        ) : null}
      </nav>

      <div
        id="ops-mobile-sheet"
        className="ops-mobile-sheet lg:hidden"
        data-open={moreOpen ? "true" : "false"}
        aria-hidden={!moreOpen}
      >
        <button
          type="button"
          aria-label="Close sheet"
          className="absolute inset-0 bg-black/60"
          onClick={() => setMoreOpen(false)}
        />
        <div className="ops-mobile-sheet-panel px-4 pb-[calc(1.5rem+env(safe-area-inset-bottom))] pt-3">
          <div className="mx-auto mb-4 h-1.5 w-12 rounded-full bg-zinc-700" />
          <div className="mb-2 flex items-center justify-between px-1">
            <p className="mono-data text-[10px] uppercase tracking-[0.28em] text-zinc-500">
              Aether OpsCenter
            </p>
            <button
              type="button"
              onClick={() => setMoreOpen(false)}
              className="rounded-full p-1 text-zinc-500 transition hover:text-zinc-200"
              aria-label="Close"
            >
              <X className="h-4 w-4" />
            </button>
          </div>
          <div className="space-y-2">
            {sheet.map((item, index) => {
              const Icon = item.icon;
              const tone = item.tone ?? "default";
              const content = (
                <>
                  <span className="flex items-center gap-3">
                    <Icon className={`h-4 w-4 ${toneClass[tone]}`} aria-hidden="true" />
                    {item.label}
                  </span>
                  <ChevronRight className="h-4 w-4 text-zinc-600" aria-hidden="true" />
                </>
              );
              if (item.kind === "link") {
                return (
                  <Link
                    key={`${item.label}-${index}`}
                    href={item.href}
                    onClick={() => setMoreOpen(false)}
                    className="flex items-center justify-between rounded-2xl border border-zinc-800/70 bg-black/20 px-4 py-4 text-sm text-zinc-100 transition hover:border-zinc-700"
                  >
                    {content}
                  </Link>
                );
              }
              return (
                <button
                  key={`${item.label}-${index}`}
                  type="button"
                  onClick={() => {
                    setMoreOpen(false);
                    item.onClick();
                  }}
                  className="flex w-full items-center justify-between rounded-2xl border border-zinc-800/70 bg-black/20 px-4 py-4 text-left text-sm text-zinc-100 transition hover:border-zinc-700"
                >
                  {content}
                </button>
              );
            })}
            <button
              type="button"
              onClick={handleLogout}
              disabled={isSigningOut}
              className="flex w-full items-center justify-between rounded-2xl border border-rose-500/20 bg-rose-500/10 px-4 py-4 text-left text-sm text-rose-100 transition hover:border-rose-400/30 disabled:cursor-not-allowed disabled:opacity-70"
            >
              <span className="flex items-center gap-3">
                <LogOut className="h-4 w-4 text-rose-300" aria-hidden="true" />
                {isSigningOut ? "Signing out..." : "Sign out"}
              </span>
              <ChevronRight className="h-4 w-4 text-rose-300/60" aria-hidden="true" />
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}
