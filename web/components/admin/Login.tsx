"use client";

import { useEffect, useState } from "react";

import { Lotus } from "@/components/admin/Lotus";
import { api, ApiError, setToken } from "@/lib/admin";

type Method = "otp" | "password";

export function Login({ onSignedIn }: { onSignedIn: () => void }) {
  const [method, setMethod] = useState<Method>("otp");
  const [phone, setPhone] = useState("");
  const [code, setCode] = useState("");
  const [password, setPassword] = useState("");
  const [sent, setSent] = useState(false);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const [demo, setDemo] = useState(false);

  // A build running on the shared development password should say so out loud,
  // rather than looking like the real thing.
  useEffect(() => {
    api<{ shared_dev_password: boolean }>("/admin/auth/methods")
      .then((body) => setDemo(body.shared_dev_password))
      .catch(() => setDemo(false));
  }, []);

  function signedIn(body: { access: string; refresh: string }) {
    setToken(body.access, body.refresh);
    onSignedIn();
  }

  async function submit(event: React.FormEvent) {
    event.preventDefault();
    setBusy(true); setError("");
    try {
      if (method === "password") {
        signedIn(await api("/admin/auth/password/login",
                           { method: "POST", json: { phone, password } }));
      } else if (!sent) {
        await api("/admin/auth/otp/request", { method: "POST", json: { phone } });
        setSent(true);
      } else {
        signedIn(await api("/admin/auth/otp/verify",
                           { method: "POST", json: { phone, code } }));
      }
    } catch (caught) {
      setError(caught instanceof ApiError ? caught.message : "That did not work.");
    } finally { setBusy(false); }
  }

  function switchTo(next: Method) {
    setMethod(next);
    setSent(false); setCode(""); setPassword(""); setError("");
  }

  const label = method === "password" ? "Sign in" : sent ? "Sign in" : "Send code";

  return (
    <div className="login">
      <form className="login-card form" onSubmit={submit}>
        {/* Mark and wordmark on one line, the way the rail carries them, so
            signing in and being signed in look like the same product. */}
        <div className="login-head">
          <span className="login-mark"><Lotus /></span>
          <div>
            <h1>eDurgaPuja</h1>
            <p className="sub">Admin login</p>
          </div>
        </div>

        <p className="login-note">
          {method === "password"
            ? "Sign in with your mobile number and password."
            : sent ? "Enter the code we sent you."
                   : "Sign in with your mobile number."}
        </p>

        <label>
          <span>Mobile number</span>
          <input value={phone} onChange={(e) => setPhone(e.target.value)}
                 placeholder="98765 43210" autoComplete="tel" disabled={sent} />
        </label>

        {method === "password" && (
          <label>
            <span>Password</span>
            <input type="password" value={password} autoComplete="current-password"
                   onChange={(e) => setPassword(e.target.value)} placeholder="Your password" />
          </label>
        )}

        {method === "otp" && sent && (
          <label>
            <span>One-time code</span>
            <input value={code} onChange={(e) => setCode(e.target.value)}
                   inputMode="numeric" autoFocus placeholder="6 digits" />
          </label>
        )}

        <button className="abtn" type="submit"
                disabled={busy || !phone || (method === "password" && !password)}>
          {busy ? "Working…" : label}
        </button>

        {method === "otp" && sent && (
          <button type="button" className="abtn abtn-quiet"
                  onClick={() => switchTo("otp")}>
            Use a different number
          </button>
        )}

        <button type="button" className="link-btn"
                onClick={() => switchTo(method === "otp" ? "password" : "otp")}>
          {method === "otp" ? "Use a password instead" : "Use a one-time code instead"}
        </button>

        {demo && (
          <p className="msg demo-note">
            Demo build · any account signs in with the password <code>password</code>.
          </p>
        )}

        {error && <p className="msg" data-tone="error">{error}</p>}
      </form>
    </div>
  );
}
