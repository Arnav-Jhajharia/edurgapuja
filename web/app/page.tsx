import type { Metadata } from "next";
import { permanentRedirect } from "next/navigation";
import { headers } from "next/headers";

import { PandalSite } from "@/components/PandalSite";
import { getPandalPage, listPandals, resolveHost, type PandalPage } from "@/lib/api";
import { pandalDisplayHost, pandalHref, ROUTING } from "@/lib/urls";
import { slugFromHost } from "@/lib/host";

async function resolve(): Promise<PandalPage | null> {
  const slug = await slugFromHost();
  if (!slug) return null;

  // A renamed pandal keeps its old host alive as a permanent redirect (FR-248),
  // and a committee may bring its own domain — so this is a lookup, not string
  // manipulation. The optimistic strip above covers the common case.
  const page = await getPandalPage(slug);
  if (page) return page;

  const host = (await headers()).get("host") ?? "";
  const resolved = await resolveHost(host);
  if (resolved?.status === "redirect") permanentRedirect(resolved.redirect_to);
  if (resolved?.status === "ok") return getPandalPage(resolved.slug);
  return null;
}

export async function generateMetadata(): Promise<Metadata> {
  const page = await resolve();
  if (!page) return { title: "eDurgaPuja" };

  return {
    title: page.seo.title,
    description: page.seo.description,
    alternates: { canonical: page.pandal.canonical_url },
    openGraph: {
      title: page.seo.title,
      description: page.seo.description,
      url: page.pandal.canonical_url,
      type: "website",
      images: page.seo.og_image_url ? [page.seo.og_image_url] : undefined,
    },
    twitter: { card: "summary_large_image", title: page.seo.title },
  };
}

export default async function Page() {
  const page = await resolve();
  if (!page) return <Index />;
  return <PandalSite page={page} />;
}

/** The directory, shown on a bare host where no pandal is named. */
async function Index() {
  const pandals = await listPandals();
  return (
    <main className="shell index">
      <p className="eyebrow">eDurgaPuja</p>
      <h1 className="display">Every pandal, its own site.</h1>
      <p style={{ maxWidth: "52ch", opacity: 0.75 }}>
        {ROUTING === "subdomain"
          ? "Each committee is served on its own subdomain."
          : "Each committee has its own page."}
      </p>
      <ul>
        {pandals.map((pandal) => (
          <li key={pandal.slug}>
            {/* From lib/urls, so this link is correct in either mode and on
                any host — including a laptop, where it used to be hardcoded. */}
            <a href={pandalHref(pandal.slug)}>
              <span>{pandal.name}</span>
              <code>{pandalDisplayHost(pandal.slug)}</code>
            </a>
          </li>
        ))}
      </ul>
    </main>
  );
}
