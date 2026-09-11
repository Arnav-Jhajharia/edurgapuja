"use client";

import { useState } from "react";

import { api, list, rupees, type Me } from "@/lib/admin";

import { donationLinkUrl, pandalDisplayHost, pandalHref } from "@/lib/urls";

import { CopyButton, Field, Form, Panel, Pill, Select, Table, Tile, useLoad } from "./ui";

type Pandal = Me["pandals"][number];
type Props = { me: Me; screen: string; pandalId: string };

export function PandalPanel({ me, screen, pandalId }: Props) {
  const pandal = me.pandals.find((p) => p.id === pandalId) ?? me.pandals[0];
  if (!pandal) return <p className="empty">No pandal is assigned to this account.</p>;

  const Screen = {
    revenue: Revenue, links: Links, offerings: Offerings, services: Services,
    bookings: Bookings, volunteers: Volunteers, packages: Packages, sponsors: Sponsors,
    live: Live, support: Support, page: PageContent,
    passSetup: PassSetup, passSales: PassSales, entryLog: EntryLog,
    appearance: Appearance, details: Details, visitFacts: VisitFacts,
    staff: Staff,
  }[screen] ?? Revenue;

  return <Screen pandal={pandal} />;
}

type P = { pandal: Pandal };

/* -------------------------------------------------------------- Donations */

function Revenue({ pandal }: P) {
  const { data: revenue } = useLoad<any>(() => api(`/admin/revenue?pandal=${pandal.id}`),
                                         [pandal.id]);
  const { data: donations } = useLoad<any[]>(() => list(`/admin/donations?pandal=${pandal.id}`),
                                             [pandal.id]);
  const { data: bookings } = useLoad<any[]>(
    () => list(`/admin/service-bookings?pandal=${pandal.id}`), [pandal.id]);

  const { data: links, reload: reloadLinks } = useLoad<any[]>(
    () => list(`/admin/donation-links?pandal=${pandal.id}`), [pandal.id]);
  const [purpose, setPurpose] = useState("");
  const [amount, setAmount] = useState("");

  const byKind: Record<string, any> = {};
  for (const row of revenue?.by_kind ?? []) byKind[row.kind] = row;
  const received = (donations ?? []).filter((d) => d.received_at);

  return (
    <>
      <div className="tiles">
        <Tile label="Paid orders" value={revenue?.orders ?? "—"} />
        <Tile label="Total received" value={revenue ? rupees(revenue.total_paise) : "—"} />
        <Tile label="Donations"
              value={byKind.donation ? rupees(byKind.donation.total_paise) : "₹0"} />
        <Tile label="Services"
              value={byKind.service_booking ? rupees(byKind.service_booking.total_paise) : "₹0"} />
      </div>

      <Panel title="Generate a donation link"
             note="A shareable address that opens straight on the ask — for a committee member collecting for something specific.">
        <div className="panel-body">
          <Form label="Generate link"
                onDone={() => { setPurpose(""); setAmount(""); reloadLinks(); }}
                submit={() => api("/admin/donation-links", {
                  method: "POST",
                  json: {
                    pandal: pandal.id,
                    purpose,
                    suggested_amount_paise: amount ? Math.round(Number(amount) * 100) : null,
                  },
                })}>
            <Field label="Purpose · optional" value={purpose} placeholder="Bhog fund"
                   onChange={(e) => setPurpose(e.target.value)} />
            <Field label="Suggested amount · optional" value={amount} inputMode="decimal"
                   placeholder="501" onChange={(e) => setAmount(e.target.value)} />
          </Form>
        </div>
        <Table columns={["Purpose", "Suggested", "Link", "Donations", ""]}
               rows={(links ?? []).slice(0, 5).map((l: any) => [
                 l.purpose || <em>General</em>,
                 l.suggested_amount_paise
                   ? <span className="num">{rupees(l.suggested_amount_paise)}</span> : "—",
                 // One helper builds every pandal URL — hand-rolling it here is
                 // what put localhost:3000 into production links before.
                 <code className="link-cell">{donationLinkUrl(pandal.slug, l.token)}</code>,
                 <span className="num">{l.donation_count ?? 0}</span>,
                 <CopyButton text={donationLinkUrl(pandal.slug, l.token)} />,
               ])}
               empty="No links yet." />
      </Panel>

      <Panel title="Recent donations"
             note="Direct contributions made through this pandal's page.">
        <Table columns={["Donor", "Amount", "Offering", "Message", "Status"]}
               rows={(donations ?? []).slice(0, 8).map((d) => [
                 d.is_anonymous ? <em>Anonymous</em> : d.donor_name,
                 <span className="num">{rupees(d.amount_paise)}</span>,
                 d.offering_label || "—", d.message || "—",
                 <Pill value={d.received_at ? "received" : "pending"} />,
               ])}
               empty="No donations yet." />
      </Panel>

      <Panel title="Recent service bookings">
        <Table columns={["Service", "Date", "Quantity", "Status"]}
               rows={(bookings ?? []).slice(0, 8).map((b) => [
                 b.service_name, b.date, <span className="num">{b.quantity}</span>,
                 <Pill value={b.status} />,
               ])}
               empty="No bookings yet." />
      </Panel>

      {received.length === 0 && (donations ?? []).length > 0 && (
        <p className="empty">
          Revenue reads zero because no payment has been captured yet — these donations
          are still awaiting their gateway callback.
        </p>
      )}
    </>
  );
}

/* -------------------------------------------------------- Donation links */

function Links({ pandal }: P) {
  const { data, reload } = useLoad<any[]>(
    () => list(`/admin/donation-links?pandal=${pandal.id}`), [pandal.id]);
  const [purpose, setPurpose] = useState("");
  const [amount, setAmount] = useState("");

  return (
    <>
      <Panel title="New donation link"
             note="Leave the amount blank to let the donor choose how much to give.">
        <div className="panel-body">
          <Form label="Generate link" onDone={() => { setPurpose(""); setAmount(""); reload(); }}
                submit={() => api("/admin/donation-links", { method: "POST", json: {
                  pandal: pandal.id, purpose,
                  suggested_amount_paise: amount ? Math.round(Number(amount) * 100) : null,
                }})}>
            <Field label="Purpose · optional" value={purpose}
                   onChange={(e) => setPurpose(e.target.value)} placeholder="e.g. Bhog Seva" />
            <Field label="Suggested amount · optional" value={amount} inputMode="decimal"
                   onChange={(e) => setAmount(e.target.value)} placeholder="e.g. 501" />
          </Form>
        </div>
      </Panel>

      <Panel title="Generated links"
             note="Every link created for this pandal, newest first. Copy one and send it — whoever opens it gets your page with the amount already filled in, and no account is needed.">
        <Table columns={["Purpose", "Amount", "Link", "Donations", "Active", ""]}
               rows={(data ?? []).map((l) => [
                 l.purpose || "General",
                 l.suggested_amount_paise ? rupees(l.suggested_amount_paise) : "Any amount",
                 <code style={{ fontSize: 13 }}>/d/{l.token}</code>,
                 <span className="num">{l.donation_count}</span>,
                 <Pill value={l.is_active ? "active" : "off"} />,
                 <CopyButton text={donationLinkUrl(pandal.slug, l.token)} />,
               ])}
               empty="No links yet." />
      </Panel>
    </>
  );
}

/* ------------------------------------------------------ Donation presets */

function Offerings({ pandal }: P) {
  const { data, reload } = useLoad<any[]>(
    () => list(`/admin/donation-offerings?pandal=${pandal.id}`), [pandal.id]);
  const [label, setLabel] = useState("");
  const [amount, setAmount] = useState("");

  return (
    <>
      <Panel title="Add a preset"
             note="An amount with a purpose — '₹501 · Support a diya' — shown on the pandal's page.">
        <div className="panel-body">
          <Form label="Add preset" onDone={() => { setLabel(""); setAmount(""); reload(); }}
                submit={() => api("/admin/donation-offerings", { method: "POST", json: {
                  pandal: pandal.id, label,
                  amount_paise: Math.round(Number(amount) * 100),
                  sort_order: (data?.length ?? 0) + 1,
                }})}>
            <Field label="Amount" value={amount} inputMode="decimal" required
                   onChange={(e) => setAmount(e.target.value)} placeholder="501" />
            <Field label="Purpose" value={label} required
                   onChange={(e) => setLabel(e.target.value)} placeholder="Support a diya" />
          </Form>
        </div>
      </Panel>

      <Panel title="Presets on the page">
        <Table columns={["Amount", "Purpose", "Order", "Active", ""]}
               rows={(data ?? []).map((o) => [
                 <strong className="num">{rupees(o.amount_paise)}</strong>, o.label,
                 <span className="num">{o.sort_order}</span>,
                 <Pill value={o.is_active ? "active" : "off"} />,
                 <button className="abtn abtn-quiet" onClick={async () => {
                   await api(`/admin/donation-offerings/${o.id}`,
                             { method: "PATCH", json: { is_active: !o.is_active } });
                   reload();
                 }}>{o.is_active ? "Hide" : "Show"}</button>,
               ])}
               empty="No presets yet — the page will show only a custom amount." />
      </Panel>
    </>
  );
}

/* --------------------------------------------------------------- Services */


const KINDS: [string, string][] = [
  ["text", "Short text"], ["textarea", "Long text"], ["phone", "Mobile number"],
  ["email", "Email"], ["number", "Number"], ["date", "Date"], ["time", "Time"],
  ["select", "Choose one"], ["checkbox", "Yes or no"],
];

function Services({ pandal }: P) {
  const { data, reload } = useLoad<any[]>(() => list(`/admin/services?pandal=${pandal.id}`),
                                          [pandal.id]);
  const { data: templates } = useLoad<any[]>(() => api("/admin/services/templates"), []);

  const [name, setName] = useState("");
  const [type, setType] = useState("");
  const [template, setTemplate] = useState("blank");
  const [description, setDescription] = useState("");
  const [price, setPrice] = useState("");
  const [maxPer, setMaxPer] = useState("10");
  const [limited, setLimited] = useState(true);
  const [editing, setEditing] = useState<any>(null);
  const [openForm, setOpenForm] = useState<string | null>(null);

  const [openFrom, setOpenFrom] = useState("2026-10-10");
  const [openTo, setOpenTo] = useState("2026-10-14");
  const [places, setPlaces] = useState("20");

  const chosen = (templates ?? []).find((t) => t.slug === template);

  return (
    <>
      <Panel title={editing ? `Edit ${editing.name}` : "Add a service"}
             note="A service is whatever your committee offers, and it asks whatever you decide to ask. The templates below are starting points, not a list to choose from."
             actions={editing
               ? <button className="abtn abtn-quiet" onClick={() => setEditing(null)}>Cancel</button>
               : undefined}>
        <div className="panel-body">
          <Form label={editing ? "Save changes" : "Add service"}
                onDone={() => {
                  setName(""); setDescription(""); setPrice(""); setEditing(null); reload();
                }}
                submit={async () => {
                  const body: Record<string, unknown> = {
                    pandal: pandal.id, type, name, description,
                    price_paise: Math.round(Number(price || 0) * 100),
                    max_per_booking: Number(maxPer || 1),
                    requires_capacity: limited,
                    slug: (editing?.slug ?? name.toLowerCase().replace(/[^a-z0-9]+/g, "-")),
                  };
                  if (editing) {
                    return api(`/admin/services/${editing.id}`, { method: "PATCH", json: body });
                  }
                  const created = await api<any>("/admin/services",
                                                 { method: "POST", json: { ...body, template } });
                  if (limited && openFrom && openTo && Number(places) > 0) {
                    await api(`/admin/services/${created.id}/capacity`, {
                      method: "PUT", json: { days: daysBetween(openFrom, openTo, Number(places)) },
                    });
                  }
                  setOpenForm(created.id);
                  return created;
                }}>
            <Field label="Name" value={name} required placeholder="e.g. Dhunuchi Naach entry"
                   onChange={(e) => setName(e.target.value)} />
            <Field label="Group it under · optional" value={type}
                   onChange={(e) => setType(e.target.value)}
                   placeholder="e.g. Darshan, Prasad, Competition" />
            <Field label="Description" value={description}
                   onChange={(e) => setDescription(e.target.value)}
                   placeholder="What the visitor gets" />
            <Field label="Price · rupees" value={price} inputMode="decimal" required
                   onChange={(e) => setPrice(e.target.value)} placeholder="750" />
            <Field label="Maximum per booking" value={maxPer} inputMode="numeric"
                   onChange={(e) => setMaxPer(e.target.value)} />

            {!editing && (
              <>
                <Select label="Start its form from" value={template}
                        onChange={(e) => {
                          setTemplate(e.target.value);
                          const picked = (templates ?? []).find((t) => t.slug === e.target.value);
                          if (picked) setLimited(picked.requires_capacity);
                        }}>
                  {(templates ?? []).map((t) => (
                    <option key={t.slug} value={t.slug}>{t.name}</option>
                  ))}
                </Select>
                {chosen && (
                  <p className="hint">
                    {chosen.description} Starts by asking:{" "}
                    {chosen.fields.map((f: any) => f.label).join(", ")}. You can rename, reorder,
                    add or delete any of them afterwards.
                  </p>
                )}
              </>
            )}

            <label className="inline-check">
              <input type="checkbox" checked={limited}
                     onChange={(e) => setLimited(e.target.checked)} />
              This has a limited number of places each day
            </label>

            {!editing && limited && (
              <>
                <p className="hint">
                  Open it on these days. Without them it is saved but cannot be booked.
                </p>
                <div className="row">
                  <Field label="Open from" type="date" value={openFrom}
                         onChange={(e) => setOpenFrom(e.target.value)} />
                  <Field label="Open to" type="date" value={openTo}
                         onChange={(e) => setOpenTo(e.target.value)} />
                  <Field label="Places each day" value={places} inputMode="numeric"
                         onChange={(e) => setPlaces(e.target.value)} />
                </div>
              </>
            )}
          </Form>
        </div>
      </Panel>

      <Panel title="Services offered" note="What appears on the pandal's page.">
        <Table columns={["Service", "Group", "Price", "Max", "Places", "Questions", "Active", ""]}
               rows={(data ?? []).map((s) => [
                 <strong>{s.name}</strong>,
                 s.type || <span className="muted">—</span>,
                 <span className="num">{rupees(s.price_paise)}</span>,
                 <span className="num">{s.max_per_booking}</span>,
                 s.requires_capacity ? "Limited daily" : <span className="muted">Unlimited</span>,
                 <button className="abtn abtn-quiet"
                         onClick={() => setOpenForm(openForm === s.id ? null : s.id)}>
                   {s.form?.length ?? 0} · {openForm === s.id ? "close" : "edit form"}
                 </button>,
                 <Pill value={s.is_active ? "active" : "off"} />,
                 <span className="row">
                   <button className="abtn abtn-quiet" onClick={() => {
                     setEditing(s); setName(s.name); setType(s.type ?? "");
                     setDescription(s.description); setPrice(String(s.price_paise / 100));
                     setMaxPer(String(s.max_per_booking));
                     setLimited(s.requires_capacity);
                   }}>Edit</button>
                   <button className="abtn abtn-quiet" onClick={async () => {
                     await api(`/admin/services/${s.id}`,
                               { method: "PATCH", json: { is_active: !s.is_active } });
                     reload();
                   }}>{s.is_active ? "Retire" : "Restore"}</button>
                 </span>,
               ])}
               empty="No services yet. Add one above and it appears on the page." />
      </Panel>

      {openForm && (data ?? []).some((s) => s.id === openForm) && (
        <FormBuilder service={(data ?? []).find((s) => s.id === openForm)}
                     templates={templates ?? []} reload={reload} />
      )}

      {(data ?? []).filter((s) => s.requires_capacity)
                   .map((s) => <Capacity key={s.id} service={s} />)}
    </>
  );
}

/**
 * The questions one service asks.
 *
 * This is the screen that makes a service anything the pandal wants. There is
 * no list of types to pick from, because there is no list.
 */
function FormBuilder({ service, templates, reload }: any) {
  const [key, setKey] = useState("");
  const [label, setLabel] = useState("");
  const [kind, setKind] = useState("text");
  const [options, setOptions] = useState("");
  const [help, setHelp] = useState("");
  const [required, setRequired] = useState(false);
  const [sensitive, setSensitive] = useState(false);
  const [template, setTemplate] = useState(templates[0]?.slug ?? "blank");

  const fields: any[] = service.form ?? [];

  async function move(index: number, by: number) {
    const order = fields.map((f) => f.key);
    const target = index + by;
    if (target < 0 || target >= order.length) return;
    [order[index], order[target]] = [order[target], order[index]];
    await api(`/admin/services/${service.id}/reorder`, { method: "PUT", json: { keys: order } });
    reload();
  }

  return (
    <Panel title={`${service.name} · what the booking form asks`}
           note="Anything you like. A visitor only ever sees these questions, and a booking may only answer these — nothing else is stored.">
      <Table columns={["Question", "Stored as", "Kind", "Required", "Personal", "Order", ""]}
             rows={fields.map((field, index) => [
               <strong>{field.label}</strong>,
               <code>{field.key}</code>,
               field.kind === "select"
                 ? <span>choose one <span className="muted">
                     ({(field.options ?? []).join(", ")})</span></span>
                 : KINDS.find(([v]) => v === field.kind)?.[1] ?? field.kind,
               <Pill value={field.required ? "active" : "off"}
                     label={field.required ? "required" : "optional"} />,
               field.is_sensitive
                 ? <Pill value="pending" label="personal" />
                 : <span className="muted">—</span>,
               <span className="row">
                 <button className="abtn abtn-quiet" onClick={() => move(index, -1)}>↑</button>
                 <button className="abtn abtn-quiet" onClick={() => move(index, 1)}>↓</button>
               </span>,
               <span className="row">
                 <button className="abtn abtn-quiet" onClick={async () => {
                   await api(`/admin/service-fields/${field.id}`,
                             { method: "PATCH", json: { required: !field.required } });
                   reload();
                 }}>{field.required ? "Make optional" : "Make required"}</button>
                 <button className="abtn abtn-quiet" onClick={async () => {
                   await api(`/admin/service-fields/${field.id}`, { method: "DELETE" });
                   reload();
                 }}>Delete</button>
               </span>,
             ])}
             empty="This service asks nothing yet, so a booking would carry no details." />

      <div className="panel-body side-by-side">
        <Form label="Add question" onDone={() => {
                setKey(""); setLabel(""); setOptions(""); setHelp("");
                setRequired(false); setSensitive(false); reload();
              }}
              submit={() => api("/admin/service-fields", { method: "POST", json: {
                service: service.id, label, kind, required, is_sensitive: sensitive,
                help_text: help,
                // Apostrophes are dropped rather than turned into separators,
                // so "Dancer's name" becomes dancer_name and not dancer_s_name.
                // The key is permanent — bookings are stored under it — so it
                // is worth getting right the first time.
                key: (key || label).toLowerCase().replace(/['\u2019]/g, "")
                       .replace(/[^a-z0-9]+/g, "_").replace(/^_|_$/g, ""),
                options: kind === "select"
                  ? options.split(",").map((o) => o.trim()).filter(Boolean) : [],
              }})}>
          <Field label="What to ask" value={label} required
                 placeholder="e.g. Which age group" onChange={(e) => setLabel(e.target.value)} />
          <Select label="Kind of answer" value={kind} onChange={(e) => setKind(e.target.value)}>
            {KINDS.map(([v, l]) => <option key={v} value={v}>{l}</option>)}
          </Select>
          {kind === "select" && (
            <Field label="Choices · comma separated" value={options} required
                   placeholder="Under 12, 12-18, Adult"
                   onChange={(e) => setOptions(e.target.value)} />
          )}
          <Field label="Help text · optional" value={help}
                 onChange={(e) => setHelp(e.target.value)}
                 placeholder="Shown under the question" />
          <label className="inline-check">
            <input type="checkbox" checked={required}
                   onChange={(e) => setRequired(e.target.checked)} />
            Must be answered
          </label>
          <label className="inline-check">
            <input type="checkbox" checked={sensitive}
                   onChange={(e) => setSensitive(e.target.checked)} />
            Personal — a gotra, a disability, a name to be chanted
          </label>
        </Form>

        <Form label="Add these questions" onDone={reload}
              submit={() => api(`/admin/services/${service.id}/apply-template`,
                                { method: "POST", json: { template } })}>
          <Select label="Borrow from a template" value={template}
                  onChange={(e) => setTemplate(e.target.value)}>
            {templates.map((t: any) => <option key={t.slug} value={t.slug}>{t.name}</option>)}
          </Select>
          <p className="hint">
            Adds only what this service does not already ask. A question you have already
            written is never overwritten.
          </p>
        </Form>
      </div>
    </Panel>
  );
}

/**
 * A date range, inclusive, as the day rows the capacity endpoint expects.
 *
 * Kept out of both callers because the add-a-service form and the per-service
 * capacity editor must agree on what "10 Oct to 14 Oct" means, or a service
 * would be bookable on a different set of days than the one the admin saw.
 */
function daysBetween(from: string, to: string, capacity: number) {
  const days: { date: string; capacity: number }[] = [];
  for (const d = new Date(from); d <= new Date(to); d.setDate(d.getDate() + 1)) {
    days.push({ date: d.toISOString().slice(0, 10), capacity });
  }
  return days;
}

function Capacity({ service }: { service: any }) {
  const { data, reload } = useLoad<any[]>(
    () => api(`/admin/services/${service.id}/capacity`), [service.id]);
  const [from, setFrom] = useState("2026-10-10");
  const [to, setTo] = useState("2026-10-14");
  const [places, setPlaces] = useState("20");

  return (
    <Panel title={`${service.name} · places per day`}
           note="An aarti slot has finite seats and a tour is a small group, so a service needs capacity.">
      <div className="panel-body">
        <Form label="Set places" onDone={reload} submit={() =>
          api(`/admin/services/${service.id}/capacity`, {
            method: "PUT", json: { days: daysBetween(from, to, Number(places)) },
          })}>
          <div className="row">
            <Field label="From" type="date" value={from} onChange={(e) => setFrom(e.target.value)} />
            <Field label="To" type="date" value={to} onChange={(e) => setTo(e.target.value)} />
            <Field label="Places each day" value={places} inputMode="numeric"
                   onChange={(e) => setPlaces(e.target.value)} />
          </div>
        </Form>
      </div>
      <Table columns={["Date", "Capacity", "Taken", "Available", "Open"]}
             rows={(data ?? []).map((d) => [
               d.date, <span className="num">{d.capacity}</span>,
               <span className="num">{d.issued_count}</span>,
               <strong className="num">{d.available}</strong>,
               <Pill value={d.is_open ? "active" : "off"} />,
             ])}
             empty="No days configured, so this service cannot be booked." />
    </Panel>
  );
}

function Bookings({ pandal }: P) {
  const { data } = useLoad<any[]>(() => list(`/admin/service-bookings?pandal=${pandal.id}`),
                                  [pandal.id]);
  return (
    <Panel title="Service bookings" note="Including whatever each service's own form captured.">
      <Table columns={["Service", "Date", "Quantity", "Status", "Details"]}
             rows={(data ?? []).map((b) => [
               b.service_name, b.date, <span className="num">{b.quantity}</span>,
               <Pill value={b.status} />,
               <code style={{ fontSize: 12.5 }}>
                 {Object.entries(b.details ?? {}).map(([k, v]) => `${k}: ${v}`).join(" · ") || "—"}
               </code>,
             ])}
             empty="No bookings yet." />
    </Panel>
  );
}

/* ------------------------------------------------------------ Volunteers */

function Volunteers({ pandal }: P) {
  const { data: gates, reload: reloadGates } = useLoad<any[]>(
    () => list(`/admin/gates?pandal=${pandal.id}`), [pandal.id]);
  const { data: volunteers, reload } = useLoad<any[]>(
    () => list(`/admin/volunteers?pandal=${pandal.id}`), [pandal.id]);
  const [gateName, setGateName] = useState("");
  const [volPhone, setVolPhone] = useState("");
  const [volGate, setVolGate] = useState("");

  return (
    <>
      <Panel title="Gates" note="A named scanning position — 'Gate 1', 'Ticket Desk'.">
        <div className="panel-body">
          <Form label="Add gate" onDone={() => { setGateName(""); reloadGates(); }}
                submit={() => api("/admin/gates", { method: "POST",
                                                    json: { pandal: pandal.id, name: gateName } })}>
            <Field label="Gate name" value={gateName} required placeholder="Gate 1"
                   onChange={(e) => setGateName(e.target.value)} />
          </Form>
        </div>
        <Table columns={["Gate", "Active"]}
               rows={(gates ?? []).map((g) => [g.name, <Pill value={g.is_active ? "active" : "off"} />])}
               empty="No gates yet." />
      </Panel>

      <Panel title="Volunteers" note="Deactivating one immediately ends their ability to scan.">
        <div className="panel-body">
          <Form label="Add volunteer"
                onDone={() => { setVolPhone(""); setVolGate(""); reload(); }}
                submit={() => api("/admin/volunteers", {
                  method: "POST",
                  json: { pandal: pandal.id, phone: volPhone, gate: volGate || null },
                })}>
            <Field label="Mobile number" value={volPhone} required placeholder="98765 43210"
                   onChange={(e) => setVolPhone(e.target.value)} />
            <Select label="Assigned gate · optional" value={volGate}
                    onChange={(e) => setVolGate(e.target.value)}>
              <option value="">Unassigned</option>
              {(gates ?? []).map((g: any) => <option key={g.id} value={g.id}>{g.name}</option>)}
            </Select>
          </Form>
          <p className="hint">
            Naming the number is all it takes — the account is created if this person
            has never opened the app, so their first sign-in works.
          </p>
        </div>
        <Table columns={["Name", "Mobile", "Assigned gate", "Status", ""]}
               rows={(volunteers ?? []).map((v) => [
                 v.name || "—", v.user_phone, v.gate_name || "Unassigned",
                 <Pill value={v.is_active ? "active" : "off"} />,
                 <button className="abtn abtn-quiet" onClick={async () => {
                   await api(`/admin/volunteers/${v.id}`,
                             { method: "PATCH", json: { is_active: !v.is_active } });
                   reload();
                 }}>{v.is_active ? "Deactivate" : "Reactivate"}</button>,
               ])}
               empty="No volunteers yet." />
      </Panel>
    </>
  );
}

/* ---------------------------------------------------------- Sponsorship */

function Packages({ pandal }: P) {
  const { data, reload } = useLoad<any[]>(() => list(`/admin/packages?pandal=${pandal.id}`),
                                          [pandal.id]);
  const [name, setName] = useState("");
  const [value, setValue] = useState("");
  const [passes, setPasses] = useState("");
  const [banners, setBanners] = useState("1");
  const [benefits, setBenefits] = useState("");

  return (
    <>
      <Panel title="Add a sponsorship package"
             note="Pass count, value, branding placements and benefits — what a sponsor buys.">
        <div className="panel-body">
          <Form label="Add package"
                onDone={() => { setName(""); setValue(""); setPasses(""); reload(); }}
                submit={() => api("/admin/packages", { method: "POST", json: {
                  pandal: pandal.id, name, slug: name.toLowerCase().replace(/[^a-z0-9]+/g, "-"),
                  value_paise: Math.round(Number(value || 0) * 100),
                  pass_count: Number(passes || 0), banner_placements: Number(banners || 0),
                  benefits,
                }})}>
            <Field label="Package name" value={name} required placeholder="Gold Sponsor"
                   onChange={(e) => setName(e.target.value)} />
            <Field label="Value · rupees" value={value} inputMode="decimal" required
                   onChange={(e) => setValue(e.target.value)} placeholder="50000" />
            <Field label="Passes included" value={passes} inputMode="numeric"
                   onChange={(e) => setPasses(e.target.value)} placeholder="500" />
            <Field label="Branding placements" value={banners} inputMode="numeric"
                   onChange={(e) => setBanners(e.target.value)} />
            <Field label="Benefits" value={benefits} onChange={(e) => setBenefits(e.target.value)}
                   placeholder="Priority entry gate, listed on the Sponsors page" />
          </Form>
        </div>
      </Panel>

      <Panel title="Packages offered">
        <Table columns={["Package", "Value", "Passes", "Placements", "Active"]}
               rows={(data ?? []).map((p) => [
                 <strong>{p.name}</strong>,
                 <span className="num">{rupees(p.value_paise)}</span>,
                 <span className="num">{p.pass_count}</span>,
                 <span className="num">{p.banner_placements}</span>,
                 <Pill value={p.is_active ? "active" : "off"} />,
               ])}
               empty="No packages yet." />
      </Panel>
    </>
  );
}

function Sponsors({ pandal }: P) {
  const { data: allocations, reload } = useLoad<any[]>(() => list("/admin/allocations"), [pandal.id]);
  const { data: packages } = useLoad<any[]>(() => list(`/admin/packages?pandal=${pandal.id}`),
                                            [pandal.id]);
  const { data: organisations } = useLoad<any[]>(() => list("/admin/organisations"), []);

  const [organisation, setOrganisation] = useState("");
  const [pkg, setPkg] = useState("");
  const [passes, setPasses] = useState("");

  const mine = (allocations ?? []).filter((a) => a.pandal === pandal.id);

  return (
    <>
      <Panel title="Allocate passes to a sponsor"
             note="An allocation is an offer. The sponsor's pool is credited only when they accept it.">
        <div className="panel-body">
          <Form label="Allocate" onDone={() => { setPasses(""); reload(); }}
                submit={() => api("/admin/allocations", { method: "POST", json: {
                  pandal: pandal.id, organisation, package: pkg || null,
                  pass_count: Number(passes),
                  value_paise: packages?.find((p) => p.id === pkg)?.value_paise ?? 0,
                }})}>
            <Select label="Sponsor" value={organisation} required
                    onChange={(e) => setOrganisation(e.target.value)}>
              <option value="">Choose a sponsor…</option>
              {(organisations ?? []).filter((o) => !o.is_sub_sponsor)
                .map((o) => <option key={o.id} value={o.id}>{o.name}</option>)}
            </Select>
            <Select label="Package" value={pkg} onChange={(e) => setPkg(e.target.value)}>
              <option value="">No package</option>
              {(packages ?? []).map((p) => <option key={p.id} value={p.id}>{p.name}</option>)}
            </Select>
            <Field label="Passes" value={passes} inputMode="numeric" required
                   onChange={(e) => setPasses(e.target.value)} placeholder="100" />
          </Form>
        </div>
      </Panel>

      <Panel title="Allocation history" note="Every package allocation, newest first.">
        <Table columns={["Sponsor", "Package", "Passes", "Value", "Status"]}
               rows={mine.map((a) => [
                 a.organisation_name, a.package_name || "—",
                 <span className="num">{a.pass_count}</span>,
                 <span className="num">{rupees(a.value_paise)}</span>,
                 <Pill value={a.status} />,
               ])}
               empty="Nothing allocated yet." />
      </Panel>
    </>
  );
}

/* ------------------------------------------------- Live status & lost items */

function Live({ pandal }: P) {
  const { data, reload } = useLoad<any>(() => api(`/admin/pandals/${pandal.id}/live-status`),
                                        [pandal.id]);
  const { data: items, reload: reloadItems } = useLoad<any[]>(
    () => list(`/admin/lost-items?pandal=${pandal.id}`), [pandal.id]);

  const [wait, setWait] = useState("");
  const [crowd, setCrowd] = useState("low");
  const [ready, setReady] = useState(false);

  if (data && !ready) {
    setWait(String(data.estimated_wait_minutes ?? ""));
    setCrowd(data.crowd_level);
    setReady(true);
  }

  return (
    <>
      <Panel title="Current status"
             note="Shown live to visitors browsing this pandal, stamped with how old the reading is.">
        <div className="panel-body">
          <Form label="Update" onDone={reload}
                submit={() => api(`/admin/pandals/${pandal.id}/live-status`, {
                  method: "PUT",
                  json: { estimated_wait_minutes: wait ? Number(wait) : null, crowd_level: crowd },
                })}>
            <Field label="Estimated wait · minutes" value={wait} inputMode="numeric"
                   onChange={(e) => setWait(e.target.value)} />
            <Select label="Live crowd level" value={crowd}
                    onChange={(e) => setCrowd(e.target.value)}>
              <option value="low">Low</option>
              <option value="medium">Medium</option>
              <option value="high">High</option>
            </Select>
          </Form>
        </div>
      </Panel>

      <Panel title="Digital lost & found" note="Visitors see the items still marked lost.">
        <Table columns={["Item", "Where", "Contact", "Status", ""]}
               rows={(items ?? []).map((i) => [
                 i.item, i.location || "—", i.contact_phone || "—", <Pill value={i.status} />,
                 i.status === "lost" ? (
                   <button className="abtn abtn-quiet" onClick={async () => {
                     await api(`/admin/lost-items/${i.id}/mark-found`, { method: "POST" });
                     reloadItems();
                   }}>Mark found</button>
                 ) : null,
               ])}
               empty="Nothing reported." />
      </Panel>
    </>
  );
}

function Support({ pandal }: P) {
  const { data, reload } = useLoad<any[]>(
    () => list(`/admin/support-requests?pandal=${pandal.id}`), [pandal.id]);
  return (
    <Panel title="Support & feedback" note="Submitted from the app and from the pandal's page.">
      <Table columns={["Name", "Contact", "Subject", "Message", "Status", ""]}
             rows={(data ?? []).map((r) => [
               r.name, r.contact_phone, r.subject.replace(/_/g, " "), r.message,
               <Pill value={r.status} />,
               r.status !== "resolved" ? (
                 <button className="abtn abtn-quiet" onClick={async () => {
                   await api(`/admin/support-requests/${r.id}/resolve`, { method: "POST" });
                   reload();
                 }}>Mark resolved</button>
               ) : null,
             ])}
             empty="Nothing outstanding." />
    </Panel>
  );
}

/**
 * Writing the page.
 *
 * The form is generated from `/admin/pandals/page-schema`, not hard-coded here.
 * A block's shape lives in one place on the server, so adding a field to the
 * hero is one entry there rather than an edit in the model, the renderer and
 * this file — which is how the three of them drifted apart before.
 */
function PageContent({ pandal }: P) {
  const { data: schema } = useLoad<any[]>(() => api("/admin/pandals/page-schema"), []);
  const { data: existing, reload } =
    useLoad<any[]>(() => api(`/admin/pandals/${pandal.id}/blocks`), [pandal.id]);

  const written = new Map((existing ?? []).map((b) => [b.kind, b]));

  return (
    <>
      <Panel title="Your page"
             note={`Everything a visitor reads at ${pandalDisplayHost(pandal.slug)}. Changes are live as soon as you save.`}
             actions={
               <a className="abtn abtn-quiet" target="_blank" rel="noreferrer"
                  href={pandalHref(pandal.slug)}>Open my page ↗</a>
             }>
        <div className="panel-body">
          <p className="hint">
            Each section below is one part of the page, in the order a visitor scrolls
            through them. A section you have not written yet shows the wording we started
            you off with.
          </p>
        </div>
      </Panel>

      {(schema ?? []).map((block) => (
        <BlockEditor key={block.kind} pandal={pandal} block={block}
                     saved={written.get(block.kind)} reload={reload} />
      ))}
    </>
  );
}

function BlockEditor({ pandal, block, saved, reload }: any) {
  const [content, setContent] = useState<Record<string, any>>(saved?.content ?? {});
  const [visible, setVisible] = useState(saved?.is_visible ?? true);

  const set = (key: string, value: any) =>
    setContent((current) => ({ ...current, [key]: value }));

  return (
    <Panel title={block.name} note={block.description}
           actions={
             <label className="inline-check">
               <input type="checkbox" checked={visible} onChange={async (e) => {
                 setVisible(e.target.checked);
                 await api(`/admin/pandals/${pandal.id}/blocks/${block.kind}`, {
                   method: "PATCH", json: { is_visible: e.target.checked },
                 });
                 reload();
               }} />
               Show on my page
             </label>
           }>
      <div className="panel-body">
        <Form label="Save this section" onDone={reload}
              submit={() => api(`/admin/pandals/${pandal.id}/blocks/${block.kind}`, {
                method: "PATCH", json: { content },
              })}>
          {block.fields.map((field: any) => (
            <BlockField key={field.key} field={field} value={content[field.key]}
                        onChange={(v: any) => set(field.key, v)} />
          ))}
        </Form>
      </div>
    </Panel>
  );
}

/** One field of one block, rendered according to its kind. */
function BlockField({ field, value, onChange }: any) {
  if (field.kind === "textarea") {
    return (
      <label>
        <span>{field.label}</span>
        <textarea rows={3} value={value ?? ""} onChange={(e) => onChange(e.target.value)} />
        {field.help_text && <small className="hint">{field.help_text}</small>}
      </label>
    );
  }

  if (field.kind === "list") {
    // Stored as a list, edited as lines — nobody wants to type JSON to change
    // the words that scroll under their hero.
    return (
      <label>
        <span>{field.label}</span>
        <textarea rows={4} value={(value ?? []).join("\n")}
                  onChange={(e) => onChange(e.target.value.split("\n")
                                              .map((line: string) => line.trim())
                                              .filter(Boolean))} />
        {field.help_text && <small className="hint">{field.help_text}</small>}
      </label>
    );
  }

  if (field.kind === "pillars") {
    const pillars: any[] = value ?? [];
    const edit = (index: number, key: string, next: string) =>
      onChange(pillars.map((p, i) => (i === index ? { ...p, [key]: next } : p)));

    return (
      <div className="pillars-editor">
        <span className="field-label">{field.label}</span>
        {field.help_text && <small className="hint">{field.help_text}</small>}
        {pillars.map((pillar, index) => (
          <div className="pillar-row" key={index}>
            <input value={pillar.title ?? ""} placeholder="Title"
                   onChange={(e) => edit(index, "title", e.target.value)} />
            <input value={pillar.body ?? ""} placeholder="One sentence"
                   onChange={(e) => edit(index, "body", e.target.value)} />
            <button type="button" className="abtn abtn-quiet"
                    onClick={() => onChange(pillars.filter((_, i) => i !== index))}>
              Remove
            </button>
          </div>
        ))}
        <button type="button" className="abtn abtn-quiet"
                onClick={() => onChange([...pillars, { title: "", body: "" }])}>
          Add another
        </button>
      </div>
    );
  }

  return (
    <label>
      <span>{field.label}</span>
      <input value={value ?? ""} onChange={(e) => onChange(e.target.value)} />
      {field.help_text && <small className="hint">{field.help_text}</small>}
    </label>
  );
}

/* -------------------------------------------------------------- Appearance */

const SWATCHES: [string, string, string][] = [
  ["primary_colour", "Primary", "Headings, buttons, the accents people notice first."],
  ["accent_colour", "Accent", "Highlights and secondary detail."],
  ["surface_colour", "Background", "The paper your page is printed on."],
  ["ink_colour", "Text", "The colour your words are set in."],
];

const PALETTES: [string, Record<string, string>][] = [
  // The platform's own, first: a committee with no opinion should land on brand.
  ["eDurgaPuja", { primary_colour: "#7B0D1E", accent_colour: "#D4AF37",
                   surface_colour: "#FAF6EE", ink_colour: "#241A18" }],
  ["Terracotta", { primary_colour: "#B45F1E", accent_colour: "#E0A66A",
                   surface_colour: "#FBF3E8", ink_colour: "#3A1D0C" }],
  ["Alta red", { primary_colour: "#9A2B23", accent_colour: "#E8A87C",
                 surface_colour: "#FDF4EE", ink_colour: "#3B1310" }],
  ["Indigo", { primary_colour: "#2F3E8C", accent_colour: "#C9B57B",
               surface_colour: "#F4F4FA", ink_colour: "#171B33" }],
  ["Palash", { primary_colour: "#C2410C", accent_colour: "#F4B860",
               surface_colour: "#FFF7ED", ink_colour: "#3A1A08" }],
  ["Forest", { primary_colour: "#1F5C43", accent_colour: "#D9B44A",
               surface_colour: "#F2F7F2", ink_colour: "#12261C" }],
];

/** Your colours, with the page itself as the preview. */
function Appearance({ pandal }: P) {
  const { data, reload } = useLoad<any>(() => api(`/admin/pandals/${pandal.id}/brand`),
                                        [pandal.id]);
  const [draft, setDraft] = useState<Record<string, string> | null>(null);

  const brand = draft ?? data;
  if (!brand) return <p className="empty">Loading…</p>;

  const set = (key: string, value: string) => setDraft({ ...brand, [key]: value });

  return (
    <>
      <Panel title="Your colours"
             note="These are your committee's, not ours. The preview below is the real page, drawn with what you have picked.">
        <div className="panel-body">
          <Form label="Save colours" onDone={() => { setDraft(null); reload(); }}
                submit={() => api(`/admin/pandals/${pandal.id}/brand`,
                                  { method: "PATCH", json: brand })}>
            {SWATCHES.map(([key, label, hint]) => (
              <label key={key} className="swatch-row">
                <span>{label}</span>
                <div className="swatch-controls">
                  <input type="color" value={brand[key] ?? "#000000"}
                         onChange={(e) => set(key, e.target.value)} />
                  <input className="swatch-hex" value={brand[key] ?? ""}
                         onChange={(e) => set(key, e.target.value)} />
                </div>
                <small className="hint">{hint}</small>
              </label>
            ))}
          </Form>

          <div className="palette-row">
            <span className="field-label">Or start from one of these</span>
            <div className="row">
              {PALETTES.map(([name, palette]) => (
                <button key={name} type="button" className="palette"
                        onClick={() => setDraft({ ...brand, ...palette })}>
                  <span className="palette-chips">
                    {["primary_colour", "accent_colour", "surface_colour"].map((k) => (
                      <i key={k} style={{ background: palette[k] }} />
                    ))}
                  </span>
                  {name}
                </button>
              ))}
            </div>
          </div>
        </div>
      </Panel>

      <Panel title="How it looks" note="A live sketch of your page in these colours.">
        <div className="panel-body">
          <div className="brand-preview"
               style={{
                 background: brand.surface_colour,
                 color: brand.ink_colour,
                 borderColor: brand.accent_colour,
               }}>
            <p className="preview-eyebrow" style={{ color: brand.primary_colour }}>
              {pandal.name} · Durga Puja
            </p>
            <h3 style={{ color: brand.ink_colour }}>Durga Puja at {pandal.name}</h3>
            <p className="preview-body">
              A few lines about this year's puja — the theme, the idol, what makes the
              pandal worth the queue.
            </p>
            <div className="row">
              <span className="preview-btn"
                    style={{ background: brand.primary_colour, color: brand.surface_colour }}>
                Donate Now
              </span>
              <span className="preview-btn preview-btn-ghost"
                    style={{ borderColor: brand.primary_colour, color: brand.primary_colour }}>
                Explore Services
              </span>
            </div>
          </div>
        </div>
      </Panel>
    </>
  );
}

/* ----------------------------------------------------------------- Details */

/** Name, contact, theme, dates, and what the page offers at all. */
function Details({ pandal }: P) {
  const { data, reload } = useLoad<any>(() => api(`/admin/pandals/${pandal.id}`), [pandal.id]);
  const [draft, setDraft] = useState<Record<string, any> | null>(null);

  const row = draft ?? data;
  if (!row) return <p className="empty">Loading…</p>;
  const set = (key: string, value: any) => setDraft({ ...row, [key]: value });

  const field = (key: string, label: string, extra: any = {}) => (
    <Field label={label} value={row[key] ?? ""}
           onChange={(e: any) => set(key, e.target.value)} {...extra} />
  );

  return (
    <>
      <Panel title="Your committee"
             note="What appears across the page and in search results.">
        <div className="panel-body">
          <Form label="Save" onDone={() => { setDraft(null); reload(); }}
                submit={() => api(`/admin/pandals/${pandal.id}`,
                                  { method: "PATCH", json: draft ?? {} })}>
            {field("name", "Pandal name")}
            {field("committee_name", "Committee's full name")}
            <div className="row">
              {field("theme_name", "This year's theme")}
              {field("theme_name_local", "Theme in Bengali")}
            </div>
            {field("address", "Address")}
            <div className="row">
              {field("contact_name", "Who to contact")}
              {field("contact_phone", "Contact number")}
            </div>
            {field("contact_email", "Contact email")}
            <div className="row">
              {field("opens_on", "Open from", { type: "date" })}
              {field("closes_on", "Until", { type: "date" })}
            </div>
            {field("seo_title", "Title in search results")}
            {field("seo_description", "Description in search results")}
            <p className="hint">
              Your address is <code>{pandalDisplayHost(row.slug)}</code>. It cannot be changed
              here — people have already been given it. Ask us for a rename and the old one
              keeps working.
            </p>
          </Form>
        </div>
      </Panel>

      <Panel title="What your page offers"
             note="Turning one off hides that whole section. Nothing you have set up is lost.">
        <div className="panel-body">
          {[["accepts_donations", "Accept donations"],
            ["offers_services", "Offer value-added services"],
            ["sells_passes", "Sell entry passes"]].map(([key, label]) => (
            <label key={key} className="inline-check toggle-row">
              <input type="checkbox" checked={Boolean(row[key])} onChange={async (e) => {
                set(key, e.target.checked);
                await api(`/admin/pandals/${pandal.id}`,
                          { method: "PATCH", json: { [key]: e.target.checked } });
                reload();
              }} />
              {label}
            </label>
          ))}
        </div>
      </Panel>
    </>
  );
}

/** The timings-and-directions strip. */
function VisitFacts({ pandal }: P) {
  const { data, reload } = useLoad<any[]>(() => list(`/admin/visit-facts?pandal=${pandal.id}`),
                                          [pandal.id]);
  const [label, setLabel] = useState("");
  const [value, setValue] = useState("");

  return (
    <Panel title="Plan your visit"
           note="The short facts under your visit section — timings, nearest metro, what to expect.">
      <div className="panel-body">
        <Form label="Add" onDone={() => { setLabel(""); setValue(""); reload(); }}
              submit={() => api("/admin/visit-facts", { method: "POST", json: {
                pandal: pandal.id, label, value, sort_order: (data?.length ?? 0) + 1,
              }})}>
          <Field label="Label" value={label} required placeholder="e.g. Nearest Metro"
                 onChange={(e) => setLabel(e.target.value)} />
          <Field label="Value" value={value} required placeholder="e.g. Kalighat, 12 minutes"
                 onChange={(e) => setValue(e.target.value)} />
        </Form>
      </div>
      <Table columns={["Label", "Value", ""]}
             rows={(data ?? []).map((f) => [
               <strong>{f.label}</strong>, f.value,
               <button className="abtn abtn-quiet" onClick={async () => {
                 await api(`/admin/visit-facts/${f.id}`, { method: "DELETE" });
                 reload();
               }}>Remove</button>,
             ])}
             empty="Nothing yet." />
    </Panel>
  );
}

/* ------------------------------------------------------------------ Passes */

const PRODUCTS: [string, string][] = [
  ["individual", "Individual"],
  ["group", "Group"],
  ["city", "City"],
];

/**
 * What the pandal sells, and how many it will let in.
 *
 * Three things on one screen because they are one decision: the categories are
 * the pandal's own names for who a holder is, the grid says what each costs and
 * when, and the day capacity is the ceiling every row sits under.
 */
function PassSetup({ pandal }: P) {
  const { data: categories, reload: reloadCategories } =
    useLoad<any[]>(() => list(`/admin/pass-categories?pandal=${pandal.id}`), [pandal.id]);
  const { data: configs, reload: reloadConfigs } =
    useLoad<any[]>(() => list(`/admin/pass-configs?pandal=${pandal.id}`), [pandal.id]);
  const { data: days, reload: reloadDays } =
    useLoad<any[]>(() => api(`/admin/pandals/${pandal.id}/day-capacity`), [pandal.id]);

  const [name, setName] = useState("");
  const [description, setDescription] = useState("");

  const [product, setProduct] = useState("individual");
  const [categoryId, setCategoryId] = useState("");
  const [price, setPrice] = useState("");
  const [maxParty, setMaxParty] = useState("1");
  const [fromDate, setFromDate] = useState("2026-10-10");
  const [toDate, setToDate] = useState("2026-10-14");
  const [fromTime, setFromTime] = useState("18:00");
  const [toTime, setToTime] = useState("21:00");
  const [editing, setEditing] = useState<any>(null);

  const [capFrom, setCapFrom] = useState("2026-10-10");
  const [capTo, setCapTo] = useState("2026-10-14");
  const [places, setPlaces] = useState("2000");

  // A City Pass has a date but no time (D3) — the database refuses one that
  // carries a time, so the form must not offer one.
  const isCity = product === "city";

  if (!pandal.sells_passes) {
    return (
      <Panel title="Passes are switched off"
             note="A committee turns passes on when it decides to sell them; nothing else changes.">
        <div className="panel-body">
          <p className="hint" style={{ marginBottom: 16 }}>
            Turning this on makes the pass section appear on your landing page. You can
            configure what you sell first and switch it on when you are ready.
          </p>
          <Form label="Start selling passes" onDone={() => window.location.reload()}
                submit={() => api(`/admin/pandals/${pandal.id}`,
                                  { method: "PATCH", json: { sells_passes: true } })}>
            <p className="hint">Your categories and prices are kept either way.</p>
          </Form>
        </div>
      </Panel>
    );
  }

  return (
    <>
      <Panel title="Who your passes are for"
             note="Your own names — Sponsor, VIP, Para Pass, Senior Citizen, Donor, anything else.">
        <div className="panel-body">
          <Form label="Add category"
                onDone={() => { setName(""); setDescription(""); reloadCategories(); }}
                submit={() => api("/admin/pass-categories", { method: "POST", json: {
                  pandal: pandal.id, name, description,
                  slug: name.toLowerCase().replace(/[^a-z0-9]+/g, "-"),
                }})}>
            <Field label="Name" value={name} required placeholder="e.g. Para Pass"
                   onChange={(e) => setName(e.target.value)} />
            <Field label="Description" value={description}
                   onChange={(e) => setDescription(e.target.value)}
                   placeholder="Who it is for" />
          </Form>
        </div>
        <Table columns={["Category", "Description", "Active", ""]}
               rows={(categories ?? []).map((c) => [
                 <strong>{c.name}</strong>, c.description || "—",
                 <Pill value={c.is_active ? "active" : "off"} />,
                 <button className="abtn abtn-quiet" onClick={async () => {
                   await api(`/admin/pass-categories/${c.id}`,
                             { method: "PATCH", json: { is_active: !c.is_active } });
                   reloadCategories();
                 }}>{c.is_active ? "Retire" : "Restore"}</button>,
               ])}
               empty="None yet. Add one above before setting a price." />
      </Panel>

      <Panel title={editing ? `Edit ${editing.category_name} · ${editing.product_display}`
                            : "What is on sale"}
             note="Product then category. The platform fixes the three products; the category is yours and carries the price."
             actions={editing
               ? <button className="abtn abtn-quiet" onClick={() => setEditing(null)}>Cancel</button>
               : undefined}>
        <div className="panel-body">
          <Form label={editing ? "Save changes" : "Put on sale"}
                onDone={() => { setPrice(""); setEditing(null); reloadConfigs(); }}
                submit={() => {
                  const body: Record<string, unknown> = {
                    pandal: pandal.id, category: categoryId || categories?.[0]?.id,
                    product, from_date: fromDate, to_date: toDate,
                    price_paise: Math.round(Number(price || 0) * 100),
                    max_party_size: Number(maxParty || 1),
                    from_time: isCity ? null : fromTime,
                    to_time: isCity ? null : toTime,
                  };
                  return editing
                    ? api(`/admin/pass-configs/${editing.id}`, { method: "PATCH", json: body })
                    : api("/admin/pass-configs", { method: "POST", json: body });
                }}>
            <Select label="Product" value={product} onChange={(e) => setProduct(e.target.value)}>
              {PRODUCTS.map(([v, l]) => <option key={v} value={v}>{l}</option>)}
            </Select>
            <Select label="Category" value={categoryId}
                    onChange={(e) => setCategoryId(e.target.value)}>
              {(categories ?? []).map((c) => (
                <option key={c.id} value={c.id}>{c.name}</option>
              ))}
            </Select>
            <Field label="Price · rupees" value={price} inputMode="decimal" required
                   onChange={(e) => setPrice(e.target.value)} placeholder="300" />
            {product === "group" && (
              <Field label="Maximum people on one pass" value={maxParty} inputMode="numeric"
                     onChange={(e) => setMaxParty(e.target.value)} />
            )}
            <div className="row">
              <Field label="On sale from" type="date" value={fromDate}
                     onChange={(e) => setFromDate(e.target.value)} />
              <Field label="To" type="date" value={toDate}
                     onChange={(e) => setToDate(e.target.value)} />
            </div>
            {isCity ? (
              <p className="hint">
                A City Pass carries a date and no time, and admits the holder to every pandal
                in the city selling passes that day.
              </p>
            ) : (
              <div className="row">
                <Field label="Entry from" type="time" value={fromTime}
                       onChange={(e) => setFromTime(e.target.value)} />
                <Field label="Until" type="time" value={toTime}
                       onChange={(e) => setToTime(e.target.value)} />
              </div>
            )}
          </Form>
        </div>
        <Table columns={["Product", "Category", "Price", "Party", "Dates", "Time", "Active", ""]}
               rows={(configs ?? []).map((c) => [
                 <strong>{c.product_display}</strong>, c.category_name,
                 <span className="num">{rupees(c.price_paise)}</span>,
                 <span className="num">{c.max_party_size}</span>,
                 <span className="num">{c.from_date} → {c.to_date}</span>,
                 c.from_time ? `${c.from_time.slice(0, 5)}–${c.to_time?.slice(0, 5)}` : "Any time",
                 <Pill value={c.is_active ? "active" : "off"} />,
                 <span className="row">
                   <button className="abtn abtn-quiet" onClick={() => {
                     setEditing(c); setProduct(c.product); setCategoryId(c.category);
                     setPrice(String(c.price_paise / 100));
                     setMaxParty(String(c.max_party_size));
                     setFromDate(c.from_date); setToDate(c.to_date);
                     setFromTime(c.from_time?.slice(0, 5) ?? "18:00");
                     setToTime(c.to_time?.slice(0, 5) ?? "21:00");
                   }}>Edit</button>
                   <button className="abtn abtn-quiet" onClick={async () => {
                     await api(`/admin/pass-configs/${c.id}`,
                               { method: "PATCH", json: { is_active: !c.is_active } });
                     reloadConfigs();
                   }}>{c.is_active ? "Withdraw" : "Restore"}</button>
                 </span>,
               ])}
               empty="Nothing on sale yet." />
      </Panel>

      <Panel title="How many you will admit each day"
             note="Your own ceiling. Every pass sold, and every one a sponsor gives away, comes out of this.">
        <div className="panel-body">
          <Form label="Set places" onDone={reloadDays} submit={() => {
            const rows: { date: string; capacity: number }[] = [];
            for (const d = new Date(capFrom); d <= new Date(capTo); d.setDate(d.getDate() + 1)) {
              rows.push({ date: d.toISOString().slice(0, 10), capacity: Number(places) });
            }
            return api(`/admin/pandals/${pandal.id}/day-capacity`,
                       { method: "PUT", json: { days: rows } });
          }}>
            <div className="row">
              <Field label="From" type="date" value={capFrom}
                     onChange={(e) => setCapFrom(e.target.value)} />
              <Field label="To" type="date" value={capTo}
                     onChange={(e) => setCapTo(e.target.value)} />
              <Field label="Places each day" value={places} inputMode="numeric"
                     onChange={(e) => setPlaces(e.target.value)} />
            </div>
          </Form>
        </div>
        <Table columns={["Date", "Capacity", "Issued", "Available", "Open"]}
               rows={(days ?? []).map((d) => [
                 d.date, <span className="num">{d.capacity}</span>,
                 <span className="num">{d.issued_count}</span>,
                 <strong className="num">{d.available}</strong>,
                 <Pill value={d.is_open ? "active" : "off"} />,
               ])}
               empty="No days set, so nothing can be sold." />
      </Panel>
    </>
  );
}

/** Passes & Payments: what has been sold, and what it was worth. */
function PassSales({ pandal }: P) {
  const { data: summary } = useLoad<any>(() => api(`/admin/pass-summary?pandal=${pandal.id}`),
                                         [pandal.id]);
  const [query, setQuery] = useState("");
  const { data: passes } = useLoad<any[]>(
    () => list(`/admin/passes?pandal=${pandal.id}${query ? `&q=${query}` : ""}`),
    [pandal.id, query]);

  return (
    <>
      <div className="tiles">
        <Tile label="Places for sale" value={summary?.capacity ?? "—"} />
        <Tile label="Issued" value={summary?.issued ?? "—"} />
        <Tile label="Still available" value={summary?.available ?? "—"} />
        <Tile label="Pass revenue"
              value={summary ? rupees(summary.revenue_paise) : "—"} />
        <Tile label="Yet to visit" value={summary?.legs_pending ?? "—"} />
        <Tile label="Came in" value={summary?.legs_visited ?? "—"} />
      </div>

      <Panel title="By category" note="Which of your categories people are actually buying.">
        <Table columns={["Category", "Passes"]}
               rows={(summary?.by_category ?? []).map((row: any) => [
                 row.category, <span className="num">{row.count}</span>,
               ])}
               empty="Nothing issued yet." />
      </Panel>

      <Panel title="Passes issued"
             note="A City Pass appears here for your pandal too — you see its leg, not the whole itinerary.">
        <div className="panel-body">
          <div className="form">
            <Field label="Find a pass code" value={query} placeholder="EDP-2026-…"
                   onChange={(e) => setQuery(e.target.value)} />
          </div>
        </div>
        <Table columns={["Pass", "Product", "Category", "People", "Source", "Where it stands",
                         "Status"]}
               rows={(passes ?? []).map((p) => [
                 <code>{p.pass_code}</code>, p.product, p.category_name,
                 <span className="num">{p.party_size}</span>,
                 p.source.replace(/_/g, " "),
                 <span className="row">
                   {p.legs.map((leg: any) => (
                     <Pill key={leg.id}
                           value={leg.state === "visited" ? "active"
                                  : leg.state === "void" ? "off" : "pending"}
                           label={`${leg.pandal_name} · ${leg.state}`} />
                   ))}
                 </span>,
                 <Pill value={p.status === "active" ? "active"
                              : p.status === "used" ? "completed" : "off"} />,
               ])}
               empty={query ? "No pass matches that code." : "Nothing issued yet."} />
      </Panel>
    </>
  );
}

const SCAN_TONE: Record<string, string> = {
  admitted: "active", manual_override: "pending",
  duplicate: "rejected", expired: "rejected", invalid: "rejected",
};

/** Entry & QR logs: every scan, whatever its outcome (FR-110). */
function EntryLog({ pandal }: P) {
  const [result, setResult] = useState("");
  const { data: scans } = useLoad<any[]>(
    () => list(`/admin/scans?pandal=${pandal.id}${result ? `&result=${result}` : ""}`),
    [pandal.id, result]);

  const counts: Record<string, number> = {};
  for (const scan of scans ?? []) counts[scan.result] = (counts[scan.result] ?? 0) + 1;

  return (
    <>
      <Panel title="Every scan at your gates"
             note="Refusals are recorded as often as they happen — the number worth reading the morning after is how many were turned away, and why."
             actions={
               <Select label="" value={result} onChange={(e) => setResult(e.target.value)}>
                 <option value="">All results</option>
                 <option value="admitted">Admitted</option>
                 <option value="duplicate">Already used</option>
                 <option value="expired">Code expired</option>
                 <option value="invalid">Not valid</option>
                 <option value="manual_override">Admitted by exception</option>
               </Select>
             }>
        <Table columns={["When", "Gate", "Pass", "Result", "Volunteer", "Device", "Reason"]}
               rows={(scans ?? []).map((scan) => [
                 new Date(scan.scanned_at).toLocaleString("en-IN",
                   { day: "numeric", month: "short", hour: "2-digit", minute: "2-digit" }),
                 scan.gate_name,
                 scan.pass_code ? <code>{scan.pass_code}</code> : <span className="muted">—</span>,
                 <Pill value={SCAN_TONE[scan.result] ?? "off"}
                       label={scan.result.replace(/_/g, " ")} />,
                 scan.volunteer_name || "—",
                 scan.device_id || "—",
                 scan.override_reason || "—",
               ])}
               empty="No scans yet." />
      </Panel>
    </>
  );
}

/* ------------------------------------------------------------------- People */

/**
 * Who can sign in to this committee's console.
 *
 * A committee manages its own people. The alternative is a support ticket every
 * time a volunteer joins, which is how one login ends up shared by nine.
 */
function Staff({ pandal }: P) {
  const { data, reload } = useLoad<any[]>(() => list("/admin/staff"), [pandal.id]);
  const [phone, setPhone] = useState("");

  const mine = (data ?? []).filter((row) => row.pandal === pandal.id);

  return (
    <Panel title="Who can sign in"
           note="Anyone here can open this console for your pandal. There is no password to send — they sign in with their number and a one-time code.">
      <div className="panel-body">
        <Form label="Give access" onDone={() => { setPhone(""); reload(); }}
              submit={() => api("/admin/staff", { method: "POST", json: {
                phone, role: "pandal_admin", pandal: pandal.id,
              }})}>
          <Field label="Their mobile number" value={phone} required
                 placeholder="+91 98765 43210" onChange={(e) => setPhone(e.target.value)} />
          <p className="hint">
            They do not need an account first. Their number is the invitation.
          </p>
        </Form>
      </div>
      <Table columns={["Number", "Name", "Access", ""]}
             rows={mine.map((row) => [
               <span className="num">{row.user_phone}</span>,
               row.user_name || <span className="muted">Not signed in yet</span>,
               <Pill value="active" label={row.role_display} />,
               <button className="abtn abtn-quiet" onClick={async () => {
                 await api(`/admin/staff/${row.id}`, { method: "DELETE" });
                 reload();
               }}>Remove</button>,
             ])}
             empty="Nobody yet." />
    </Panel>
  );
}
