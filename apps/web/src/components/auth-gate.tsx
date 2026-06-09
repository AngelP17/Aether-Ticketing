"use client";

import { useEffect, useRef, useState, type ReactNode } from "react";
import { usePathname, useRouter } from "next/navigation";

import {
  clearStoredSession,
  getAuthRedirectPath,
  isProtectedPath,
  readAccessToken,
  validateAccessToken,
} from "@/lib/auth";

function AuthLoadingShell() {
  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center bg-zinc-950/95 px-4 text-center text-sm text-zinc-400"
      aria-live="polite"
      aria-busy="true"
    >
      <div className="flex flex-col items-center gap-3 rounded-2xl border border-zinc-800 bg-black/40 px-5 py-4 shadow-2xl">
        <div className="h-7 w-7 animate-spin rounded-full border-2 border-amber-500/25 border-t-amber-400" />
        <div>Checking session...</div>
      </div>
    </div>
  );
}

function AuthErrorShell({
  message,
  onRetry,
}: {
  message: string;
  onRetry: () => void;
}) {
  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center bg-zinc-950/95 px-4 text-center"
      aria-live="polite"
    >
      <div className="max-w-md rounded-2xl border border-red-500/20 bg-black/60 px-6 py-5 shadow-2xl">
        <div className="text-base font-semibold text-red-100">
          Session verification failed
        </div>
        <p className="mt-3 text-sm leading-6 text-zinc-300">{message}</p>
        <button
          type="button"
          onClick={onRetry}
          className="mt-5 inline-flex items-center justify-center rounded-full border border-red-400/20 bg-red-500/10 px-4 py-2 text-sm font-medium text-red-100 transition hover:bg-red-500/20"
        >
          Retry
        </button>
      </div>
    </div>
  );
}

export function AuthGate({ children }: { children: ReactNode }) {
  const pathname = usePathname();
  const router = useRouter();
  const requiresAuthCheck = pathname === "/login" || isProtectedPath(pathname);
  const [settledPathname, setSettledPathname] = useState<string | null>(
    requiresAuthCheck ? null : pathname,
  );
  const [validationError, setValidationError] = useState<string | null>(null);
  const [retryNonce, setRetryNonce] = useState(0);
  const verifyingRef = useRef(false);

  useEffect(() => {
    if (!requiresAuthCheck) {
      setSettledPathname(pathname);
      setValidationError(null);
      return;
    }

    let active = true;
    const controller = new AbortController();

    setSettledPathname(null);
    setValidationError(null);
    verifyingRef.current = true;

    const finish = (nextPath: string | null) => {
      if (!active) {
        return;
      }

      verifyingRef.current = false;
      setSettledPathname(nextPath);
    };

    const verifySession = async () => {
      const token = readAccessToken();

      if (!token) {
        if (isProtectedPath(pathname)) {
          router.replace("/login");
          finish(null);
          return;
        }

        finish(pathname);
        return;
      }

      try {
        const result = await validateAccessToken(token, controller.signal);
        if (!active) {
          return;
        }

        if (result.status === "valid") {
          const redirectTo = getAuthRedirectPath(pathname, true);
          if (redirectTo) {
            router.replace(redirectTo);
            finish(null);
            return;
          }

          finish(pathname);
          return;
        }

        if (result.status === "invalid") {
          clearStoredSession();
          if (isProtectedPath(pathname)) {
            router.replace("/login");
            finish(null);
            return;
          }

          finish(pathname);
          return;
        }

        if (isProtectedPath(pathname)) {
          setValidationError(result.message);
          finish(null);
          return;
        }

        finish(pathname);
      } catch {
        if (!active) return;
        if (isProtectedPath(pathname)) {
          setValidationError("Session verification failed unexpectedly");
          finish(null);
          return;
        }
        finish(pathname);
      }
    };

    void verifySession();

    return () => {
      active = false;
      controller.abort();
      verifyingRef.current = false;
    };
  }, [pathname, requiresAuthCheck, retryNonce, router]);

  if (!requiresAuthCheck) {
    return <>{children}</>;
  }

  if (validationError && isProtectedPath(pathname)) {
    return (
      <AuthErrorShell
        message={validationError}
        onRetry={() => setRetryNonce((value) => value + 1)}
      />
    );
  }

  if (settledPathname !== pathname) {
    return <AuthLoadingShell />;
  }

  return <>{children}</>;
}
