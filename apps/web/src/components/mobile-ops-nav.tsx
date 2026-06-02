"use client";

import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import { useState } from "react";
import {
  Columns3,
  FileBarChart,
  Gauge,
  LogOut,
  MoreHorizontal,
  Plus,
  Shield,
  Ticket,
} from "lucide-react";

import { clearStoredSession, isProtectedPath } from "@/lib/auth";

const primaryLinks = [
  { href: "/command-center", label: "Center", icon: Gauge },
  { href: "/board", label: "Board", icon: Columns3 },
  { href: "/reports", label: "Reports", icon: FileBarChart },
  { href: "/admin", label: "Admin", icon: Shield },
];

function isActive(pathname: string, href: string) {
  if (href === "/command-center") {
    return pathname === href;
  }

  return pathname === href || pathname.startsWith(`${href}/`);
}

export function MobileOpsNav() {
  const pathname = usePathname();
  const router = useRouter();
  const [isOpen, setIsOpen] = useState(false);

  if (!isProtectedPath(pathname) || pathname === "/command-center") {
    return null;
  }

  const closeSheet = () => setIsOpen(false);
  const logout = () => {
    clearStoredSession();
    router.replace("/login");
  };

  return (
    <>
      <nav className="ops-mobile-nav lg:hidden" aria-label="Mobile operations navigation">
        {primaryLinks.slice(0, 3).map((item) => {
          const Icon = item.icon;
          return (
            <Link
              key={item.href}
              href={item.href}
              className={`ops-mobile-item ${pathname && isActive(pathname, item.href) ? "active" : ""}`}
            >
              <Icon className="h-5 w-5" aria-hidden="true" />
              <span>{item.label}</span>
            </Link>
          );
        })}
        <button
          type="button"
          className="ops-mobile-item"
          aria-expanded={isOpen}
          aria-controls="mobile-ops-sheet"
          onClick={() => setIsOpen(true)}
        >
          <MoreHorizontal className="h-5 w-5" aria-hidden="true" />
          <span>More</span>
        </button>
      </nav>

      <div
        id="mobile-ops-sheet"
        className="ops-mobile-sheet lg:hidden"
        data-open={isOpen ? "true" : "false"}
        aria-hidden={!isOpen}
      >
        <button
          type="button"
          className="absolute inset-0 bg-black/55"
          aria-label="Close mobile navigation"
          onClick={closeSheet}
        />
        <div className="ops-mobile-sheet-panel px-4 pb-[calc(1rem+env(safe-area-inset-bottom))] pt-4">
          <div className="mx-auto mb-4 h-1 w-10 rounded-full bg-zinc-700" />
          <div className="grid gap-2">
            <Link
              href="/tickets/new"
              className="flex items-center justify-between rounded-2xl border border-amber-500/25 bg-amber-500/10 px-4 py-3 text-sm font-semibold text-amber-100"
              onClick={closeSheet}
            >
              <span className="flex items-center gap-3">
                <Plus className="h-4 w-4" aria-hidden="true" />
                New ticket
              </span>
              <span className="mono-data text-[10px] uppercase tracking-[0.24em] text-amber-300">Create</span>
            </Link>
            <Link
              href="/command-center"
              className="flex items-center justify-between rounded-2xl border border-white/10 bg-white/[0.04] px-4 py-3 text-sm text-zinc-200"
              onClick={closeSheet}
            >
              <span className="flex items-center gap-3">
                <Ticket className="h-4 w-4 text-zinc-400" aria-hidden="true" />
                Queue overview
              </span>
              <span className="mono-data text-[10px] uppercase tracking-[0.24em] text-zinc-500">Open</span>
            </Link>
            {primaryLinks.map((item) => {
              const Icon = item.icon;
              return (
                <Link
                  key={item.href}
                  href={item.href}
                  className={`flex items-center gap-3 rounded-2xl border px-4 py-3 text-sm transition ${
                    pathname && isActive(pathname, item.href)
                      ? "border-amber-500/25 bg-amber-500/10 text-amber-100"
                      : "border-white/10 bg-white/[0.04] text-zinc-200"
                  }`}
                  onClick={closeSheet}
                >
                  <Icon className="h-4 w-4 text-current" aria-hidden="true" />
                  {item.label}
                </Link>
              );
            })}
            <button
              type="button"
              className="mt-2 flex items-center gap-3 rounded-2xl border border-rose-500/20 bg-rose-500/10 px-4 py-3 text-left text-sm text-rose-100"
              onClick={logout}
            >
              <LogOut className="h-4 w-4" aria-hidden="true" />
              Sign out
            </button>
          </div>
        </div>
      </div>
    </>
  );
}
