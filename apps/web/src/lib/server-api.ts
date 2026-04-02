import { headers } from "next/headers";

const DEFAULT_INTERNAL_API_URL = "http://127.0.0.1:8000";

export const getServerApiUrl = (path: string) => {
  const configuredBase =
    process.env.API_INTERNAL_URL ||
    process.env.NEXT_PUBLIC_API_URL ||
    DEFAULT_INTERNAL_API_URL;

  if (configuredBase.startsWith("http://") || configuredBase.startsWith("https://")) {
    return `${configuredBase.replace(/\/$/, "")}${path}`;
  }

  const requestHeaders = headers();
  const forwardedHost = requestHeaders.get("x-forwarded-host");
  const host = forwardedHost || requestHeaders.get("host");
  const protocol = requestHeaders.get("x-forwarded-proto") || "http";

  if (host) {
    return `${protocol}://${host}${configuredBase}${path}`;
  }

  return `${DEFAULT_INTERNAL_API_URL}${path}`;
};
