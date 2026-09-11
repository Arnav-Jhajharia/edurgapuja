"use client";

import { useCallback, useEffect, useState } from "react";

import { Avatar, Icon, ScreenIcon } from "@/components/admin/Icons";
import { Login } from "@/components/admin/Login";
import { Lotus } from "@/components/admin/Lotus";
import { PandalPanel } from "@/components/admin/PandalPanel";
import { SponsorPanel } from "@/components/admin/SponsorPanel";
import { SuperPanel } from "@/components/admin/SuperPanel";
import { api, getToken, PANEL_FOR, setToken, type Me } from "@/lib/admin";

import "./admin.css";

/**
 * A rail entry. `tabs`, when present, are sibling screens that share the
 * entry — the rail names the subject and a strip above the panel names the
 * view of it. Screen keys are untouched by the grouping, so what the rail
 * shows and what the panels answer to stay independent.
 */
type Item = { key: string; label: string; tabs?: [string, string][] };
/** `group: null` means a flat list with no heading — right when there are few
    enough entries that a heading would be labelling the obvious. */
type Group = { group: string | null; items: Item[] };

/**
 * What a pandal admin runs. A Super Admin gets all of it, so this is defined
 * once and reused rather than copied — the copy had already drifted, missing
 * six screens a platform operator could reach through the API but not the nav.
 *
 * Sixteen entries became ten. The six that went were not removed: donation
 * links and presets are views of Donations, what-you-sell and the entry log are
 * views of Passes, bookings are a view of Services, and the four website
 * screens are four tabs of one page. Each was a separate rail entry only
 * because it is a separate component, which is the console's problem and not
 * the committee's.
 */
const PANDAL_ITEMS: Item[] = [
  { key: "revenue", label: "Donations", tabs: [
      ["revenue", "Donations"], ["links", "Donation links"], ["offerings", "Presets"]] },
  { key: "passSales", label: "Passes & payments", tabs: [
      ["passSales", "Sales"], ["passSetup", "What you sell"], ["entryLog", "Entry & QR log"]] },
  { key: "services", label: "Services", tabs: [
      ["services", "Services"], ["bookings", "Bookings"]] },
  { key: "packages", label: "Sponsorship packages" },
  { key: "sponsors", label: "Sponsors" },
  { key: "volunteers", label: "Volunteers & gates" },
  { key: "live", label: "Live status" },
  { key: "support", label: "Support & feedback" },
  { key: "details", label: "My website", tabs: [
      ["details", "Committee & details"], ["appearance", "Colours"],
      ["page", "Page text"], ["visitFacts", "Plan your visit"]] },
  { key: "staff", label: "Who can sign in" },
];

/** The same screens, worded for somebody operating on a committee's behalf. */
const REWORDED: Record<string, string> = {
  "My website": "Their website", "What you sell": "What they sell",
};
const forSuperAdmin = (items: Item[]): Item[] =>
  items.map((item) => ({
    ...item,
    label: REWORDED[item.label] ?? item.label,
    tabs: item.tabs?.map(([key, label]) =>
      [key, REWORDED[label] ?? label] as [string, string]),
  }));

const SCREENS: Record<string, Group[]> = {
  pandal_admin: [{ group: null, items: PANDAL_ITEMS }],
  sponsor_admin: [{ group: null, items: [
    { key: "overview", label: "Overview" },
    { key: "passes", label: "Pass management" },
    { key: "sub-sponsors", label: "Sub-sponsors" },
    { key: "branding", label: "Branding" },
  ] }],
  sub_sponsor_admin: [{ group: null, items: [
    { key: "overview", label: "Overview" },
    { key: "passes", label: "Pass management" },
    { key: "branding", label: "Branding" },
  ] }],
  // A Super Admin outranks a pandal admin, so they can do everything a pandal
  // admin can — plus the platform's own screens. Every queryset behind these
  // already returns everything for a super admin; only the nav withheld them.
  //
  // Three headings, because a super admin is really wearing three hats: the
  // platform's, a committee's, and a sponsor's. Seven headings described the
  // codebase's folders, not the job.
  super_admin: [
    { group: "Platform", items: [
      { key: "dashboard", label: "Dashboard" },
      { key: "pandals", label: "Pandals" },
      { key: "users", label: "People" },
      { key: "issuances", label: "Pass issue history" },
    ] },
    { group: "Pandal operations", items: forSuperAdmin(PANDAL_ITEMS) },
    { group: "Sponsor operations", items: [
      { key: "sponsors-pools", label: "Sponsor pools" },
      { key: "creatives", label: "Branding review" },
    ] },
  ],
};

/** Every screen PandalPanel renders, taken from the nav so the two cannot
    disagree — a key present in one and absent from the other silently falls
    back to the Donations screen. Tabs count: they are screens too. */
const keysOf = (items: Item[]) =>
  items.flatMap((item) => item.tabs?.map(([key]) => key) ?? [item.key]);

const PANDAL_SCREENS = new Set(keysOf(PANDAL_ITEMS));
const SUPER_SCREENS = new Set(["dashboard", "pandals", "sponsors-pools", "creatives",
                               "issuances", "users"]);

const ROLE_ICON: Record<string, string> = {
  super_admin: "dashboard", pandal_admin: "pandals",
  sponsor_admin: "sponsors", sub_sponsor_admin: "subsponsors",
};

/** The entry a screen belongs to — itself, or the parent whose tabs hold it. */
const owner = (groups: Group[], screen: string): Item | undefined =>
  groups.flatMap((g) => g.items)
        .find((item) => item.key === screen
                     || item.tabs?.some(([key]) => key === screen));

const firstScreen = (role: string) => SCREENS[role]?.[0]?.items[0]?.key ?? "";

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
        setScreen(firstScreen(first));
        setPandalId(body.pandals[0]?.id ?? "");
      })
      .catch(() => setToken(null, null))
      .finally(() => setChecked(true));
  }, []);

  useEffect(load, [load]);

  if (!checked) return <div className="login"><p>Loading…</p></div>;
  if (!me) return <Login onSignedIn={() => { setChecked(false); load(); }} />;

  const groups = SCREENS[role] ?? [];
  const current = owner(groups, screen);
  const title = current?.label ?? "Admin";
  const onPandalScreen = PANDAL_SCREENS.has(screen);
  const scoped = onPandalScreen && me.pandals.length > 0;
  const who = me.full_name || me.phone;

  return (
    <div className="admin">
      <aside className="admin-side">
        <div className="admin-brand">
          <span className="admin-mark"><Lotus /></span>
          <div>
            <strong>eDurgaPuja</strong>
            <span>{PANEL_FOR[role] ?? "Admin"}</span>
          </div>
        </div>

        <nav className="admin-nav">
          {/* Only roles this account actually holds. The tab does not grant the
              role — authority comes from the account and is checked server-side. */}
          {me.roles.length > 1 && (
            <>
              <p>Panels</p>
              <div>
                {me.roles.map((r) => (
                  <button key={r} aria-current={r === role} onClick={() => {
                    setRole(r);
                    setScreen(firstScreen(r));
                  }}>
                    <Icon name={ROLE_ICON[r] ?? "dashboard"} />
                    {PANEL_FOR[r] ?? r}
                  </button>
                ))}
              </div>
            </>
          )}

          {groups.map((group, i) => (
            <div key={group.group ?? i}>
              {group.group && <p>{group.group}</p>}
              {group.items.map((item) => (
                <button key={item.key} aria-current={item.key === current?.key}
                        onClick={() => setScreen(item.key)}>
                  <ScreenIcon screen={item.key} />
                  {item.label}
                </button>
              ))}
            </div>
          ))}
        </nav>

        <div className="admin-foot">
          <Avatar name={who} />
          <div>
            <strong>{who}</strong>
            <span>{PANEL_FOR[role] ?? "Admin"}</span>
          </div>
          <button title="Sign out" aria-label="Sign out"
                  onClick={() => { setToken(null, null); setMe(null); }}>
            <Icon name="signout" />
          </button>
        </div>
      </aside>

      <main className="admin-main">
        <div className="admin-head">
          <h1>{title}</h1>
          <div className="head-right">
            {me.pandals.length > 1 && onPandalScreen && (
              <select value={pandalId} onChange={(e) => setPandalId(e.target.value)}>
                {me.pandals.map((p) => <option key={p.id} value={p.id}>{p.name}</option>)}
              </select>
            )}
            <Avatar name={who} />
          </div>
        </div>

        <div className="admin-body">
          <p className="admin-context">
            {PANEL_FOR[role]}
            {scoped ? ` · ${me.pandals.find((p) => p.id === pandalId)?.name ?? ""}` : ""}
          </p>

          {current?.tabs && (
            <div className="subnav">
              {current.tabs.map(([key, label]) => (
                <button key={key} aria-current={key === screen}
                        onClick={() => setScreen(key)}>{label}</button>
              ))}
            </div>
          )}

          {(role === "pandal_admin" || role === "super_admin") && PANDAL_SCREENS.has(screen) &&
            <PandalPanel me={me} screen={screen} pandalId={pandalId} />}

          {role === "super_admin" && SUPER_SCREENS.has(screen) &&
            <SuperPanel screen={screen === "sponsors-pools" ? "sponsors" : screen} />}

          {(role === "sponsor_admin" || role === "sub_sponsor_admin") &&
            <SponsorPanel me={me} screen={screen} />}
        </div>
      </main>
    </div>
  );
}
