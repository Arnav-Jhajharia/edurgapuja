"use client";

/**
 * The admin client.
 *
 * One API, four panels. Which panel a person sees is decided by the roles in
 * /admin/me — but every request is scoped server-side regardless, so choosing a
 * different view here shows a different screen, never somebody else's data.
 */

const TOKEN_KEY = "edp.admin.token";
const REFRESH_KEY = "edp.admin.refresh";

export type Me = {
  id: string;
  full_name: string;
  phone: string;
  roles: string[];
  pandals: { id: string; name: string; slug: string; sells_passes: boolean }[];
  organisations: { id: string; name: string; is_sub_sponsor: boolean }[];
};

export function getToken(): string | null {
  if (typeof window === "undefined") return null;
  return window.localStorage.getItem(TOKEN_KEY);
}

/**
 * Store the pair. The access token is short-lived by design; the refresh token
 * is what keeps an admin signed in across an evening, so both have to be kept.
 * Passing null for either clears it — signing out clears both.
 */
export function setToken(token: string | null, refresh?: string | null) {
  if (token) window.localStorage.setItem(TOKEN_KEY, token);
  else window.localStorage.removeItem(TOKEN_KEY);
  if (refresh !== undefined) {
    if (refresh) window.localStorage.setItem(REFRESH_KEY, refresh);
    else window.localStorage.removeItem(REFRESH_KEY);
  }
  if (token === null && refresh === undefined) window.localStorage.removeItem(REFRESH_KEY);
}

/**
 * Trade the refresh token for a new access token.
 *
 * Every 401 in a tab races every other 401 — a dashboard fires six requests at
 * once and all six expire together. One in-flight promise, shared, means one
 * refresh call and one rotation; six would burn five rotated tokens and, with
 * blacklisting on, sign the admin out.
 */
let refreshing: Promise<string | null> | null = null;

function refreshAccessToken(): Promise<string | null> {
  if (refreshing) return refreshing;
  const refresh = window.localStorage.getItem(REFRESH_KEY);
  if (!refresh) return Promise.resolve(null);

  refreshing = fetch("/api/auth/token/refresh", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ refresh }),
  })
    .then((r) => (r.ok ? r.json() : null))
    .then((body: any) => {
      if (!body?.access) {
        setToken(null, null);
        return null;
      }
      // ROTATE_REFRESH_TOKENS is on, so the response carries a new refresh
      // token too and the old one is now blacklisted. Keep the new one.
      setToken(body.access, body.refresh ?? undefined);
      return body.access as string;
    })
    .catch(() => null)
    .finally(() => {
      refreshing = null;
    });

  return refreshing;
}

export class ApiError extends Error {
  code: string;
  fields: Record<string, string>;
  constructor(code: string, message: string, fields: Record<string, string> = {}) {
    super(message);
    this.code = code;
    this.fields = fields;
  }
}

export async function api<T = any>(
  path: string,
  init: RequestInit & { json?: unknown } = {},
): Promise<T> {
  const { json, ...rest } = init;
  const body = json !== undefined ? JSON.stringify(json) : rest.body;

  const send = (token: string | null) => {
    const headers: Record<string, string> = { ...(rest.headers as any) };
    if (token) headers.Authorization = `Bearer ${token}`;
    if (json !== undefined) headers["Content-Type"] = "application/json";
    return fetch(`/api${path}`, { ...rest, headers, body });
  };

  let response = await send(getToken());

  // An expired access token is the ordinary case, not an error: refresh once
  // and replay the request. Only a failed refresh is a real sign-out.
  if (response.status === 401 && path !== "/auth/token/refresh") {
    const fresh = await refreshAccessToken();
    if (fresh) response = await send(fresh);
  }

  if (response.status === 204) return undefined as T;
  const payload = await response.json().catch(() => ({}));

  if (!response.ok) {
    const error = payload?.error ?? {};
    throw new ApiError(error.code ?? "error", error.message ?? "Something went wrong.",
                       error.fields ?? {});
  }
  return payload as T;
}

/** DRF paginates lists; unwrap them so callers always get an array. */
export async function list<T = any>(path: string): Promise<T[]> {
  const body = await api<any>(path);
  return body?.results ?? body ?? [];
}

export const rupees = (paise: number) =>
  `₹${(paise / 100).toLocaleString("en-IN", { maximumFractionDigits: 0 })}`;

export const PANEL_FOR: Record<string, string> = {
  super_admin: "Super Admin",
  pandal_admin: "Pandal Admin",
  sponsor_admin: "Sponsor Admin",
  sub_sponsor_admin: "Sub-Sponsor",
};
