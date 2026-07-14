const API_BASE = import.meta.env.VITE_API_URL || "http://localhost:8000";

/** Error thrown for non-2xx responses, carrying the HTTP status and the
 * backend's `detail` message so pages can branch on status instead of
 * pattern-matching message strings. */
export class ApiError extends Error {
  status: number;

  constructor(status: number, detail?: string) {
    super(detail || `Request failed (${status})`);
    this.name = "ApiError";
    this.status = status;
  }
}

export function isApiError(err: unknown, status?: number): err is ApiError {
  if (!(err instanceof ApiError)) return false;
  return status === undefined || err.status === status;
}

async function request<T>(path: string, options: RequestInit = {}): Promise<T> {
  const headers: Record<string, string> = {
    ...(options.headers as Record<string, string>),
  };
  if (options.body && typeof options.body === "string") {
    headers["Content-Type"] = headers["Content-Type"] || "application/json";
  }

  const res = await fetch(`${API_BASE}${path}`, {
    ...options,
    credentials: "include",
    headers,
  });
  if (!res.ok) {
    let detail: string | undefined;
    try {
      const body = await res.json();
      if (typeof body?.detail === "string") detail = body.detail;
    } catch {
      // Non-JSON error body; fall back to the generic message.
    }
    throw new ApiError(res.status, detail);
  }
  return res.json();
}

export const api = {
  get: <T>(path: string) => request<T>(path),
  post: <T>(path: string, body?: unknown) =>
    request<T>(path, { method: "POST", body: body ? JSON.stringify(body) : undefined }),
};

/** Clears HttpOnly session cookie on the server. */
export async function logoutSession(): Promise<void> {
  await fetch(`${API_BASE}/auth/logout`, {
    method: "POST",
    credentials: "include",
  });
}

export function getGoogleLoginUrl(): string {
  return `${API_BASE}/auth/google/login`;
}

/** Only allow https avatars from the browser (mitigate mixed content / odd schemes). */
export function safeAvatarUrl(url: string | null | undefined): string | null {
  if (!url) return null;
  try {
    const u = new URL(url);
    if (u.protocol !== "https:") return null;
    return url;
  } catch {
    return null;
  }
}
