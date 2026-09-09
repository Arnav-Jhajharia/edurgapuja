"use client";

import { useEffect, useState } from "react";

import {
  ApiError, authMethods, requestCode, signInWithPassword, verifyCode,
} from "@/lib/visitor";

type Method = "otp" | "password";

/**
 * The sign-in step, shared by every block that needs one.
 *
 * A donation may be entirely anonymous; a pass or a booking has to reach a
 * phone. Both of those blocks used to carry their own copy of this, which meant
 * adding a second sign-in method would have meant writing it twice.
 */
export function SignIn({ reason, onSignedIn }: {
  reason: string;
  onSignedIn: (phone: string) => void;
}) {
  const [method, setMethod] = useState<Method>("otp");
  const [phone, setPhone] = useState("");
  const [code, setCode] = useState("");
  const [password, setPassword] = useState("");
  const [sent, setSent] = useState(false);
  const [busy, setBusy] = useState(false);
  const [status, setStatus] = useState<{ tone: "ok" | "error"; message: string } | null>(null);
  const [demo, setDemo] = useState(false);

  useEffect(() => {
    authMethods().then((m) => setDemo(m.shared_dev_password)).catch(() => setDemo(false));
  }, []);

  async function submit(event: React.FormEvent) {
    event.preventDefault();
    setBusy(true); setStatus(null);
    try {
      if (method === "password") {
        await signInWithPassword(phone, password);
        onSignedIn(phone);
      } else if (!sent) {
        await requestCode(phone);
        setSent(true);
        setStatus({ tone: "ok", message: "We sent you a code." });
      } else {
        await verifyCode(phone, code);
        onSignedIn(phone);
      }
    } catch (caught) {
      setStatus({ tone: "error",
                  message: caught instanceof ApiError ? caught.message : "That did not work." });
    } finally { setBusy(false); }
  }

  const label = method === "password" ? "Sign in"
              : sent ? "Verify and continue" : "Send me a code";

  // Its own <form>, deliberately. It renders inside a card that is otherwise a
  // buy-or-book form, and a submit button inside that form would fire *that*
  // handler — posting a purchase with no session and answering 401.
  return (
    <form className="signin" onSubmit={submit}>
      <label className="field">
        <span>Mobile number</span>
        <input inputMode="tel" value={phone} placeholder="+91 98765 43210"
               autoComplete="tel" onChange={(e) => setPhone(e.target.value)} />
      </label>

      {method === "password" && (
        <label className="field">
          <span>Password</span>
          <input type="password" value={password} autoComplete="current-password"
                 onChange={(e) => setPassword(e.target.value)} />
        </label>
      )}

      {method === "otp" && sent && (
        <label className="field">
          <span>The code we sent you</span>
          <input inputMode="numeric" value={code} placeholder="6 digits"
                 onChange={(e) => setCode(e.target.value)} />
        </label>
      )}

      <p className="note">{reason}</p>

      <button className="btn btn-ink" type="submit"
              disabled={busy || !phone || (method === "password" && !password)}>
        {busy ? "Working…" : label}
      </button>

      <button type="button" className="link-inline" onClick={() => {
        setMethod(method === "otp" ? "password" : "otp");
        setSent(false); setCode(""); setPassword(""); setStatus(null);
      }}>
        {method === "otp" ? "Use a password instead" : "Use a one-time code instead"}
      </button>

      {demo && (
        <p className="note demo-note">
          Demo build · any number signs in with the password <code>password</code>.
        </p>
      )}

      {status && <p className="status" data-tone={status.tone} role="status">{status.message}</p>}
    </form>
  );
}
