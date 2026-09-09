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
  const [nonce, setNonce] = useState(0);
  useEffect(() => { list("/admin/creatives").then(setRows); }, [nonce]);

  async function review(id: string, decision: string) {
    await api(`/admin/creatives/${id}/review`, { method: "POST", json: { decision } });
    setNonce((n) => n + 1);
  }

  return (
    <Panel title="Branding review" note="Approving a creative is a platform decision.">
      <Table columns={["Creative", "Sponsor", "Pandal", "Placement", "Status", ""]}
             rows={rows.map((c: any) => [
               c.name, c.organisation_name, c.pandal_name, c.placement_name,
               <Pill value={c.status} />,
               c.status === "pending" ? (
                 <span className="row">
                   <button className="abtn" onClick={() => review(c.id, "approved")}>Approve</button>
                   <button className="abtn abtn-quiet"
                           onClick={() => review(c.id, "rejected")}>Reject</button>
                 </span>
               ) : null,
             ])}
             empty="Nothing awaiting review." />
    </Panel>
  );
}

function Sponsors() {
  const [rows, setRows] = useState<any[]>([]);
  useEffect(() => { list("/admin/pools").then(setRows); }, []);

  return (
    <Panel title="Sponsor pools"
           note="One row per organisation per pandal — a sponsor at five pandals holds five pools.">
      <Table columns={["Organisation", "Pandal", "Granted", "Sold on", "Issued", "Remaining"]}
             rows={rows.map((p: any) => [
               p.organisation_name, p.pandal_name,
               <span className="num">{p.granted}</span>,
               <span className="num">{p.transferred_out}</span>,
               <span className="num">{p.issued}</span>,
               <strong className="num">{p.available}</strong>,
             ])}
             empty="No pools yet." />
    </Panel>
  );
}

function Users() {
  const [term, setTerm] = useState("");
  const [adminsOnly, setAdminsOnly] = useState(false);
  const [rows, setRows] = useState<any[]>([]);

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
  }, [term, adminsOnly]);

  return (
    <Panel title="People"
           note="Everyone with an account. Read-only — an account is opened by verifying a mobile number and closed by the person who owns it."
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
      <Table columns={["Person", "Mobile", "Email", "Authority", "Verified", "Joined"]}
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
             ])}
             empty={term ? "Nobody matches that." : "No accounts yet."} />
    </Panel>
  );
}
