"use client";

import { useEffect, useState } from "react";

import { Card } from "@/components/Card";
import { openCheckout } from "@/lib/checkout";
import { KycStep } from "@/components/KycStep";
import { SignIn } from "@/components/SignIn";
import type { PandalPage } from "@/lib/api";
import { blockOf, rupees } from "@/lib/api";
import { ApiError, api, getPhone, getToken, kycStatus, paymentProviders } from "@/lib/visitor";

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

  // Above a threshold a donation has to be reported, so it needs a verified PAN
  // and cannot be anonymous. The threshold is fetched rather than assumed: the
  // first a donor hears of it should not be a refusal at the last step.
  const [threshold, setThreshold] = useState<number | null>(null);
  const [verified, setVerified] = useState(false);
  const [signedInAs, setSignedInAs] = useState<string | null>(null);
  const [providers, setProviders] = useState<string[]>([]);
  const [provider, setProvider] = useState("");

  useEffect(() => {
    setSignedInAs(getToken() ? getPhone() : null);
    kycStatus()
      .then((s) => { setThreshold(s.threshold_paise); setVerified(s.verified); })
      .catch(() => setThreshold(null));
    paymentProviders()
      .then((p) => setProviders(p.providers))
      .catch(() => setProviders([]));
  }, []);

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
    if (provider) body.payment_provider = provider;

    try {
      // Through the session helper, not a bare fetch: a donation large enough
      // to need a PAN also needs the Authorization header, and a raw fetch
      // sends none — which reads on the server as an anonymous donor.
      const payload = await api<any>("/donations", {
        method: "POST", idempotent: true, json: body,
      });

      // The order exists; now take the money. Dismissing the modal leaves the
      // order pending rather than failed — somebody may come back to it.
      const result = await openCheckout(payload.payment, {
        name: page.pandal.name,
        description: `Donation to ${page.pandal.name}`,
        prefillPhone: signedInAs ?? "",
        prefillName: name,
        themeColour: page.brand?.primary_colour,
      });

      if (result.status === "paid") {
        setStatus({ tone: "ok", message: `Thank you. Receipt ${result.receipt}.` });
      } else if (result.status === "dismissed") {
        setStatus({ tone: "error", message: "Payment cancelled — nothing has been charged." });
      } else {
        setStatus({ tone: "error", message: result.message });
      }
    } catch (caught) {
      setStatus({
        tone: "error",
        message: caught instanceof ApiError ? caught.message : "That did not work.",
      });
    } finally {
      setBusy(false);
    }
  }

  const selectedAmount = custom.trim()
    ? Math.round(Number(custom) * 100)
    : offerings.find((o) => o.id === offeringId)?.amount_paise ?? 0;

  // Worked out from the amount as it is typed, so the requirement appears while
  // the donor is still deciding rather than after they have committed.
  const overThreshold = threshold !== null && selectedAmount >= threshold;
  const needsSignIn = overThreshold && !signedInAs;
  const needsKyc = overThreshold && Boolean(signedInAs) && !verified;
  const thresholdLabel = threshold !== null ? rupees(threshold) : "";

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

        {/* A <form> only when nothing else is blocking. Both SignIn and
            KycStep own forms of their own, and HTML forms cannot nest — an
            inner submit fires the outer one and reloads the page. */}
        <Card signedIn={!needsSignIn && !needsKyc} onSubmit={submit} className="offer-card">
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

          {providers.length > 1 && (
            <label className="field">
              <span>Pay with</span>
              <select value={provider} onChange={(event) => setProvider(event.target.value)}>
                {providers.map((name) => (
                  <option key={name} value={name}>
                    {name === "razorpay" ? "Razorpay" : "Cashfree"}
                  </option>
                ))}
              </select>
            </label>
          )}

          {needsSignIn ? (
            <SignIn
              reason={`Donations over ${thresholdLabel} have to be reported by the committee, so this one cannot be anonymous.`}
              onSignedIn={(phone) => { setSignedInAs(phone); kycStatus()
                .then((s) => setVerified(s.verified)).catch(() => undefined); }}
            />
          ) : needsKyc ? (
            <KycStep threshold={thresholdLabel} onVerified={() => setVerified(true)} />
          ) : (
            <>
              <p className="note">
                {overThreshold
                  ? "Verified. Your receipt will carry your name as registered."
                  : "No account needed. Leaving your name blank donates anonymously, and the receipt then carries no name."}
              </p>

              <button className="btn btn-ink" type="submit" disabled={busy || selectedAmount <= 0}>
                {busy ? "Working…" : `Donate ${selectedAmount > 0 ? rupees(selectedAmount) : ""}`}
              </button>
            </>
          )}

          {status && (
            <p className="status" data-tone={status.tone} role="status">
              {status.message}
            </p>
          )}
        </Card>
      </div>
    </section>
  );
}
