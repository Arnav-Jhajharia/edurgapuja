"use client";

import { useState } from "react";

import type { PandalPage } from "@/lib/api";
import { blockOf, rupees } from "@/lib/api";

type Status = { tone: "ok" | "error"; message: string } | null;

export function Donate({ page }: { page: PandalPage }) {
  const content = blockOf(page, "donate");
  const offerings = page.donation_offerings;

  const [offeringId, setOfferingId] = useState<string | null>(offerings[1]?.id ?? null);
  const [custom, setCustom] = useState("");
  const [name, setName] = useState("");
  const [message, setMessage] = useState("");
  const [busy, setBusy] = useState(false);
  const [status, setStatus] = useState<Status>(null);

  if (!page.capabilities.accepts_donations) return null;

  async function submit(event: React.FormEvent) {
    event.preventDefault();
    setBusy(true);
    setStatus(null);

    const body: Record<string, unknown> = {
      pandal_id: page.pandal.id,
      donor_name: name,
      message,
    };
    if (custom.trim()) {
      body.amount_paise = Math.round(Number(custom) * 100);
    } else if (offeringId) {
      body.offering_id = offeringId;
    }

    try {
      const response = await fetch("/api/donations", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          // The client retries; the network duplicates. Same key, same order.
          "Idempotency-Key": crypto.randomUUID(),
        },
        body: JSON.stringify(body),
      });
      const payload = await response.json();

      if (!response.ok) {
        setStatus({ tone: "error", message: payload?.error?.message ?? "That did not work." });
      } else {
        setStatus({
          tone: "ok",
          message: `Thank you. ${rupees(payload.amount_paise)} is ready to pay — order ${
            payload.order_id.slice(0, 8)
          }.`,
        });
      }
    } catch {
      setStatus({ tone: "error", message: "We could not reach the server. Try again." });
    } finally {
      setBusy(false);
    }
  }

  const selectedAmount = custom.trim()
    ? Math.round(Number(custom) * 100)
    : offerings.find((o) => o.id === offeringId)?.amount_paise ?? 0;

  return (
    <section className="section on-primary" id="donate">
      <div className="shell donate-grid">
        <div>
          <p className="eyebrow">03 / Donate</p>
          <h2 className="display" style={{ fontSize: "clamp(38px, 6vw, 72px)", margin: "16px 0" }}>
            {content?.headline ?? "Support the Celebration."}
          </h2>
          <p style={{ maxWidth: "42ch", opacity: 0.92 }}>{content?.body}</p>
        </div>

        <form className="offer-card" onSubmit={submit}>
          <p className="eyebrow" style={{ margin: 0 }}>
            {content?.card_eyebrow ?? "Choose your offering"}
          </p>
          <h3 className="display" style={{ fontSize: 30, margin: "8px 0 4px" }}>
            {content?.card_title ?? "Keep the light burning."}
          </h3>

          <div className="offer-grid">
            {offerings.map((offering) => (
              <button
                type="button"
                key={offering.id}
                className="offer"
                aria-pressed={!custom.trim() && offeringId === offering.id}
                onClick={() => {
                  setOfferingId(offering.id);
                  setCustom("");
                }}
              >
                <strong>{rupees(offering.amount_paise)}</strong>
                <span>{offering.label}</span>
              </button>
            ))}
          </div>

          <label className="field">
            <span>Or enter a custom amount</span>
            <input
              inputMode="decimal"
              value={custom}
              placeholder="e.g. 750"
              onChange={(event) => setCustom(event.target.value)}
            />
          </label>

          <label className="field">
            <span>Your name · optional for receipt</span>
            <input
              value={name}
              placeholder="Leave blank to donate anonymously"
              onChange={(event) => setName(event.target.value)}
            />
          </label>

          <label className="field">
            <span>Message · optional</span>
            <input
              value={message}
              placeholder="e.g. Jai Maa Durga"
              onChange={(event) => setMessage(event.target.value)}
            />
          </label>

          <p className="note">
            No account needed. Leaving your name blank donates anonymously, and the receipt then
            carries no name.
          </p>

          <button className="btn btn-ink" type="submit" disabled={busy || selectedAmount <= 0}>
            {busy ? "Working…" : `Donate ${selectedAmount > 0 ? rupees(selectedAmount) : ""}`}
          </button>

          {status && (
            <p className="status" data-tone={status.tone} role="status">
              {status.message}
            </p>
          )}
        </form>
      </div>
    </section>
  );
}
