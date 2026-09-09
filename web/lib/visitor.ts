"use client";

/**
 * The visitor's own session.
 *
 * Separate from `lib/admin.ts` on purpose: these are different people with
 * different tokens, and a volunteer signing in to scan must not inherit the
 * console session of whoever last used the browser.
 *
 * A donation needs none of this — it may be entirely anonymous. A pass does,
 * because a pass has to reach a phone.
 */

const TOKEN_KEY = "edp.visitor.token";
const REFRESH_KEY = "edp.visitor.refresh";
const PHONE_KEY = "edp.visitor.phone";

export function getToken(): string | null {
  if (typeof window === "undefined") return null;
  try {
    return window.localStorage.getItem(TOKEN_KEY);
  } catch {
    return null;
  }
}

export function getPhone(): string | null {
  if (typeof window === "undefined") return null;
  try {
    return window.localStorage.getItem(PHONE_KEY);
  } catch {
    return null;
  }
}

export function setSession(access: string | null, refresh?: string | null, phone?: string) {
  try {
    if (access) window.localStorage.setItem(TOKEN_KEY, access);
    else window.localStorage.removeItem(TOKEN_KEY);
    if (refresh !== undefined) {
      if (refresh) window.localStorage.setItem(REFRESH_KEY, refresh);
      else window.localStorage.removeItem(REFRESH_KEY);
    }
    if (phone) window.localStorage.setItem(PHONE_KEY, phone);
    if (access === null) window.localStorage.removeItem(PHONE_KEY);
  } catch {
    /* private browsing; the session simply does not persist */
  }
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

let refreshing: Promise<string | null> | null = null;

function refreshAccessToken(): Promise<string | null> {
  if (refreshing) return refreshing;
  let refresh: string | null = null;
  try {
    refresh = window.localStorage.getItem(REFRESH_KEY);
  } catch {
    refresh = null;
  }
  if (!refresh) return Promise.resolve(null);

  refreshing = fetch("/api/auth/token/refresh", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ refresh }),
  })
    .then((r) => (r.ok ? r.json() : null))
    .then((body: any) => {
      if (!body?.access) {
        setSession(null, null);
        return null;
      }
      setSession(body.access, body.refresh ?? undefined);
      return body.access as string;
    })
    .catch(() => null)
    .finally(() => {
      refreshing = null;
    });

  return refreshing;
}

export async function api<T = any>(
  path: string,
  init: RequestInit & { json?: unknown; idempotent?: boolean } = {},
): Promise<T> {
  const { json, idempotent, ...rest } = init;
  const body = json !== undefined ? JSON.stringify(json) : rest.body;
  // One key for the whole call, retries included: the point of an idempotency
  // key is that the retry carries the *same* one.
  const key = idempotent ? crypto.randomUUID() : null;

  const send = (token: string | null) => {
    const headers: Record<string, string> = { ...(rest.headers as any) };
    if (token) headers.Authorization = `Bearer ${token}`;
    if (json !== undefined) headers["Content-Type"] = "application/json";
    if (key) headers["Idempotency-Key"] = key;
    return fetch(`/api${path}`, { ...rest, headers, body });
  };

  let response = await send(getToken());
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

/** Sign in with a password instead of waiting for an SMS. */
export async function signInWithPassword(phone: string, password: string) {
  const body = await api<{ access: string; refresh: string }>(
    "/auth/password/login", { method: "POST", json: { phone, password } },
  );
  setSession(body.access, body.refresh, phone);
  return body;
}

/** What sign-in options this deployment offers. */
export const authMethods = () =>
  api<{ otp: boolean; password: boolean; shared_dev_password: boolean }>("/auth/methods");

/** Step one: send a code. Identical whether or not the number is registered. */
export const requestCode = (phone: string) =>
  api("/auth/otp/request", { method: "POST", json: { phone } });

/** Step two: verifying creates the account if it does not exist, which is what
    lets a web purchase reach the app with no separate linking step (FR-019). */
export async function verifyCode(phone: string, code: string) {
  const body = await api<{ access: string; refresh: string; is_new_user: boolean }>(
    "/auth/otp/verify", { method: "POST", json: { phone, code } },
  );
  setSession(body.access, body.refresh, phone);
  return body;
}

// --- KYC -------------------------------------------------------------------

export type KycStatus = {
  threshold_paise: number;
  verified: boolean;
  check: { masked_number: string; name_on_record: string } | null;
};

/** Where the threshold is, and whether this donor is past it already. */
export const kycStatus = () => api<KycStatus>("/kyc/status");

/** Verify a PAN. Throws ApiError with code `kyc_failed` if the register says no. */
export const verifyPan = (pan: string, name: string) =>
  api("/kyc/pan", { method: "POST", json: { pan, name } });

/** Which gateways this deployment will take money through. */
export const paymentProviders = () =>
  api<{ providers: string[] }>("/payments/providers");

