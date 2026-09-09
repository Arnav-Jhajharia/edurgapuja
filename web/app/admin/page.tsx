"use client";

import { useCallback, useEffect, useState } from "react";

import { Login } from "@/components/admin/Login";
import { PandalPanel } from "@/components/admin/PandalPanel";
import { SponsorPanel } from "@/components/admin/SponsorPanel";
import { SuperPanel } from "@/components/admin/SuperPanel";
import { api, getToken, PANEL_FOR, setToken, type Me } from "@/lib/admin";

import "./admin.css";

type Group = { group: string; items: [string, string][] };

/** Which screens each panel offers. The role decides; the server enforces. */
const SCREENS: Record<string, Group[]> = {
  pandal_admin: [
    { group: "Money", items: [["revenue", "Donations"], ["links", "Donation links"],
                              ["offerings", "Donation presets"]] },
    { group: "Visitors", items: [["services", "Services"], ["bookings", "Service bookings"],
                                 ["live", "Live status"], ["support", "Support & feedback"]] },
    { group: "Passes", items: [["passSetup", "What you sell"], ["passSales", "Passes & payments"],
                               ["entryLog", "Entry & QR log"]] },
    { group: "Sponsorship", items: [["packages", "Sponsorship packages"],
                                    ["sponsors", "Sponsors"]] },
    { group: "People", items: [["volunteers", "Volunteers & gates"],
                               ["staff", "Who can sign in"]] },
    { group: "My website", items: [["details", "Committee & details"],
                                   ["appearance", "Colours"],
                                   ["page", "Page text"],
                                   ["visitFacts", "Plan your visit"]] },
  ],
  sponsor_admin: [
    { group: "Sponsorship", items: [["overview", "Overview"], ["passes", "Pass management"],
                                    ["sub-sponsors", "Sub-sponsors"], ["branding", "Branding"]] },
  ],
  sub_sponsor_admin: [
    { group: "Sponsorship", items: [["overview", "Overview"], ["passes", "Pass management"],
                                    ["branding", "Branding"]] },
  ],
  super_admin: [
    { group: "Platform", items: [["dashboard", "Dashboard"], ["pandals", "Pandals"],
                                 ["sponsors-pools", "Sponsor pools"],
                                 ["creatives", "Branding review"],
                                 ["users", "People"]] },
    { group: "Pandal operations", items: [["revenue", "Donations"], ["services", "Services"],
                                          ["passSales", "Passes & payments"],
                                          ["entryLog", "Entry & QR log"],
                                          ["live", "Live status"],
                                          ["support", "Support & feedback"]] },
    // A platform operator onboarding a committee needs to be able to set their
    // page up with them. The API already allowed this — only the nav did not
    // offer it, which is the kind of gap that ends in someone asking for the
    // committee's login.
    { group: "Their website", items: [["details", "Committee & details"],
                                      ["appearance", "Colours"],
                                      ["page", "Page text"],
                                      ["visitFacts", "Plan your visit"],
                                      ["passSetup", "What they sell"],
                                      ["staff", "Who can sign in"]] },
  ],
};

const PANDAL_SCREENS = new Set(["revenue", "links", "offerings", "services", "bookings",
                                "volunteers", "packages", "sponsors", "live", "support", "page",
                                "passSetup", "passSales", "entryLog",
                                "appearance", "details", "visitFacts", "staff"]);
const SUPER_SCREENS = new Set(["dashboard", "pandals", "sponsors-pools", "creatives",
                               "users"]);

export default function AdminPage() {
  const [me, setMe] = useState<Me | null>(null);
  const [checked, setChecked] = useState(false);
  const [role, setRole] = useState("");
  const [screen, setScreen] = useState("");
  const [pandalId, setPandalId] = useState("");

  const load = useCallback(() => {
    if (!getToken()) { setChecked(true); return; }
    api<Me>("/admin/me")
      .then((body) => {
        setMe(body);
        const first = body.roles[0] ?? "";
        setRole(first);
        setScreen(SCREENS[first]?.[0]?.items[0]?.[0] ?? "");
        setPandalId(body.pandals[0]?.id ?? "");
      })
      .catch(() => setToken(null, null))
      .finally(() => setChecked(true));
  }, []);

  useEffect(load, [load]);

  if (!checked) return <div className="login"><p>Loading…</p></div>;
  if (!me) return <Login onSignedIn={() => { setChecked(false); load(); }} />;

  const groups = SCREENS[role] ?? [];
  const title = groups.flatMap((g) => g.items).find(([k]) => k === screen)?.[1] ?? "Admin";
  const onPandalScreen = PANDAL_SCREENS.has(screen);
  const scoped = onPandalScreen && me.pandals.length > 0;

  return (
    <div className="admin">
      <aside className="admin-side">
        <div className="admin-brand">
          <strong>eDurgaPuja</strong>
          <span>{PANEL_FOR[role] ?? "Admin"}</span>
        </div>

        <nav className="admin-nav">
          {/* Only roles this account actually holds. The tab does not grant the
              role — authority comes from the account and is checked server-side. */}
          {me.roles.length > 1 && (
            <>
              <p>Panels</p>
              {me.roles.map((r) => (
                <button key={r} aria-current={r === role} onClick={() => {
                  setRole(r);
                  setScreen(SCREENS[r]?.[0]?.items[0]?.[0] ?? "");
                }}>{PANEL_FOR[r] ?? r}</button>
              ))}
            </>
          )}

          {groups.map((group) => (
            <div key={group.group}>
              <p>{group.group}</p>
              {group.items.map(([key, label]) => (
                <button key={key} aria-current={key === screen}
                        onClick={() => setScreen(key)}>{label}</button>
              ))}
            </div>
          ))}
        </nav>

        <div className="admin-foot">
          <div>{me.full_name || me.phone}</div>
          <button onClick={() => { setToken(null, null); setMe(null); }}>Sign out</button>
        </div>
      </aside>

      <main className="admin-main">
        <div className="admin-head">
          <div>
            <h1>{title}</h1>
            <p>
              {PANEL_FOR[role]}
              {scoped ? ` · ${me.pandals.find((p) => p.id === pandalId)?.name ?? ""}` : ""}
            </p>
          </div>

          {me.pandals.length > 1 && onPandalScreen && (
            <select value={pandalId} onChange={(e) => setPandalId(e.target.value)}>
              {me.pandals.map((p) => <option key={p.id} value={p.id}>{p.name}</option>)}
            </select>
          )}
        </div>

        {(role === "pandal_admin" || role === "super_admin") && PANDAL_SCREENS.has(screen) &&
          <PandalPanel me={me} screen={screen} pandalId={pandalId} />}

        {role === "super_admin" && SUPER_SCREENS.has(screen) &&
          <SuperPanel screen={screen === "sponsors-pools" ? "sponsors" : screen} />}

        {(role === "sponsor_admin" || role === "sub_sponsor_admin") &&
          <SponsorPanel me={me} screen={screen} />}
      </main>
    </div>
  );
}
