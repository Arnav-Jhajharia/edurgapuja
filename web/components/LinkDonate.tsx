"use client";

import { useState } from "react";

import type { DonationLink, PandalPage } from "@/lib/api";
import { rupees } from "@/lib/api";
import { ApiError, api } from "@/lib/visitor";

type Status = { tone: "ok" | "error"; message: string } | null;

/**
 * The donate form behind a shared link.
 *
 * Two differences from the one on the pandal's own page. It opens on the amount
 * the person sharing asked for, because arriving to find nothing selected reads
 * as though the link forgot what it was for. And it sends `link_token`, so the
 * committee can see which of their links actually collected anything (FR-050d).
 */
export function LinkDonate({ page, link }: { page: PandalPage; link: DonationLink }) {
  const offerings = page.donation_offerings;
  const suggested = link.suggested_amount_paise;

  // If the link names an amount that matches a preset, select that preset;
  // otherwise put the amount in the custom field so it is visible and editable.
  const matching = suggested ? offerings.find((o) => o.amount_paise === suggested) : undefined;
  const [offeringId, setOfferingId] = useState<string | null>(matching?.id ?? null);
  const [custom, setCustom] = useState(
    suggested && !matching ? String(suggested / 100) : "",
  );
  const [name, setName] = useState("");
  const [message, setMessage] = useState("");
  const [busy, setBusy] = useState(false);
  const [status, setStatus] = useState<Status>(null);

  const amount = custom.trim()
    ? Math.round(Number(custom) * 100)
    : offerings.find((o) => o.id === offeringId)?.amount_paise ?? 0;

  async function submit(event: React.FormEvent) {
    event.preventDefault();
    setBusy(true);
    setStatus(null);

    const body: Record<string, unknown> = {
      pandal_id: page.pandal.id,
      donor_name: name,
      message,
      link_token: link.token,
    };
    if (custom.trim()) body.amount_paise = amount;
    else if (offeringId) body.offering_id = offeringId;

    try {
      // Same helper as the page's own form: a large donation needs the session
      // header, and a bare fetch would send none.
      const payload = await api<any>("/donations", {
        method: "POST", idempotent: true, json: body,
      });
      setStatus({
        tone: "ok",
        message: `Thank you. ${rupees(payload.amount_paise)} is ready to pay — order ${
          payload.order_id.slice(0, 8)
        }.`,
      });
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
    <form className="offer-card link-card" onSubmit={submit}>
      {offerings.length > 0 && (
        <div className="offer-grid">
          {offerings.map((offering) => (
            <button
              type="button"
              key={offering.id}
              className="offer"
              aria-pressed={!custom.trim() && offeringId === offering.id}
              onClick={() => { setOfferingId(offering.id); setCustom(""); }}
            >
              <strong>{rupees(offering.amount_paise)}</strong>
              <span>{offering.label}</span>
            </button>
          ))}
        </div>
      )}

      <label className="field">
        <span>{offerings.length > 0 ? "Or another amount" : "Amount"}</span>
        <input inputMode="decimal" value={custom} placeholder="e.g. 750"
               onChange={(event) => setCustom(event.target.value)} />
      </label>

      <label className="field">
        <span>Your name · optional for receipt</span>
        <input value={name} placeholder="Leave blank to give anonymously"
               onChange={(event) => setName(event.target.value)} />
      </label>

      <label className="field">
        <span>Message · optional</span>
        <input value={message} placeholder="e.g. Jai Maa Durga"
               onChange={(event) => setMessage(event.target.value)} />
      </label>

      <button className="btn btn-ink" type="submit" disabled={busy || amount <= 0}>
        {busy ? "Working…" : `Donate ${amount > 0 ? rupees(amount) : ""}`}
      </button>

      {status && (
        <p className="status" data-tone={status.tone} role="status">{status.message}</p>
      )}
    </form>
  );
}
