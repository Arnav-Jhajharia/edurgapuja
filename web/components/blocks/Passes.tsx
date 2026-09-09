"use client";

import { useEffect, useState } from "react";

import type { PandalPage } from "@/lib/api";
import { blockOf, rupees } from "@/lib/api";
import { Card } from "@/components/Card";
import { SignIn } from "@/components/SignIn";
import { ApiError, api, getPhone, getToken } from "@/lib/visitor";

type Status = { tone: "ok" | "error"; message: string } | null;
type Day = { date: string; capacity: number; available: number };

const DAY_LABEL = (iso: string) =>
  new Date(`${iso}T00:00:00`).toLocaleDateString("en-IN",
    { weekday: "short", day: "numeric", month: "short" });

export function Passes({ page }: { page: PandalPage }) {
  const content = blockOf(page, "passes");
  const configs = page.passes;

  const [configId, setConfigId] = useState(configs[0]?.id ?? "");
  const [date, setDate] = useState("");
  const [party, setParty] = useState(1);
  const [days, setDays] = useState<Day[]>([]);
  const [status, setStatus] = useState<Status>(null);
  const [busy, setBusy] = useState(false);

  // Sign-in stays inline. A pass has to reach a phone, so unlike a donation
  // this cannot be anonymous — but it should not be a detour to another page.
  const [signedInAs, setSignedInAs] = useState<string | null>(null);

  useEffect(() => { setSignedInAs(getToken() ? getPhone() : null); }, []);

  useEffect(() => {
    if (configs.length === 0) return;
    fetch(`/api/pandals/${page.pandal.slug}/pass-availability`)
      .then((r) => (r.ok ? r.json() : []))
      .then((rows: Day[]) => {
        setDays(rows);
        setDate((current) => current || rows.find((d) => d.available > 0)?.date || "");
      })
      .catch(() => setDays([]));
  }, [page.pandal.slug, configs.length]);

  if (!page.capabilities.sells_passes || configs.length === 0) return null;

  const selected = configs.find((c) => c.id === configId) ?? configs[0];
  const isGroup = selected?.product === "group";
  const size = isGroup ? party : 1;
  const total = (selected?.price_paise ?? 0) * size;
  const chosenDay = days.find((d) => d.date === date);

  async function buy(event: React.FormEvent) {
    event.preventDefault();
    setBusy(true); setStatus(null);
    try {
      const body = await api<any>("/passes", {
        method: "POST", idempotent: true,
        json: {
          config_id: selected.id, visit_date: date, party_size: size,
          contact_phone: signedInAs ?? "",
        },
      });
      setStatus({
        tone: "ok",
        message: `${body.pass_code} is held for you — ${rupees(body.amount_paise)} to pay`
          + (body.pandals_covered > 1 ? `, covering ${body.pandals_covered} pandals.` : "."),
      });
    } catch (caught) {
      setStatus({ tone: "error",
                  message: caught instanceof ApiError ? caught.message : "That did not work." });
    } finally { setBusy(false); }
  }

  return (
    <section className="section on-surface" id="passes">
      <div className="shell">
        <div className="section-head">
          <div>
            <p className="eyebrow">04 / Entry Passes</p>
            <h2 className="display">{content?.headline ?? "Skip the queue."}</h2>
          </div>
          <p>
            {content?.standfirst
              ?? "Your pass lives on your phone and works without a signal at the gate."}
          </p>
        </div>

        <div className="pass-grid">
          <div className="pass-options">
            {configs.map((config) => (
              <button
                type="button"
                key={config.id}
                className="pass-option"
                aria-pressed={config.id === selected.id}
                onClick={() => { setConfigId(config.id); setParty(1); }}
              >
                <div className="pass-option-head">
                  <strong>{config.category.name}</strong>
                  <span className="pass-price">{rupees(config.price_paise)}</span>
                </div>
                <p className="pass-kind">
                  {config.product_display}
                  {config.product === "group" && ` · up to ${config.max_party_size} people`}
                  {config.product === "city" && " · every pandal in Kolkata"}
                </p>
                <p className="pass-when">
                  {/* A City Pass has a date and no time (D3), so there is
                      nothing to print here for one. */}
                  {config.from_time
                    ? `${config.from_time.slice(0, 5)} – ${config.to_time?.slice(0, 5)}`
                    : "Any time on the day"}
                </p>
                {config.category.description && (
                  <p className="pass-note">{config.category.description}</p>
                )}
              </button>
            ))}
          </div>

          <Card signedIn={Boolean(signedInAs)} onSubmit={buy}>
            <p className="eyebrow" style={{ margin: 0 }}>Your pass</p>
            <h3 className="display" style={{ fontSize: 28, margin: "8px 0 14px" }}>
              {selected.category.name} · {selected.product_display}
            </h3>

            <label className="field">
              <span>Which day</span>
              <select value={date} onChange={(e) => setDate(e.target.value)}>
                {days.map((day) => (
                  <option key={day.date} value={day.date} disabled={day.available === 0}>
                    {DAY_LABEL(day.date)}
                    {day.available === 0 ? " · sold out" : ` · ${day.available} left`}
                  </option>
                ))}
              </select>
            </label>

            {isGroup && (
              <label className="field">
                <span>How many people</span>
                <select value={party} onChange={(e) => setParty(Number(e.target.value))}>
                  {Array.from({ length: selected.max_party_size }, (_, i) => i + 1).map((n) => (
                    <option key={n} value={n}>{n}</option>
                  ))}
                </select>
              </label>
            )}

            {signedInAs ? (
              <>
                <p className="note">
                  Signed in as {signedInAs}. Your pass appears in the app straight away — the
                  entry code is generated on your phone, so it works with no signal at the gate.
                </p>
                <button className="btn btn-ink" type="submit"
                        disabled={busy || !date || (chosenDay?.available ?? 0) < size}>
                  {busy ? "Working…" : `Buy for ${rupees(total)}`}
                </button>
              </>
            ) : (
              <SignIn reason="A pass has to reach a phone, so this one needs your number — unlike a donation, which can be entirely anonymous."
                      onSignedIn={setSignedInAs} />
            )}

            {status && (
              <p className="status" data-tone={status.tone} role="status">{status.message}</p>
            )}
          </Card>
        </div>
      </div>
    </section>
  );
}
