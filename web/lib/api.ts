/**
 * Server-side reads of the pandal API.
 *
 * These run in the Next server, not the browser, so they talk to the API origin
 * directly and never touch CORS. Browser calls go through the /api rewrite so
 * they are same-origin.
 */

const API_ORIGIN = process.env.API_ORIGIN ?? "http://127.0.0.1:8000";

export type Brand = {
  primary_colour: string;
  accent_colour: string;
  surface_colour: string;
  ink_colour: string;
  display_font: string;
  body_font: string;
  logo: string | null;
  mark: string | null;
};

export type Block = {
  kind: string;
  sort_order: number;
  content: Record<string, any>;
};

export type ServiceFormField = {
  key: string;
  label: string;
  kind: "text" | "textarea" | "phone" | "email" | "number" | "date" | "time"
      | "select" | "checkbox";
  required: boolean;
  help_text: string;
  options: string[];
  is_sensitive: boolean;
  sort_order: number;
};

export type PandalPage = {
  pandal: {
    id: string;
    slug: string;
    name: string;
    committee_name: string;
    locality: string;
    city: string;
    canonical_url: string;
    theme: { name: string; name_local: string };
  };
  seo: {
    title: string;
    description: string;
    og_image_url: string | null;
    locales: string[];
  };
  capabilities: {
    sells_passes: boolean;
    accepts_donations: boolean;
    offers_services: boolean;
  };
  brand: Brand | null;
  blocks: Block[];
  visit_facts: { label: string; value: string; sort_order: number }[];
  donation_offerings: { id: string; amount_paise: number; label: string; description: string }[];
  services: {
    id: string;
    name: string;
    slug: string;
    type: string;
    description: string;
    price_paise: number;
    max_per_booking: number;
    requires_capacity: boolean;
    // The form is data, not a shape the client hard-codes — a pandal inventing
    // a service nobody thought of gets a working booking form with no change
    // here (FR-133).
    fields: ServiceFormField[];
  }[];
  // Empty until the committee switches passes on. The block below reads this
  // and renders nothing when it is empty, so turning passes on is a flag —
  // there is no second version of the page (FR-050a).
  passes: {
    id: string;
    product: "individual" | "group" | "city";
    product_display: string;
    category: { id: string; name: string; slug: string; description: string };
    from_date: string;
    to_date: string;
    from_time: string | null;
    to_time: string | null;
    price_paise: number;
    max_party_size: number;
  }[];
  live_status: {
    estimated_wait_minutes: number | null;
    crowd_level: string;
    crowd_level_display: string;
    note: string;
    updated_at: string;
    age_seconds: number;
  } | null;
};

/** Turn an incoming host into a slug, or into a redirect (D12). */
export async function resolveHost(
  host: string,
): Promise<{ status: "ok"; slug: string } | { status: "redirect"; redirect_to: string } | null> {
  const response = await fetch(
    `${API_ORIGIN}/api/v1/site/resolve?host=${encodeURIComponent(host)}`,
    { next: { revalidate: 3600 } },
  );
  if (!response.ok) return null;
  return response.json();
}

/** One request renders the page. */
export async function getPandalPage(slug: string, language = "en"): Promise<PandalPage | null> {
  const response = await fetch(`${API_ORIGIN}/api/v1/pandals/${slug}/page`, {
    headers: { "Accept-Language": language },
    next: { revalidate: 60, tags: [`pandal:${slug}`] },
  });
  if (!response.ok) return null;
  return response.json();
}

export async function listPandals(): Promise<{ slug: string; name: string; city_name: string }[]> {
  const response = await fetch(`${API_ORIGIN}/api/v1/pandals/`, { next: { revalidate: 300 } });
  if (!response.ok) return [];
  const body = await response.json();
  return body.results ?? body;
}

export function rupees(paise: number): string {
  return `₹${(paise / 100).toLocaleString("en-IN", { maximumFractionDigits: 0 })}`;
}

export function blockOf(page: PandalPage, kind: string): Record<string, any> | null {
  return page.blocks.find((b) => b.kind === kind)?.content ?? null;
}

export type DonationLink = {
  id: string;
  pandal: string;
  pandal_slug: string;
  suggested_amount_paise: number | null;
  purpose: string;
  token: string;
  path: string;
  is_active: boolean;
};

/** Resolve a shared donation link to what it is collecting for (FR-140). */
export async function resolveDonationLink(
  slug: string, token: string,
): Promise<DonationLink | null> {
  const response = await fetch(
    `${API_ORIGIN}/api/v1/d/${encodeURIComponent(slug)}/${encodeURIComponent(token)}`,
    // Never cached: a link the committee has just switched off must stop
    // collecting now, not in sixty seconds.
    { cache: "no-store" },
  );
  if (!response.ok) return null;
  return response.json();
}
