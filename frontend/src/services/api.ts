// Empty string = relative requests against the current origin. In local dev
// that means Vite's dev-server proxy (see vite.config.ts) forwards /api/*
// to the backend, keeping frontend+backend same-origin so the session
// cookie works as plain SameSite=Lax. In production, set VITE_API_URL to
// the deployed backend's URL (see .env.frontend.example / DEPLOY_RENDER.md)
// — that's a genuinely cross-origin call, which is why the backend switches
// COOKIE_SAMESITE=none + COOKIE_SECURE=true in production.
const API_URL = import.meta.env.VITE_API_URL || "";

export class ApiError extends Error {
  status: number;
  constructor(status: number, message: string) {
    super(message);
    this.status = status;
  }
}

async function request<T>(path: string, options: RequestInit = {}): Promise<T> {
  const res = await fetch(`${API_URL}${path}`, {
    ...options,
    credentials: "include",
    headers: {
      ...(options.body && !(options.body instanceof FormData) ? { "Content-Type": "application/json" } : {}),
      ...options.headers,
    },
  });

  if (!res.ok) {
    let detail = "Something went wrong. Please try again.";
    try {
      const data = await res.json();
      detail = data.detail || detail;
    } catch {
      /* non-JSON error body */
    }
    throw new ApiError(res.status, detail);
  }

  if (res.status === 204) return undefined as T;

  const contentType = res.headers.get("content-type") || "";
  if (contentType.includes("application/json")) {
    return (await res.json()) as T;
  }
  return (await res.blob()) as unknown as T;
}

export const api = {
  get: <T>(path: string) => request<T>(path, { method: "GET" }),
  post: <T>(path: string, body?: unknown) =>
    request<T>(path, { method: "POST", body: body !== undefined ? JSON.stringify(body) : undefined }),
  put: <T>(path: string, body?: unknown) =>
    request<T>(path, { method: "PUT", body: body !== undefined ? JSON.stringify(body) : undefined }),
  patch: <T>(path: string, body?: unknown) =>
    request<T>(path, { method: "PATCH", body: body !== undefined ? JSON.stringify(body) : undefined }),
  delete: <T>(path: string) => request<T>(path, { method: "DELETE" }),
  blob: async (path: string): Promise<Blob> => {
    const res = await fetch(`${API_URL}${path}`, { credentials: "include" });
    if (!res.ok) throw new ApiError(res.status, "Failed to download file.");
    return res.blob();
  },
};

export { API_URL };
