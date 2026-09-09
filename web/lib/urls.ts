/**
 * Where a pandal's page lives.
 *
 * Every link to a pandal comes from here, because there are two shapes and the
 * deployment decides which. Before this the answer was written out in nine
 * places, three of which still said `localhost:3000` — links that worked on a
 * laptop and were broken the moment anything was deployed.
 *
 * - **subdomain** — `ballygunge-cultural.itsmedonna.com`, the intended shape.
 *   Needs a wildcard certificate.
 * - **path** — `itsmedonna.com/p/ballygunge-cultural`, for deployments that
 *   cannot issue one.
 *
 * Only *link building* changes between the two. Host resolution keeps working
 * regardless, so a subdomain that does resolve still serves the page — which is
 * what makes switching modes a config change rather than a migration.
 */

export type Routing = "subdomain" | "path";

export const ROUTING: Routing =
  (process.env.NEXT_PUBLIC_PANDAL_ROUTING as Routing) ?? "subdomain";

/** The bare domain, without scheme or port: `itsmedonna.com`, `localhost`. */
export const SITE_DOMAIN = process.env.NEXT_PUBLIC_SITE_DOMAIN ?? "edurgapuja.app";

/**
 * A link to a pandal's page, relative wherever it can be.
 *
 * In path mode this is `/p/<slug>` — a relative link, which cannot point at the
 * wrong host because it names no host at all. That is the whole reason path
 * mode is safe to switch on: nothing has to know where it is running.
 */
export function pandalHref(slug: string): string {
  return ROUTING === "path" ? `/p/${slug}` : absolutePandalUrl(slug);
}

/**
 * An absolute link, for somewhere a relative one will not do — a copy button,
 * an email, an OG tag.
 *
 * `origin` is where the link is being built from; on the client it defaults to
 * the page you are on, which is right in every case and needs no configuration.
 */
export function absolutePandalUrl(slug: string, origin?: string): string {
  const base = origin ?? currentOrigin();
  const { protocol, host } = split(base);

  if (ROUTING === "path") return `${protocol}//${host}/p/${slug}`;

  // Strip any pandal label already present, so building a link from one
  // pandal's page to another does not stack subdomains.
  const bare = stripSubdomain(host);
  return `${protocol}//${slug}.${bare}`;
}

/**
 * A shareable donation link.
 *
 * The long form `/d/<slug>/<token>` is used in path mode because it carries the
 * pandal in the path and therefore works on any host. The short form only works
 * where the host itself names the pandal.
 */
export function donationLinkUrl(slug: string, token: string, origin?: string): string {
  const base = origin ?? currentOrigin();
  const { protocol, host } = split(base);

  if (ROUTING === "path") return `${protocol}//${host}/d/${slug}/${token}`;
  return `${protocol}//${slug}.${stripSubdomain(host)}/d/${token}`;
}

/** What to show a committee as "your address". */
export function pandalDisplayHost(slug: string): string {
  return ROUTING === "path" ? `${SITE_DOMAIN}/p/${slug}` : `${slug}.${SITE_DOMAIN}`;
}

// ---------------------------------------------------------------------------

function currentOrigin(): string {
  if (typeof window !== "undefined") return window.location.origin;
  // Server-side callers that care pass an origin explicitly; this is the
  // last-resort default and is only ever used for absolute links.
  return `https://${SITE_DOMAIN}`;
}

function split(origin: string): { protocol: string; host: string } {
  try {
    const url = new URL(origin);
    return { protocol: url.protocol, host: url.host };
  } catch {
    return { protocol: "https:", host: origin.replace(/^https?:\/\//, "") };
  }
}

/**
 * `ballygunge-cultural.itsmedonna.com` → `itsmedonna.com`, and
 * `localhost:3000` → `localhost:3000`.
 *
 * Anything that already equals the site domain is left alone; otherwise the
 * first label is dropped only when what remains still looks like the site.
 */
function stripSubdomain(host: string): string {
  const [name, port] = host.split(":");
  const suffix = port ? `:${port}` : "";

  if (name === SITE_DOMAIN || name === "localhost") return host;
  if (name.endsWith(`.${SITE_DOMAIN}`)) return `${SITE_DOMAIN}${suffix}`;
  if (name.endsWith(".localhost")) return `localhost${suffix}`;
  return host;
}
