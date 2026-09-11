"use client";

import { useEffect, useState } from "react";

import { api, list, rupees } from "@/lib/admin";

import { pandalDisplayHost, pandalHref } from "@/lib/urls";

import { Field, Form, Panel, Pill, Select, Table, Tile } from "./ui";

export function SuperPanel({ screen }: { screen: string }) {
  switch (screen) {
    case "pandals": return <Pandals />;
    case "creatives": return <Creatives />;
    case "sponsors": return <Sponsors />;
    case "issuances": return <Issuances />;
    case "users": return <Users />;
    default: return <Dashboard />;
  }
}

function Dashboard() {
  const [data, setData] = useState<any>(null);
  useEffect(() => { api("/admin/dashboard").then(setData); }, []);
  if (!data) return <p className="empty">Loading…</p>;

  return (
    <>
      <div className="tiles">
        <Tile label="Pandals" value={data.pandals.total} />
        <Tile label="Published" value={data.pandals.published} />
        <Tile label="Selling passes" value={data.pandals.selling_passes} />
        <Tile label="Registered users" value={data.users} />
        <Tile label="Revenue" value={rupees(data.revenue_paise)} />
        <Tile label="Donations received" value={data.donations.count} />
        <Tile label="Service bookings" value={data.service_bookings} />
        <Tile label="Sponsors" value={data.sponsors.organisations} />
      </div>

      <Panel title="Needs attention" note="Everything waiting on somebody at the platform.">
        <Table columns={["Queue", "Outstanding"]}
               rows={[
                 ["Support requests", <span className="num">{data.support.new}</span>],
                 ["Lost items unclaimed", <span className="num">{data.lost_items.open}</span>],
                 ["Allocations awaiting a sponsor",
                  <span className="num">{data.sponsors.pending_allocations}</span>],
                 ["Creatives awaiting review",
                  <span className="num">{data.branding.pending_review}</span>],
               ]}
               empty="" />
      </Panel>
    </>
  );
}

function Pandals() {
  const [rows, setRows] = useState<any[]>([]);
  const [cities, setCities] = useState<any[]>([]);
  const [nonce, setNonce] = useState(0);
  useEffect(() => { list("/admin/pandals").then(setRows); }, [nonce]);
  useEffect(() => { list("/admin/cities").then(setCities); }, [nonce]);

  const [name, setName] = useState("");
  const [slug, setSlug] = useState("");
  const [committee, setCommittee] = useState("");
  const [cityId, setCityId] = useState("");
  const [localityId, setLocalityId] = useState("");
  const [contactName, setContactName] = useState("");
  const [contactPhone, setContactPhone] = useState("");
  const [adminPhone, setAdminPhone] = useState("");

  const city = cities.find((c) => c.id === (cityId || cities[0]?.id));
  // The subdomain is derived from the name until somebody types one, so the
  // common case is three fields and a button.
  const suggested = name.toLowerCase().replace(/[^a-z0-9]+/g, "-").replace(/^-|-$/g, "");

  return (
    <>
      <Panel title="Onboard a committee"
             note="Creates the pandal, its subdomain, a starting palette and a full page of placeholder text — so the committee opens their site and sees something to edit rather than a blank screen.">
        <div className="panel-body">
          <Form label="Create pandal"
                onDone={() => { setName(""); setSlug(""); setCommittee("");
                                setContactName(""); setContactPhone(""); setAdminPhone("");
                                setNonce((n) => n + 1); }}
                submit={async () => {
                  const created = await api<any>("/admin/pandals", { method: "POST", json: {
                    name, committee_name: committee,
                    slug: slug || suggested || undefined,
                    city: cityId || cities[0]?.id,
                    locality: localityId || null,
                    contact_name: contactName, contact_phone: contactPhone,
                    accepts_donations: true, offers_services: true,
                  }});
                  if (adminPhone) {
                    // Their own way in, straight away. Without this the
                    // committee has a site and no door to it.
                    await api("/admin/staff", { method: "POST", json: {
                      phone: adminPhone, role: "pandal_admin", pandal: created.id,
                    }});
                  }
                  return created;
                }}>
            <Field label="Pandal name" value={name} required
                   placeholder="e.g. Shobhabazar Rajbari"
                   onChange={(e) => setName(e.target.value)} />
            <Field label="Subdomain" value={slug}
                   placeholder={suggested || "shobhabazar-rajbari"}
                   onChange={(e) => setSlug(e.target.value)} />
            <p className="hint">
              Their page will be{" "}
              <code>{pandalDisplayHost((slug || suggested) || "…")}</code>.
              Leave blank to use the name. This cannot be changed afterwards without a
              redirect, so it is worth getting right.
            </p>
            <Field label="Committee's full name" value={committee}
                   placeholder="e.g. Shobhabazar Rajbari Sarbojanin"
                   onChange={(e) => setCommittee(e.target.value)} />
            <div className="row">
              <Select label="City" value={cityId || cities[0]?.id || ""}
                      onChange={(e) => { setCityId(e.target.value); setLocalityId(""); }}>
                {cities.map((c) => <option key={c.id} value={c.id}>{c.name}</option>)}
              </Select>
              <Select label="Locality" value={localityId}
                      onChange={(e) => setLocalityId(e.target.value)}>
                <option value="">Not sure yet</option>
                {(city?.localities ?? []).map((l: any) => (
                  <option key={l.id} value={l.id}>{l.name}</option>
                ))}
              </Select>
            </div>
            <div className="row">
              <Field label="Who to contact" value={contactName}
                     onChange={(e) => setContactName(e.target.value)} />
              <Field label="Their number" value={contactPhone}
                     onChange={(e) => setContactPhone(e.target.value)} />
            </div>
            <Field label="Sign-in number for their admin" value={adminPhone}
                   placeholder="+91 98765 43210"
                   onChange={(e) => setAdminPhone(e.target.value)} />
            <p className="hint">
              Optional, but without it the committee has a site and no way into it. They
              sign in with this number and a one-time code — there is no password to send.
            </p>
          </Form>
        </div>
      </Panel>

    <Panel title="Pandals" note="Every committee on the platform, and what each one offers.">
      <Table columns={["Pandal", "Where", "Site", "Donations", "Services", "Passes",
                       "Status", ""]}
             rows={rows.map((p: any) => [
               <strong>{p.name}</strong>,
               <span className="muted">
                 {[p.locality_name, p.city_name].filter(Boolean).join(", ") || "—"}
               </span>,
               <a href={pandalHref(p.slug)} target="_blank" rel="noreferrer">
                 <code style={{ fontSize: 11 }}>{p.slug}</code>
               </a>,
               <Pill value={p.accepts_donations ? "active" : "off"} />,
               <Pill value={p.offers_services ? "active" : "off"} />,
               <Pill value={p.sells_passes ? "active" : "off"} />,
               <Pill value={p.publication_status} />,
               p.publication_status !== "published" ? (
                 <button className="abtn abtn-quiet" onClick={async () => {
                   await api(`/admin/pandals/${p.id}/publish`,
                             { method: "POST", json: { status: "published" } });
                   setNonce((n) => n + 1);
                 }}>Publish</button>
               ) : null,
             ])}
             empty="No pandals yet." />
    </Panel>
    </>
  );
}

function Creatives() {
  const [rows, setRows] = useState<any[]>([]);
  const [placements, setPlacements] = useState<any[]>([]);
  const [orgs, setOrgs] = useState<any[]>([]);
  const [pandals, setPandals] = useState<any[]>([]);
  const [nonce, setNonce] = useState(0);
  const [editing, setEditing] = useState<any>(null);

  const blank = { name: "", organisation: "", pandal: "", placement: "",
                  start_date: "", end_date: "", price: "", target_url: "" };
  const [draft, setDraft] = useState<any>(blank);

  useEffect(() => { list("/admin/creatives").then(setRows); }, [nonce]);
  useEffect(() => {
    list("/admin/branding-placements").then(setPlacements);
    list("/admin/organisations").then(setOrgs);
    list("/admin/pandals").then(setPandals);
  }, []);

  const reload = () => setNonce((n) => n + 1);
  const set = (k: string) => (e: any) => setDraft({ ...draft, [k]: e.target.value });

  function edit(c: any) {
    setEditing(c);
    setDraft({
      name: c.name, organisation: c.organisation, pandal: c.pandal,
      placement: c.placement, start_date: c.start_date, end_date: c.end_date,
      price: c.price_paise ? String(c.price_paise / 100) : "", target_url: c.target_url || "",
    });
  }

  async function review(id: string, decision: string) {
    await api(`/admin/creatives/${id}/review`, { method: "POST", json: { decision } });
    reload();
  }

  const payload = () => ({
    name: draft.name, organisation: draft.organisation, pandal: draft.pandal,
    placement: draft.placement, start_date: draft.start_date, end_date: draft.end_date,
    target_url: draft.target_url,
    price_paise: draft.price ? Math.round(Number(draft.price) * 100) : 0,
  });

  return (
    <>
      <Panel title={editing ? `Edit “${editing.name}”` : "Add a creative"}
             note="A creative is one sponsor's artwork, in one placement, at one pandal, for a date range. Entitlement is checked when it is saved: a package that grants two placements refuses a third rather than queueing it."
             actions={editing
               ? <button className="abtn abtn-quiet"
                         onClick={() => { setEditing(null); setDraft(blank); }}>Cancel</button>
               : undefined}>
        <div className="panel-body">
          <Form label={editing ? "Save changes" : "Add creative"}
                onDone={() => { setEditing(null); setDraft(blank); reload(); }}
                submit={() => editing
                  ? api(`/admin/creatives/${editing.id}`, { method: "PATCH", json: payload() })
                  : api("/admin/creatives", { method: "POST", json: payload() })}>
            <Field label="Creative name" value={draft.name} required
                   placeholder="Puja Special" onChange={set("name")} />
            <Select label="Sponsor" value={draft.organisation} required
                    onChange={set("organisation")}>
              <option value="">Choose a sponsor…</option>
              {orgs.map((o: any) => <option key={o.id} value={o.id}>{o.name}</option>)}
            </Select>
            <Select label="Pandal" value={draft.pandal} required onChange={set("pandal")}>
              <option value="">Choose a pandal…</option>
              {pandals.map((x: any) => <option key={x.id} value={x.id}>{x.name}</option>)}
            </Select>
            <Select label="Placement" value={draft.placement} required onChange={set("placement")}>
              <option value="">Choose a placement…</option>
              {placements.map((pl: any) => (
                <option key={pl.id} value={pl.id}>
                  {pl.name} · {rupees(pl.price_per_week_paise)}/week
                </option>
              ))}
            </Select>
            <Field label="From" type="date" value={draft.start_date} required
                   onChange={set("start_date")} />
            <Field label="To" type="date" value={draft.end_date} required
                   onChange={set("end_date")} />
            <Field label="Price · rupees" value={draft.price} inputMode="decimal"
                   placeholder="5000" onChange={set("price")} />
            <Field label="Link · optional" value={draft.target_url}
                   placeholder="https://" onChange={set("target_url")} />
          </Form>
          {placements.length === 0 && (
            <p className="hint">
              No placements are defined yet, so there is nothing to book. They are
              platform inventory — add them before a sponsor can buy one.
            </p>
          )}
        </div>
      </Panel>

      <Panel title="Branding review" note="Approving a creative is a platform decision.">
        <Table columns={["Creative", "Sponsor", "Pandal", "Placement", "Runs", "Status", ""]}
               rows={rows.map((c: any) => [
                 c.name, c.organisation_name, c.pandal_name, c.placement_name,
                 <span className="num">{c.start_date} → {c.end_date}</span>,
                 <Pill value={c.status} />,
                 <span className="row">
                   <button className="abtn abtn-quiet" onClick={() => edit(c)}>Edit</button>
                   {c.status === "pending" && (
                     <>
                       <button className="abtn" onClick={() => review(c.id, "approved")}>Approve</button>
                       <button className="abtn abtn-quiet"
                               onClick={() => review(c.id, "rejected")}>Reject</button>
                     </>
                   )}
                 </span>,
               ])}
               empty="No creatives yet." />
      </Panel>
    </>
  );
}

/**
 * A sponsor is two things: the organisation, and somebody who can sign in as
 * it. Creating only the first leaves a company on the platform that nobody can
 * open — so both happen in one submit, the same way a committee is onboarded.
 */
function NewSponsor({ onCreated }: { onCreated: () => void }) {
  const [name, setName] = useState("");
  const [contactName, setContactName] = useState("");
  const [contactPhone, setContactPhone] = useState("");
  const [adminPhone, setAdminPhone] = useState("");

  return (
    <Panel title="Add a sponsor"
           note="Creates the organisation and, if you give a number, the person who can sign in as it. Pandals allocate passes to sponsors, so a sponsor has to exist before anything can be granted to it.">
      <div className="panel-body">
        <Form label="Create sponsor"
              onDone={() => { setName(""); setContactName(""); setContactPhone("");
                              setAdminPhone(""); onCreated(); }}
              submit={async () => {
                const created = await api<any>("/admin/organisations", {
                  method: "POST",
                  json: { name, contact_name: contactName, contact_phone: contactPhone },
                });
                if (adminPhone) {
                  // Their own way in, straight away. Without this the sponsor
                  // exists and nobody can open its panel.
                  await api("/admin/staff", { method: "POST", json: {
                    phone: adminPhone, role: "sponsor_admin", organisation: created.id,
                  }});
                }
                return created;
              }}>
          <Field label="Sponsor name" value={name} required
                 placeholder="e.g. Sponsor One"
                 onChange={(e) => setName(e.target.value)} />
          <div className="row">
            <Field label="Who to contact" value={contactName}
                   onChange={(e) => setContactName(e.target.value)} />
            <Field label="Their number" value={contactPhone}
                   onChange={(e) => setContactPhone(e.target.value)} />
          </div>
          <Field label="Sign-in number for their admin" value={adminPhone}
                 placeholder="+91 98765 43210"
                 onChange={(e) => setAdminPhone(e.target.value)} />
          <p className="hint">
            Optional, but without it nobody can open the sponsor&rsquo;s panel. They sign
            in with this number and a one-time code — there is no password to send.
          </p>
        </Form>
      </div>
    </Panel>
  );
}

function Sponsors() {
  const [pools, setPools] = useState<any[]>([]);
  const [allocations, setAllocations] = useState<any[]>([]);
  const [orgs, setOrgs] = useState<any[]>([]);
  const [pandals, setPandals] = useState<any[]>([]);
  const [nonce, setNonce] = useState(0);

  const [org, setOrg] = useState("");
  const [pandal, setPandal] = useState("");
  const [count, setCount] = useState("");
  const [value, setValue] = useState("");

  useEffect(() => {
    list("/admin/pools").then(setPools);
    list("/admin/allocations").then(setAllocations);
  }, [nonce]);
  useEffect(() => {
    list("/admin/organisations").then(setOrgs);
    list("/admin/pandals").then(setPandals);
  }, [nonce]);

  const reload = () => setNonce((n) => n + 1);

  async function answer(id: string, decision: "accept" | "decline") {
    await api(`/admin/allocations/${id}/${decision}`, { method: "POST" });
    reload();
  }

  const pending = allocations.filter((a: any) => a.status === "pending");

  return (
    <>
      <NewSponsor onCreated={reload} />

      <Panel
        title="Grant passes to a sponsor"
        note="A pool is not edited directly — its counters are the sum of what was granted, sold on and issued, and the database refuses any total that would break that. Granting passes is how a pool comes into being and how it grows.">
        <div className="panel-body">
          <Form label="Grant"
                onDone={() => { setCount(""); setValue(""); reload(); }}
                submit={() => api("/admin/allocations", {
                  method: "POST",
                  json: {
                    organisation: org, pandal,
                    pass_count: Number(count),
                    value_paise: value ? Math.round(Number(value) * 100) : 0,
                  },
                })}>
            <Select label="Sponsor" value={org} onChange={(e) => setOrg(e.target.value)} required>
              <option value="">Choose a sponsor…</option>
              {orgs.map((o: any) => (
                <option key={o.id} value={o.id}>
                  {o.name}{o.is_sub_sponsor ? " · sub-sponsor" : ""}
                </option>
              ))}
            </Select>
            <Select label="Pandal" value={pandal} onChange={(e) => setPandal(e.target.value)} required>
              <option value="">Choose a pandal…</option>
              {pandals.map((p: any) => <option key={p.id} value={p.id}>{p.name}</option>)}
            </Select>
            <Field label="How many passes" value={count} inputMode="numeric" required
                   placeholder="100" onChange={(e) => setCount(e.target.value)} />
            <Field label="Package value · rupees, optional" value={value} inputMode="decimal"
                   placeholder="50000" onChange={(e) => setValue(e.target.value)} />
          </Form>
          <p className="hint">
            The sponsor has to accept before the passes are usable — until then they
            are an offer, not a balance.
          </p>
        </div>
      </Panel>

      <Panel title="Waiting on a sponsor"
             note="Acceptance, not the grant, is what credits a pool. You can answer on a sponsor's behalf.">
        <Table columns={["Sponsor", "Pandal", "Passes", "Offered", ""]}
               rows={pending.map((a: any) => [
                 a.organisation_name, a.pandal_name,
                 <span className="num">{a.pass_count}</span>,
                 new Date(a.created_at).toLocaleDateString(),
                 <span className="row">
                   <button className="abtn" onClick={() => answer(a.id, "accept")}>Accept</button>
                   <button className="abtn abtn-quiet"
                           onClick={() => answer(a.id, "decline")}>Decline</button>
                 </span>,
               ])}
               empty="Nothing waiting." />
      </Panel>

      <Panel title="Sponsor pools"
             note="One row per organisation per pandal — a sponsor at five pandals holds five pools.">
        <Table columns={["Organisation", "Pandal", "Granted", "Sold on", "Issued", "Remaining"]}
               rows={pools.map((p: any) => [
                 p.organisation_name, p.pandal_name,
                 <span className="num">{p.granted}</span>,
                 <span className="num">{p.transferred_out}</span>,
                 <span className="num">{p.issued}</span>,
                 <strong className="num">{p.available}</strong>,
               ])}
               empty="No pools yet." />
      </Panel>
    </>
  );
}

function Issuances() {
  const [rows, setRows] = useState<any[]>([]);
  useEffect(() => { list("/admin/issuances").then(setRows); }, []);

  return (
    <Panel title="Pass issue history"
           note="Every handover out of a sponsor's pool, newest first — who issued it, from which pandal's pool, and to whom.">
      <Table columns={["When", "Sponsor", "Pandal", "Passes", "Given to", "Note"]}
             rows={rows.map((i: any) => [
               new Date(i.created_at).toLocaleString(),
               i.organisation_name, i.pandal_name,
               <strong className="num">{i.quantity}</strong>,
               i.distributed_to || <span className="muted">unnamed</span>,
               i.note || "—",
             ])}
             empty="Nothing has been issued out of a pool yet." />
    </Panel>
  );
}

function Users() {
  const [term, setTerm] = useState("");
  const [adminsOnly, setAdminsOnly] = useState(false);
  const [rows, setRows] = useState<any[]>([]);
  const [nonce, setNonce] = useState(0);
  const [editing, setEditing] = useState<any>(null);

  const blank = { phone: "", first_name: "", last_name: "", email: "" };
  const [draft, setDraft] = useState<any>(blank);
  const set = (k: string) => (e: any) => setDraft({ ...draft, [k]: e.target.value });

  // Typing straight into a query would fire a request per keystroke. A short
  // pause is enough: this is a support tool, not a type-ahead.
  useEffect(() => {
    const timer = setTimeout(() => {
      const query = new URLSearchParams();
      if (term) query.set("q", term);
      if (adminsOnly) query.set("admins_only", "true");
      list(`/admin/users?${query}`).then(setRows);
    }, 250);
    return () => clearTimeout(timer);
  }, [term, adminsOnly, nonce]);

  function edit(u: any) {
    setEditing(u);
    setDraft({ phone: u.phone, first_name: u.first_name ?? "",
               last_name: u.last_name ?? "", email: u.email ?? "" });
  }

  return (
    <>
      <Panel title={editing ? `Edit ${editing.full_name || editing.phone}` : "Add a person"}
             note="Normally an account opens itself when somebody verifies their number. Adding one here is for the people who have not done that yet — a committee's list, handed over before anyone has downloaded anything."
             actions={editing
               ? <button className="abtn abtn-quiet"
                         onClick={() => { setEditing(null); setDraft(blank); }}>Cancel</button>
               : undefined}>
        <div className="panel-body">
          <Form label={editing ? "Save changes" : "Add person"}
                onDone={() => { setEditing(null); setDraft(blank); setNonce((n) => n + 1); }}
                submit={() => editing
                  ? api(`/admin/users/${editing.id}`, { method: "PATCH", json: {
                      first_name: draft.first_name, last_name: draft.last_name,
                      email: draft.email } })
                  : api("/admin/users", { method: "POST", json: draft })}>
            <Field label="Mobile number" value={draft.phone} required
                   placeholder="98765 43210" disabled={!!editing} onChange={set("phone")} />
            <Field label="First name" value={draft.first_name} onChange={set("first_name")} />
            <Field label="Last name" value={draft.last_name} onChange={set("last_name")} />
            <Field label="Email · optional" value={draft.email} type="email"
                   onChange={set("email")} />
          </Form>
          <p className="hint">
            There is no password here. Sign-in is by one-time code, so the number is
            the account — which is also why it cannot be changed once set.
          </p>
        </div>
      </Panel>

      <Panel title="People"
             note="Everyone with an account."
             actions={
               <label className="inline-check">
                 <input type="checkbox" checked={adminsOnly}
                        onChange={(e) => setAdminsOnly(e.target.checked)} />
                 Administrators only
               </label>
             }>
        <div className="panel-body">
          <div className="form">
            <Field label="Search by mobile, name or email" value={term}
                   onChange={(e) => setTerm(e.target.value)} placeholder="98765 or Meera" />
          </div>
        </div>
        <Table columns={["Person", "Mobile", "Email", "Authority", "Verified", "Joined", ""]}
               rows={rows.map((u: any) => [
                 <strong>{u.full_name || "—"}</strong>,
                 <span className="num">{u.phone}</span>,
                 u.email || "—",
                 u.grants.length
                   ? <span className="row">{u.grants.map((g: string) =>
                       <Pill key={g} value="active" label={g} />)}</span>
                   : <span className="muted">Visitor</span>,
                 <Pill value={u.phone_verified_at ? "active" : "wait"} />,
                 new Date(u.date_joined).toLocaleDateString(),
                 <button className="abtn abtn-quiet" onClick={() => edit(u)}>Edit</button>,
               ])}
               empty={term ? "Nobody matches that." : "No accounts yet."} />
      </Panel>
    </>
  );
}
