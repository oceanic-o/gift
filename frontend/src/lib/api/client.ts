/**
 * src/lib/api/client.ts
 * Central fetch wrapper. All API modules import from here.
 */

const BASE_URL =
  (import.meta as any).env?.VITE_API_BASE_URL ?? "/api/v1";

// ── Token helpers ────────────────────────────────────────────────────────────
export const getToken = (): string | null =>
  (typeof window !== "undefined" && localStorage.getItem("access_token")) ||
  null;
export const setToken = (t: string) =>
  typeof window !== "undefined" && localStorage.setItem("access_token", t);
export const clearToken = () =>
  typeof window !== "undefined" && localStorage.removeItem("access_token");

export type RequestOptions = {
  auth?: boolean;
  timeoutMs?: number; // default 12000
  signal?: AbortSignal;
  retry?: {
    attempts?: number; // default 2 for GET only
    backoffMs?: number; // base backoff default 400ms
  };
  headers?: Record<string, string>;
};

function sleep(ms: number) {
  return new Promise((r) => setTimeout(r, ms));
}

async function safeJson(res: Response) {
  const text = await res.text();
  if (!text) return undefined;
  try {
    return JSON.parse(text);
  } catch {
    return text as any;
  }
}

function buildError(res: Response, data: any) {
  const detail = (data && (data.detail || data.message)) || res.statusText;
  const msg = Array.isArray(detail)
    ? detail.map((e: any) => e.msg || e.message || String(e)).join(", ")
    : String(detail || "Request failed");
  const err: any = new Error(msg);
  err.status = res.status;
  err.data = data;
  return err;
}

export async function request<T>(
  method: string,
  path: string,
  body?: unknown,
  opts: RequestOptions = {},
): Promise<T> {
  const auth = opts.auth ?? false;
  const timeoutMs = opts.timeoutMs ?? 12000;
  const retry = opts.retry ?? {};
  const retryAttempts = retry.attempts ?? (method === "GET" ? 2 : 0);
  const backoffBase = retry.backoffMs ?? 400;

  const headers: Record<string, string> = {
    Accept: "application/json",
    "Content-Type": "application/json",
    ...(opts.headers || {}),
  };
  if (auth) {
    const token = getToken();
    if (token) headers["Authorization"] = `Bearer ${token}`;
  }

  const url = `${BASE_URL}${path}`;

  let attempt = 0;
  // eslint-disable-next-line no-constant-condition
  while (true) {
    attempt++;

    const ctrl = new AbortController();
    const timeout = setTimeout(() => ctrl.abort(), timeoutMs);

    try {
      const res = await fetch(url, {
        method,
        headers,
        body: body != null ? JSON.stringify(body) : undefined,
        signal: opts.signal ? opts.signal : ctrl.signal,
      });

      const data = res.status === 204 ? undefined : await safeJson(res);

      if (!res.ok) {
        // Auto-logout on expired / invalid token
        if (res.status === 401 && auth) {
          clearToken();
          typeof window !== "undefined" && localStorage.removeItem("auth_user");
          typeof window !== "undefined" &&
            window.dispatchEvent(new Event("auth:logout"));
        }

        // Retry on transient errors for GET
        if (
          method === "GET" &&
          attempt <= 1 + retryAttempts &&
          (res.status === 502 || res.status === 503 || res.status === 504)
        ) {
          const delay =
            backoffBase * Math.pow(2, attempt - 1) + Math.random() * 100;
          await sleep(delay);
          continue;
        }

        throw buildError(res, data);
      }

      clearTimeout(timeout);
      return data as T;
    } catch (e: any) {
      clearTimeout(timeout);
      // Abort or explicit signal abort => propagate immediately
      if (e?.name === "AbortError") {
        throw e;
      }
      // Retry network errors for GET
      if (method === "GET" && attempt <= 1 + retryAttempts) {
        const delay =
          backoffBase * Math.pow(2, attempt - 1) + Math.random() * 100;
        await sleep(delay);
        continue;
      }
      // Build a normalized network error when not a Response error
      if (!e?.status) {
        const err: any = new Error(e?.message || "Network error");
        err.status = 0;
        err.data = null;
        throw err;
      }
      throw e;
    }
  }
}

export const api = {
  get: <T>(
    path: string,
    auth = false,
    options?: Omit<RequestOptions, "auth">,
  ) => request<T>("GET", path, undefined, { auth, ...(options || {}) }),
  post: <T>(
    path: string,
    body: unknown,
    auth = false,
    options?: Omit<RequestOptions, "auth">,
  ) => request<T>("POST", path, body, { auth, ...(options || {}) }),
  put: <T>(
    path: string,
    body: unknown,
    auth = false,
    options?: Omit<RequestOptions, "auth">,
  ) => request<T>("PUT", path, body, { auth, ...(options || {}) }),
  patch: <T>(
    path: string,
    body: unknown,
    auth = false,
    options?: Omit<RequestOptions, "auth">,
  ) => request<T>("PATCH", path, body, { auth, ...(options || {}) }),
  delete: <T>(
    path: string,
    auth = false,
    options?: Omit<RequestOptions, "auth">,
  ) => request<T>("DELETE", path, undefined, { auth, ...(options || {}) }),
};
