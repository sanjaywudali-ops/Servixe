export class ApiError extends Error {
  status: number;
  constructor(status: number, message: string) {
    super(message);
    this.status = status;
  }
}

const BASE = "/api/v1";

function detailToMessage(detail: unknown): string {
  if (typeof detail === "string") return detail;
  if (Array.isArray(detail)) {
    return detail
      .map((d: { loc?: (string | number)[]; msg?: string }) => `${(d.loc ?? []).slice(1).join(".")}: ${d.msg ?? ""}`.replace(/^: /, ""))
      .join("; ");
  }
  return "Something went wrong. Please try again.";
}

type Opts = { method?: string; body?: unknown; form?: FormData };

export async function api<T = unknown>(path: string, opts: Opts = {}): Promise<T> {
  const headers: Record<string, string> = { "X-Requested-With": "Servixe" };
  let body: BodyInit | undefined;
  if (opts.form) body = opts.form;
  else if (opts.body !== undefined) {
    headers["Content-Type"] = "application/json";
    body = JSON.stringify(opts.body);
  }
  const res = await fetch(`${BASE}${path}`, {
    method: opts.method ?? (body ? "POST" : "GET"),
    headers,
    body,
    credentials: "same-origin",
    cache: "no-store",
  });
  if (!res.ok) {
    let detail: unknown;
    try { detail = (await res.json()).detail; } catch { /* ignore */ }
    throw new ApiError(res.status, detailToMessage(detail));
  }
  if (res.status === 204) return undefined as T;
  return (await res.json()) as T;
}

export const get = <T,>(p: string) => api<T>(p);
export const post = <T,>(p: string, body?: unknown) => api<T>(p, { method: "POST", body: body ?? {} });
export const patch = <T,>(p: string, body?: unknown) => api<T>(p, { method: "PATCH", body });
export const put = <T,>(p: string, body?: unknown) => api<T>(p, { method: "PUT", body });
export const del = <T,>(p: string) => api<T>(p, { method: "DELETE" });
