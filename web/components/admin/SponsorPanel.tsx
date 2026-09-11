"use client";

import { useState } from "react";

import { api, list, rupees, type Me } from "@/lib/admin";

import { Field, Form, Panel, Pill, Select, Table, Tile, useLoad } from "./ui";

/**
 * Serves both the Sponsor and Sub-Sponsor panels.
 *
 * They are the same data with a different position in the tree: a sub-sponsor
 * buys from its parent and has no children of its own, so those screens simply
 * do not render — the same capability-driven pattern as the landing page.
 */
export function SponsorPanel({ me, screen }: { me: Me; screen: string }) {
  const { data, error, reload } = useLoad<any>(() => api("/admin/sponsor/overview"), []);
  const isSub = me.organisations.some((o) => o.is_sub_sponsor);

  if (error) return <p className="empty">{error}</p>;
  if (!data) return <p className="empty">Loading…</p>;

  switch (screen) {
    case "passes": return <PassManagement data={data} reload={reload} isSub={isSub} />;
    case "sub-sponsors": return <SubSponsors data={data} reload={reload} />;
    case "branding": return <Branding data={data} />;
    default: return <Overview data={data} reload={reload} isSub={isSub} />;
  }
}

/* --------------------------------------------------------------- Overview */

function Overview({ data, reload, isSub }: any) {
  const t = data.totals;
  return (
    <>
      <div className="tiles">
        <Tile label={isSub ? "Passes bought" : "Passes granted"} value={t.granted} />
        {!isSub && <Tile label="Sold to sub-sponsors" value={t.transferred_out} />}
        <Tile label="Passes issued" value={t.issued} />
        <Tile label="Remaining" value={t.available}
              note={`of ${t.granted} ${isSub ? "bought" : "granted"}`} />
      </div>

      <Pending data={data} reload={reload} />

      <Panel title="Your pools"
             note="A pool belongs to one organisation at one pandal — the totals above are a rollup of these, not a balance.">
        <Table columns={["Pandal", "Granted", "Sold on", "Issued", "Remaining"]}
               rows={data.pools.map((p: any) => [
                 p.pandal_name,
                 <span className="num">{p.granted}</span>,
                 <span className="num">{p.transferred_out}</span>,
                 <span className="num">{p.issued}</span>,
                 <strong className="num">{p.available}</strong>,
               ])}
               empty={isSub
                 ? "No passes yet. Buy some from your sponsor on the Pass management screen."
                 : "No pools yet. A pandal has to allocate you a package first."} />
      </Panel>
    </>
  );
}

function Pending({ data, reload }: any) {
  if (!data.pending_allocations?.length) return null;
  return (
    <Panel title="Waiting for your answer"
           note="Passes are unusable until an allocation is accepted.">
      <Table columns={["Pandal", "Package", "Passes", "Value", ""]}
             rows={data.pending_allocations.map((a: any) => [
               a.pandal_name, a.package_name || "—",
               <span className="num">{a.pass_count}</span>,
               <span className="num">{rupees(a.value_paise)}</span>,
               <span className="row">
                 <button className="abtn" onClick={async () => {
                   await api(`/admin/allocations/${a.id}/accept`, { method: "POST" });
                   reload();
                 }}>Accept</button>
                 <button className="abtn abtn-quiet" onClick={async () => {
                   await api(`/admin/allocations/${a.id}/decline`, { method: "POST" });
                   reload();
                 }}>Decline</button>
               </span>,
             ])}
             empty="" />
    </Panel>
  );
}

/* -------------------------------------------------------- Pass management */

function PassManagement({ data, reload, isSub }: any) {
  const [poolId, setPoolId] = useState(data.pools[0]?.id ?? "");
  const [quantity, setQuantity] = useState("");
  const [to, setTo] = useState("");
  const [buyPandal, setBuyPandal] = useState("");
  const [buyQty, setBuyQty] = useState("");

  const pool = data.pools.find((p: any) => p.id === poolId);
  const pandals: { id: string; name: string }[] = data.pools.map(
    (p: any) => ({ id: p.pandal, name: p.pandal_name }),
  );
  const org = data.organisations[0];

  return (
    <>
      <div className="tiles">
        <Tile label="Passes issued" value={data.totals.issued} />
        <Tile label="Passes remaining" value={data.totals.available}
              note={`of ${data.totals.issued + data.totals.available} in your pool`} />
      </div>

      {!isSub && data.packages?.length > 0 && (
        <Panel title="My sponsorship packages"
               note="One per pandal that has taken you on as a sponsor.">
          <Table columns={["Pandal", "Package", "Value", "Passes", "Placements", "Benefits"]}
                 rows={data.packages.map((p: any) => [
                   <strong>{p.pandal_name}</strong>,
                   p.name,
                   <span className="num">{rupees(p.value_paise)}</span>,
                   <span className="num">{p.pass_count}</span>,
                   <span className="num">{p.banner_placements}</span>,
                   p.benefits || "—",
                 ])}
                 empty="" />
        </Panel>
      )}

      <Pending data={data} reload={reload} />

      {isSub && (
        <Panel title="Buy passes from your sponsor"
               note={`You can only buy from ${org?.name ? "your sponsor" : "your sponsor"}, not directly from a pandal — at the price they set.`}>
          <div className="panel-body">
            <Form label={`Buy${org?.price_per_pass_paise
              ? ` at ${rupees(org.price_per_pass_paise)} each` : ""}`}
                  onDone={() => { setBuyQty(""); reload(); }}
                  submit={() => api("/admin/sponsor/buy", { method: "POST", json: {
                    pandal: buyPandal, quantity: Number(buyQty),
                  }})}>
              <Select label="Pandal" value={buyPandal} required
                      onChange={(e) => setBuyPandal(e.target.value)}>
                <option value="">Choose a pandal…</option>
                {pandals.map((p) => <option key={p.id} value={p.id}>{p.name}</option>)}
              </Select>
              <Field label="How many" value={buyQty} inputMode="numeric" required
                     onChange={(e) => setBuyQty(e.target.value)} placeholder="25" />
            </Form>
          </div>
        </Panel>
      )}

      <Panel title="Issue passes"
             note="Hand passes to a named recipient. The pool is drawn down and the handover recorded.">
        <div className="panel-body">
          <Form label="Issue" onDone={() => { setQuantity(""); setTo(""); reload(); }}
                submit={() => api(`/admin/pools/${poolId}/issue`, { method: "POST", json: {
                  quantity: Number(quantity), distributed_to: to,
                }})}>
            <Select label="From pool" value={poolId} onChange={(e) => setPoolId(e.target.value)}>
              {data.pools.map((p: any) => (
                <option key={p.id} value={p.id}>{p.pandal_name} · {p.available} left</option>
              ))}
            </Select>
            <Field label="How many" value={quantity} inputMode="numeric" required
                   onChange={(e) => setQuantity(e.target.value)}
                   placeholder={pool ? `up to ${pool.available}` : ""} />
            <Field label="Distributed to" value={to} onChange={(e) => setTo(e.target.value)}
                   placeholder="e.g. Bengal Sweets Co. Staff" />
          </Form>
        </div>
      </Panel>

      <Panel title="Allocation history"
             note="Every allocation between you and a pandal, newest first.">
        <Table columns={["Pandal", "Package", "Passes", "Status", "Answered"]}
               rows={(data.allocations ?? []).map((a: any) => [
                 a.pandal_name, a.package_name || "—",
                 <span className="num">{a.pass_count}</span>,
                 <Pill value={a.status} />,
                 a.responded_at ? new Date(a.responded_at).toLocaleDateString("en-IN") : "—",
               ])}
               empty="Nothing allocated yet." />
      </Panel>

      <Panel title="Where your passes went">
        <Table columns={["Pandal", "Quantity", "Distributed to", "When"]}
               rows={(data.issuances ?? []).map((i: any) => [
                 i.pandal_name, <span className="num">{i.quantity}</span>,
                 i.distributed_to || <em>unnamed</em>,
                 new Date(i.created_at).toLocaleDateString("en-IN"),
               ])}
               empty="Nothing issued yet." />
      </Panel>
    </>
  );
}

/* ----------------------------------------------------------- Sub-sponsors */

function SubSponsors({ data, reload }: any) {
  const { data: organisations, reload: reloadOrgs } =
    useLoad<any[]>(() => list("/admin/organisations"), [data]);

  const [name, setName] = useState("");
  const [price, setPrice] = useState("");
  const [contact, setContact] = useState("");
  const [adminPhone, setAdminPhone] = useState("");
  const [poolId, setPoolId] = useState(data.pools[0]?.id ?? "");
  const [grant, setGrant] = useState("");
  const [editing, setEditing] = useState<string | null>(null);
  const [newPrice, setNewPrice] = useState("");
  const [grantMore, setGrantMore] = useState("");
  const [grantPool, setGrantPool] = useState(data.pools[0]?.id ?? "");

  const parent = data.organisations[0];
  const children = (organisations ?? []).filter((o) => o.is_sub_sponsor);

  return (
    <>
      <Panel title="Create a sub-sponsor"
             note="They sign in with their own mobile number and one-time code — there is no password for anyone to see or share.">
        <div className="panel-body">
          <Form label="Create"
                onDone={() => { setName(""); setPrice(""); setGrant(""); setAdminPhone("");
                                reloadOrgs(); reload(); }}
                submit={async () => {
                  const child = await api<any>("/admin/organisations", { method: "POST", json: {
                    name, parent: parent.id, contact_phone: contact,
                    price_per_pass_paise: price ? Math.round(Number(price) * 100) : 0,
                  }});
                  if (adminPhone) {
                    // Their own way in. Until now this form created the
                    // organisation and nothing else, so the panel's promise
                    // that they sign in with their number was not yet true.
                    await api("/admin/staff", { method: "POST", json: {
                      phone: adminPhone, role: "sub_sponsor_admin", organisation: child.id,
                    }});
                  }
                  if (grant && poolId) {
                    await api(`/admin/pools/${poolId}/transfer`, { method: "POST", json: {
                      to_organisation: child.id, quantity: Number(grant),
                      price_per_pass_paise: price ? Math.round(Number(price) * 100) : 0,
                    }});
                  }
                }}>
            <Field label="Name" value={name} required placeholder="Kolkata Sweets Corner"
                   onChange={(e) => setName(e.target.value)} />
            <Field label="Contact mobile" value={contact}
                   onChange={(e) => setContact(e.target.value)} placeholder="98765 43210" />
            <Field label="Sign-in number for their admin" value={adminPhone}
                   onChange={(e) => setAdminPhone(e.target.value)}
                   placeholder="+91 98765 43210" />
            <p className="hint">
              Optional, but without it nobody can open their panel. They do not need an
              account first — their number is the invitation.
            </p>
            <Field label="Price per pass · what you charge them" value={price} inputMode="decimal"
                   onChange={(e) => setPrice(e.target.value)} placeholder="100" />
            <Select label="Starter grant from" value={poolId}
                    onChange={(e) => setPoolId(e.target.value)}>
              {data.pools.map((p: any) => (
                <option key={p.id} value={p.id}>{p.pandal_name} · {p.available} left</option>
              ))}
            </Select>
            <Field label="Starter grant · optional" value={grant} inputMode="numeric"
                   onChange={(e) => setGrant(e.target.value)} placeholder="100" />
          </Form>
        </div>
      </Panel>

      <Panel title="Your sub-sponsors"
             note="Each buys only from you, never from a pandal. The price you set is what they pay when they buy.">
        <Table columns={["Sub-sponsor", "Contact", "Price/pass", "Passes held",
                         "Paid to you", "Status", ""]}
               rows={children.map((c) => [
                 <strong>{c.name}</strong>, c.contact_phone || "—",
                 <span className="num">{rupees(c.price_per_pass_paise)}</span>,
                 <span className="num">{c.passes_held}</span>,
                 <span className="num">{rupees(c.paid_to_parent_paise)}</span>,
                 <Pill value={c.is_active ? "active" : "off"} />,
                 <button className="abtn abtn-quiet"
                         onClick={() => { setEditing(editing === c.id ? null : c.id);
                                          setNewPrice(String((c.price_per_pass_paise ?? 0) / 100)); }}>
                   {editing === c.id ? "Close" : "Manage"}
                 </button>,
               ])}
               empty="None yet." />
      </Panel>

      {editing && (() => {
        const child = children.find((c) => c.id === editing);
        if (!child) return null;
        return (
          <Panel title={`Manage ${child.name}`}
                 note="Repricing applies to their next purchase; passes already bought keep the price they were sold at.">
            <div className="panel-body side-by-side">
              <Form label="Save price"
                    onDone={() => { reloadOrgs(); reload(); }}
                    submit={() => api(`/admin/organisations/${child.id}`, {
                      method: "PATCH",
                      json: { price_per_pass_paise: Math.round(Number(newPrice) * 100) },
                    })}>
                <Field label="Price per pass" inputMode="decimal" required
                       value={newPrice} onChange={(e) => setNewPrice(e.target.value)}
                       placeholder={String((child.price_per_pass_paise ?? 0) / 100)} />
              </Form>

              <Form label="Grant passes"
                    onDone={() => { setGrantMore(""); reloadOrgs(); reload(); }}
                    submit={() => api(`/admin/pools/${grantPool}/transfer`, {
                      method: "POST",
                      json: { to_organisation: child.id, quantity: Number(grantMore),
                              price_per_pass_paise: child.price_per_pass_paise ?? 0 },
                    })}>
                <Select label="From pool" value={grantPool}
                        onChange={(e) => setGrantPool(e.target.value)}>
                  {data.pools.map((p: any) => (
                    <option key={p.id} value={p.id}>{p.pandal_name} · {p.available} left</option>
                  ))}
                </Select>
                <Field label="How many" inputMode="numeric" required value={grantMore}
                       onChange={(e) => setGrantMore(e.target.value)} placeholder="50" />
              </Form>
            </div>
          </Panel>
        );
      })()}
    </>
  );
}

/* --------------------------------------------------------------- Branding */

function Branding({ data }: any) {
  const { data: creatives, reload } = useLoad<any[]>(() => list("/admin/creatives"), []);

  const [name, setName] = useState("");
  const [pandal, setPandal] = useState(data.pools[0]?.pandal ?? "");
  const [placement, setPlacement] = useState("");
  const [start, setStart] = useState("2026-10-10");
  const [end, setEnd] = useState("2026-10-14");

  const entitled = data.packages?.reduce((n: number, p: any) => n + p.banner_placements, 0) ?? 0;
  const inUse = (creatives ?? []).filter((c) => ["pending", "approved"].includes(c.status)).length;
  const known = Array.from(new Map((creatives ?? []).map(
    (c) => [c.placement, c.placement_name])).entries());

  return (
    <>
      <Panel title="Branding entitlement"
             note={`Your packages allow ${entitled} placement(s). ${inUse} in use — pending and approved both count, so an upload beyond the entitlement is refused rather than queued.`}>
        <div className="panel-body">
          <Form label="Add creative" onDone={() => { setName(""); reload(); }}
                submit={() => api("/admin/creatives", { method: "POST", json: {
                  organisation: data.organisations[0].id, pandal, placement,
                  name, start_date: start, end_date: end,
                }})}>
            <Field label="Creative name" value={name} required placeholder="Puja Special"
                   onChange={(e) => setName(e.target.value)} />
            <Select label="Pandal" value={pandal} onChange={(e) => setPandal(e.target.value)}>
              {data.pools.map((p: any) => (
                <option key={p.pandal} value={p.pandal}>{p.pandal_name}</option>
              ))}
            </Select>
            <Select label="Placement" value={placement} required
                    onChange={(e) => setPlacement(e.target.value)}>
              <option value="">Choose a placement…</option>
              {known.map(([id, label]) => <option key={id} value={id}>{label}</option>)}
            </Select>
            <div className="row">
              <Field label="From" type="date" value={start}
                     onChange={(e) => setStart(e.target.value)} />
              <Field label="To" type="date" value={end} onChange={(e) => setEnd(e.target.value)} />
            </div>
          </Form>
        </div>
      </Panel>

      <Panel title="Your creatives">
        <Table columns={["Creative", "Pandal", "Placement", "Dates", "Price", "Status"]}
               rows={(creatives ?? []).map((c) => [
                 <strong>{c.name}</strong>, c.pandal_name, c.placement_name,
                 `${c.start_date} → ${c.end_date}`,
                 <span className="num">{rupees(c.price_paise)}</span>,
                 <Pill value={c.status} />,
               ])}
               empty="No creatives uploaded." />
      </Panel>
    </>
  );
}
