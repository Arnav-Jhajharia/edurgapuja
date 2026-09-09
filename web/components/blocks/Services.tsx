"use client";

import { useEffect, useState } from "react";

import type { PandalPage, ServiceFormField } from "@/lib/api";
import { blockOf, rupees } from "@/lib/api";
import { Card } from "@/components/Card";
import { SignIn } from "@/components/SignIn";
import { ApiError, api, getPhone, getToken } from "@/lib/visitor";

type Status = { tone: "ok" | "error"; message: string } | null;
type Day = { date: string; capacity: number; available: number };

const DAY_LABEL = (iso: string) =>
  new Date(`${iso}T00:00:00`).toLocaleDateString("en-IN",
    { weekday: "short", day: "numeric", month: "short" });

export function Services({ page }: { page: PandalPage }) {
  const [openId, setOpenId] = useState<string | null>(null);
  const content = blockOf(page, "services");

  if (!page.capabilities.offers_services || page.services.length === 0) return null;

  return (
    <section className="section on-surface" id="services">
      <div className="shell">
        <div className="section-head">
          <div>
            <p className="eyebrow">02 / Value-Added Services</p>
            <h2 className="display">{content?.headline ?? "Thoughtful extras for your visit."}</h2>
          </div>
          <p>{content?.standfirst}</p>
        </div>

        <div className="grid-3">
          {page.services.map((service, index) => (
            <div className="service" key={service.id}>
              <div className="service-index">{String(index + 1).padStart(2, "0")}</div>
              <h3>{service.name}</h3>
              {service.type && <p className="service-tag">{service.type}</p>}
              <p>{service.description}</p>
              <p className="service-price">
                {service.price_paise > 0 ? rupees(service.price_paise) : "Included"}
              </p>
              <button className="btn btn-quiet"
                      onClick={() => setOpenId(openId === service.id ? null : service.id)}>
                {openId === service.id ? "Close" : "Book this"}
              </button>
            </div>
          ))}
        </div>

        {openId && (
          <BookingForm
            page={page}
            service={page.services.find((s) => s.id === openId)!}
            onClose={() => setOpenId(null)}
          />
        )}
      </div>
    </section>
  );
}

/**
 * A booking form built from whatever the pandal decided to ask.
 *
 * There is no switch on service type here, because there is no service type any
 * more — only a list of questions and how to render each kind of answer.
 */
function BookingForm({ page, service, onClose }: {
  page: PandalPage;
  service: PandalPage["services"][number];
  onClose: () => void;
}) {
  const [answers, setAnswers] = useState<Record<string, unknown>>({});
  const [quantity, setQuantity] = useState(1);
  const [date, setDate] = useState("");
  const [days, setDays] = useState<Day[]>([]);
  const [status, setStatus] = useState<Status>(null);
  const [busy, setBusy] = useState(false);

  const [signedInAs, setSignedInAs] = useState<string | null>(null);

  useEffect(() => { setSignedInAs(getToken() ? getPhone() : null); }, []);

  useEffect(() => {
    if (!service.requires_capacity) return;
    fetch(`/api/services/${service.id}/availability`)
      .then((r) => (r.ok ? r.json() : []))
      .then((rows: Day[]) => {
        setDays(rows);
        setDate((current) => current || rows.find((d) => d.available > 0)?.date || "");
      })
      .catch(() => setDays([]));
  }, [service.id, service.requires_capacity]);

  const set = (key: string, value: unknown) =>
    setAnswers((current) => ({ ...current, [key]: value }));

  const asksAnythingPersonal = service.fields.some((f) => f.is_sensitive);
  const chosenDay = days.find((d) => d.date === date);

  async function book(event: React.FormEvent) {
    event.preventDefault();
    setBusy(true); setStatus(null);
    try {
      const body = await api<any>("/service-bookings", {
        method: "POST", idempotent: true,
        json: {
          service_id: service.id,
          date: service.requires_capacity ? date : null,
          quantity,
          details: answers,
        },
      });
      setStatus({
        tone: "ok",
        message: `Held for you — ${rupees(body.amount_paise)} to pay.`,
      });
    } catch (caught) {
      // The server names the field, so the message points at the question that
      // needs fixing rather than saying "something went wrong".
      const problem = caught instanceof ApiError
        ? Object.values(caught.fields)[0] ?? caught.message
        : "That did not work.";
      setStatus({ tone: "error", message: problem });
    } finally { setBusy(false); }
  }

  return (
    <Card signedIn={Boolean(signedInAs)} onSubmit={book} className="booking-card">
      <div className="booking-head">
        <div>
          <p className="eyebrow" style={{ margin: 0 }}>{page.pandal.name}</p>
          <h3 className="display" style={{ fontSize: 28, margin: "6px 0 0" }}>{service.name}</h3>
        </div>
        <button type="button" className="btn btn-quiet" onClick={onClose}>Close</button>
      </div>

      {service.requires_capacity ? (
        <label className="field">
          <span>Which day</span>
          <select value={date} onChange={(e) => setDate(e.target.value)}>
            {days.map((day) => (
              <option key={day.date} value={day.date} disabled={day.available === 0}>
                {DAY_LABEL(day.date)}
                {day.available === 0 ? " · fully booked" : ` · ${day.available} left`}
              </option>
            ))}
          </select>
        </label>
      ) : (
        <p className="note">No daily limit on this one — book it any time.</p>
      )}

      {service.max_per_booking > 1 && (
        <label className="field">
          <span>How many</span>
          <select value={quantity} onChange={(e) => setQuantity(Number(e.target.value))}>
            {Array.from({ length: service.max_per_booking }, (_, i) => i + 1).map((n) => (
              <option key={n} value={n}>{n}</option>
            ))}
          </select>
        </label>
      )}

      {signedInAs ? (
        <>
          {service.fields.map((field) => (
            <Question key={field.key} field={field}
                      value={answers[field.key]} onChange={(v) => set(field.key, v)} />
          ))}

          {asksAnythingPersonal && (
            <p className="note">
              Some of these are personal. They are stored only for this booking, and only
              because this service asks for them.
            </p>
          )}

          <button className="btn btn-ink" type="submit"
                  disabled={busy
                            || (service.requires_capacity
                                && (!date || (chosenDay?.available ?? 0) < quantity))}>
            {busy ? "Working…" : `Book for ${rupees(service.price_paise * quantity)}`}
          </button>
        </>
      ) : (
        <SignIn reason="A booking has to reach you, so this one needs your number."
                onSignedIn={setSignedInAs} />
      )}

      {status && <p className="status" data-tone={status.tone} role="status">{status.message}</p>}
    </Card>
  );
}

/** One question, rendered according to its kind. */
function Question({ field, value, onChange }: {
  field: ServiceFormField;
  value: unknown;
  onChange: (value: unknown) => void;
}) {
  const label = (
    <span>
      {field.label}
      {field.required && <em className="req"> · required</em>}
    </span>
  );

  if (field.kind === "checkbox") {
    return (
      <label className="field field-check">
        <input type="checkbox" checked={Boolean(value)}
               onChange={(e) => onChange(e.target.checked)} />
        {label}
        {field.help_text && <small>{field.help_text}</small>}
      </label>
    );
  }

  if (field.kind === "select") {
    return (
      <label className="field">
        {label}
        <select value={String(value ?? "")} onChange={(e) => onChange(e.target.value)}>
          <option value="">Choose…</option>
          {field.options.map((option) => <option key={option} value={option}>{option}</option>)}
        </select>
        {field.help_text && <small>{field.help_text}</small>}
      </label>
    );
  }

  if (field.kind === "textarea") {
    return (
      <label className="field">
        {label}
        <textarea rows={3} value={String(value ?? "")}
                  onChange={(e) => onChange(e.target.value)} />
        {field.help_text && <small>{field.help_text}</small>}
      </label>
    );
  }

  const TYPE_FOR: Record<string, string> = {
    text: "text", phone: "tel", email: "email",
    number: "number", date: "date", time: "time",
  };

  return (
    <label className="field">
      {label}
      <input type={TYPE_FOR[field.kind] ?? "text"} value={String(value ?? "")}
             onChange={(e) => onChange(e.target.value)} />
      {field.help_text && <small>{field.help_text}</small>}
    </label>
  );
}
