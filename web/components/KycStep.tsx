"use client";

import { useState } from "react";

import { ApiError, verifyPan } from "@/lib/visitor";

/**
 * Verifying a PAN, inline, at the moment it becomes necessary.
 *
 * This appears only when a donor has typed an amount large enough to need it,
 * because asking everybody for a PAN in case they turn out to be generous is
 * how a donate form loses the other ninety-nine donors.
 *
 * The wording says why. "Required by law for donations over ₹X" is a sentence
 * somebody will accept; an unexplained demand for a tax number on a puja page
 * is a sentence somebody closes the tab over.
 */
export function KycStep({ threshold, onVerified }: {
  threshold: string;
  onVerified: () => void;
}) {
  const [pan, setPan] = useState("");
  const [name, setName] = useState("");
  const [busy, setBusy] = useState(false);
  const [status, setStatus] = useState<{ tone: "ok" | "error"; message: string } | null>(null);

  async function submit(event: React.FormEvent) {
    event.preventDefault();
    setBusy(true);
    setStatus(null);
    try {
      await verifyPan(pan, name);
      setStatus({ tone: "ok", message: "Verified. You can complete your donation." });
      onVerified();
    } catch (caught) {
      setStatus({
        tone: "error",
        message: caught instanceof ApiError ? caught.message : "That did not work.",
      });
    } finally {
      setBusy(false);
    }
  }

  return (
    <form className="kyc-step" onSubmit={submit}>
      <p className="note kyc-why">
        Donations over {threshold} have to be reported by the committee, so this one
        needs your PAN and cannot be anonymous.
      </p>

      <label className="field">
        <span>PAN</span>
        <input value={pan} placeholder="ABCDE1234F" autoComplete="off"
               maxLength={10} style={{ textTransform: "uppercase" }}
               onChange={(e) => setPan(e.target.value.toUpperCase())} />
      </label>

      <label className="field">
        <span>Name exactly as on the PAN</span>
        <input value={name} placeholder="As printed on the card"
               onChange={(e) => setName(e.target.value)} />
      </label>

      <button className="btn btn-ink" type="submit"
              disabled={busy || pan.length !== 10 || !name.trim()}>
        {busy ? "Checking…" : "Verify"}
      </button>

      {status && (
        <p className="status" data-tone={status.tone} role="status">{status.message}</p>
      )}
    </form>
  );
}
