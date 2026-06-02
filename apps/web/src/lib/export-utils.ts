export function parseFilename(
  contentDisposition: string | null,
  fallback = "aether_report.xlsx",
) {
  if (!contentDisposition) {
    return fallback;
  }

  const encodedMatch = contentDisposition.match(
    /filename\*\s*=\s*UTF-8''([^;]+)/i,
  );
  if (encodedMatch?.[1]) {
    try {
      return decodeURIComponent(encodedMatch[1]);
    } catch {
      return encodedMatch[1].replace(/["']/g, "");
    }
  }

  const filenameMatch = contentDisposition.match(
    /filename\s*=\s*("?)([^";]+)\1/i,
  );
  if (filenameMatch?.[2]) {
    return filenameMatch[2];
  }

  return fallback;
}

export async function readExportError(response: Response) {
  const contentType = response.headers.get("content-type") || "";
  const body = await response.text().catch(() => "");

  if (contentType.includes("application/json")) {
    try {
      const data = JSON.parse(body) as unknown;
      if (data && typeof data === "object") {
        const record = data as Record<string, unknown>;
        if (typeof record.detail === "string") {
          return record.detail;
        }
        if (typeof record.message === "string") {
          return record.message;
        }
      }
    } catch {
    }
  }

  return body || `Request failed with status ${response.status}.`;
}
