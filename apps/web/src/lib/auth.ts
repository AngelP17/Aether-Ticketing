export const ACCESS_TOKEN_KEY = "access_token";
export const USER_STORAGE_KEY = "user";

const PROTECTED_PATHS = new Set([
  "/command-center",
  "/board",
  "/reports",
]);

const PROTECTED_PREFIXES = ["/tickets/", "/incidents/", "/replay/"];

export function readAccessToken() {
  if (typeof window === "undefined") {
    return null;
  }

  try {
    return window.localStorage.getItem(ACCESS_TOKEN_KEY);
  } catch {
    return null;
  }
}

export function clearStoredSession() {
  if (typeof window === "undefined") {
    return;
  }

  try {
    window.localStorage.removeItem(ACCESS_TOKEN_KEY);
    window.localStorage.removeItem(USER_STORAGE_KEY);
  } catch {
    // Ignore storage failures; redirect flow can still proceed.
  }
}

export type AuthUser = {
  username: string;
  role: string;
  display_name: string;
};

export type SessionValidationResult =
  | { status: "valid"; user: AuthUser }
  | { status: "invalid"; user: null }
  | { status: "error"; user: null; message: string };

function getApiBaseUrl() {
  return (process.env.NEXT_PUBLIC_API_URL || "/api").replace(/\/$/, "");
}

function buildAuthUrl(pathname: string) {
  return `${getApiBaseUrl()}${pathname.startsWith("/") ? pathname : `/${pathname}`}`;
}

export async function validateAccessToken(
  token: string,
  signal?: AbortSignal,
): Promise<SessionValidationResult> {
  if (!token) {
    return { status: "invalid", user: null };
  }

  try {
    const response = await fetch(buildAuthUrl("/auth/me"), {
      method: "GET",
      headers: {
        Authorization: `Bearer ${token}`,
        Accept: "application/json",
      },
      cache: "no-store",
      signal,
    });

    if (response.status === 401 || response.status === 403) {
      return { status: "invalid", user: null };
    }

    if (!response.ok) {
      return {
        status: "error",
        user: null,
        message: `Session verification failed with status ${response.status}`,
      };
    }

    return {
      status: "valid",
      user: (await response.json()) as AuthUser,
    };
  } catch (error) {
    if (error instanceof DOMException && error.name === "AbortError") {
      return {
        status: "error",
        user: null,
        message: "Session verification was interrupted",
      };
    }

    return {
      status: "error",
      user: null,
      message:
        error instanceof Error ? error.message : "Session verification failed",
    };
  }
}

export function isLoginPath(pathname: string | null) {
  return pathname === "/login";
}

export function isProtectedPath(pathname: string | null) {
  if (!pathname) {
    return false;
  }

  if (PROTECTED_PATHS.has(pathname)) {
    return true;
  }

  return PROTECTED_PREFIXES.some((prefix) => pathname.startsWith(prefix));
}

export function getAuthRedirectPath(
  pathname: string | null,
  hasValidSession: boolean,
) {
  if (isLoginPath(pathname) && hasValidSession) {
    return "/command-center";
  }

  if (isProtectedPath(pathname) && !hasValidSession) {
    return "/login";
  }

  return null;
}
