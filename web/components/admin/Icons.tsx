/**
 * The console's nav icons.
 *
 * A rail of twenty-odd plain labels reads as one undifferentiated list — you
 * scan it word by word every time. An icon gives each row a shape you learn
 * once and then recognise without reading, which is the whole reason to spend
 * the pixels.
 *
 * One line weight, one grid, no fills: they sit beside 14px text and must not
 * out-shout it. Anything that needs more than a couple of strokes to be
 * recognisable is the wrong metaphor, not a reason for more detail.
 */

const box = {
  viewBox: "0 0 24 24",
  fill: "none",
  stroke: "currentColor",
  strokeWidth: 1.6,
  strokeLinecap: "round" as const,
  strokeLinejoin: "round" as const,
  "aria-hidden": true,
};

const PATHS: Record<string, React.ReactNode> = {
  // Platform
  dashboard: <><rect x="3" y="3" width="7" height="7" rx="1.6" /><rect x="14" y="3" width="7" height="7" rx="1.6" /><rect x="3" y="14" width="7" height="7" rx="1.6" /><rect x="14" y="14" width="7" height="7" rx="1.6" /></>,
  pandals: <><path d="M12 21s7-5.3 7-10.4A7 7 0 0 0 5 10.6C5 15.7 12 21 12 21Z" /><circle cx="12" cy="10.5" r="2.4" /></>,
  users: <><circle cx="9" cy="8" r="3.2" /><path d="M3 20c0-3.1 2.7-5.2 6-5.2s6 2.1 6 5.2" /><path d="M16.5 5.4a3.2 3.2 0 0 1 0 5.9M18 14.4c2 .7 3.4 2.3 3.4 4.4" /></>,
  issuances: <><path d="M8 5h12M8 12h12M8 19h12" /><circle cx="4" cy="5" r="1" /><circle cx="4" cy="12" r="1" /><circle cx="4" cy="19" r="1" /></>,

  // Money
  donations: <><path d="M5 20V11M12 20V4M19 20v-6" /></>,
  links: <><path d="M10.2 13.8a4 4 0 0 0 5.7 0l2.4-2.4a4 4 0 0 0-5.7-5.7l-1.2 1.2" /><path d="M13.8 10.2a4 4 0 0 0-5.7 0l-2.4 2.4a4 4 0 0 0 5.7 5.7l1.2-1.2" /></>,
  passes: <><path d="M3 9.5V7.4c0-.8.6-1.4 1.4-1.4h15.2c.8 0 1.4.6 1.4 1.4v2.1a2.5 2.5 0 0 0 0 5v2.1c0 .8-.6 1.4-1.4 1.4H4.4c-.8 0-1.4-.6-1.4-1.4v-2.1a2.5 2.5 0 0 0 0-5Z" /></>,
  entryLog: <><rect x="3" y="3" width="7" height="7" rx="1.4" /><rect x="14" y="3" width="7" height="7" rx="1.4" /><rect x="3" y="14" width="7" height="7" rx="1.4" /><path d="M14 14h3v3h-3zM20 20h1M17.5 20.5h.5M20 14h1v3" /></>,

  // Running the pandal
  services: <><path d="m12 3.6 2.5 5 5.6.8-4 4 .9 5.6-5-2.6-5 2.6.9-5.6-4-4 5.6-.8Z" /></>,
  live: <><circle cx="12" cy="12" r="8.4" /><path d="M12 7.4V12l3 1.8" /></>,
  volunteers: <><circle cx="9.5" cy="8" r="3.2" /><path d="M3.5 20c0-3.1 2.7-5.2 6-5.2s6 2.1 6 5.2" /><path d="M18.5 8v5M16 10.5h5" /></>,
  staff: <><circle cx="8" cy="12" r="3.4" /><path d="M11.4 12H21M18 12v3M15 12v2.2" /></>,
  support: <><circle cx="12" cy="12" r="8.4" /><path d="M9.7 9.6a2.4 2.4 0 1 1 3.2 2.3c-.6.2-.9.7-.9 1.3v.4" /><path d="M12 16.6h.01" /></>,

  // Sponsorship
  packages: <><path d="M3.6 8.6h16.8v10.2c0 .9-.7 1.6-1.6 1.6H5.2c-.9 0-1.6-.7-1.6-1.6Z" /><path d="M3.6 8.6 5 4.8c.2-.5.6-.8 1.1-.8h11.8c.5 0 1 .3 1.1.8l1.4 3.8M12 8.6v12" /></>,
  sponsors: <><rect x="3" y="7.4" width="18" height="12.2" rx="1.8" /><path d="M8.6 7.4V5.6c0-.9.7-1.6 1.6-1.6h3.6c.9 0 1.6.7 1.6 1.6v1.8M3 12.4h18" /></>,
  pools: <><path d="m12 3.2 8.4 4.2-8.4 4.2L3.6 7.4Z" /><path d="m3.6 12 8.4 4.2 8.4-4.2M3.6 16.6l8.4 4.2 8.4-4.2" /></>,
  branding: <><rect x="3" y="4.6" width="18" height="14.8" rx="2" /><circle cx="8.6" cy="10" r="1.6" /><path d="m3.6 16.4 4.6-4 4 3.4 3.4-2.8 4.4 3.8" /></>,
  subsponsors: <><circle cx="12" cy="5.2" r="2.2" /><circle cx="5.4" cy="18.8" r="2.2" /><circle cx="18.6" cy="18.8" r="2.2" /><path d="M12 7.4v4.2M5.4 16.6v-2.4a1.6 1.6 0 0 1 1.6-1.6h10a1.6 1.6 0 0 1 1.6 1.6v2.4" /></>,
  overview: <><circle cx="12" cy="12" r="8.4" /><path d="M12 3.6V12l6 4.2" /></>,

  // The committee's own page
  website: <><rect x="3" y="4.4" width="18" height="15.2" rx="2" /><path d="M3 9.2h18M7 6.8h.01M9.6 6.8h.01" /></>,

  // Chrome
  signout: <><path d="M14.6 16.6v1.8c0 1-.8 1.8-1.8 1.8H5.4c-1 0-1.8-.8-1.8-1.8V5.6c0-1 .8-1.8 1.8-1.8h7.4c1 0 1.8.8 1.8 1.8v1.8" /><path d="M18.4 15 21.6 12 18.4 9M21.6 12H9.4" /></>,
  search: <><circle cx="10.8" cy="10.8" r="6.4" /><path d="m15.6 15.6 4.6 4.6" /></>,
};

/**
 * Screen key → glyph. Keys the rail asks for and this map does not have fall
 * back to the neutral square, so a new screen appears with a plain icon rather
 * than a gap in the alignment.
 */
const FOR_SCREEN: Record<string, string> = {
  dashboard: "dashboard", pandals: "pandals", users: "users", issuances: "issuances",
  revenue: "donations", links: "links", offerings: "donations",
  passSales: "passes", passSetup: "passes", entryLog: "entryLog",
  services: "services", bookings: "services", live: "live", support: "support",
  volunteers: "volunteers", staff: "staff",
  packages: "packages", sponsors: "sponsors", "sponsors-pools": "pools",
  creatives: "branding", branding: "branding", "sub-sponsors": "subsponsors",
  overview: "overview", passes: "passes",
  details: "website", appearance: "website", page: "website", visitFacts: "website",
};

export function Icon({ name, className }: { name: string; className?: string }) {
  return <svg {...box} className={className}>{PATHS[name] ?? PATHS.dashboard}</svg>;
}

export function ScreenIcon({ screen }: { screen: string }) {
  return <Icon name={FOR_SCREEN[screen] ?? "dashboard"} />;
}

/** Initials for the round avatar in the topbar and the rail's footer. */
export function Avatar({ name, className }: { name: string; className?: string }) {
  const initials = name.trim().split(/\s+/).slice(0, 2)
    .map((word) => word[0] ?? "").join("").toUpperCase() || "·";
  return <span className={`avatar ${className ?? ""}`}>{initials}</span>;
}
