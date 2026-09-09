import type { Metadata } from "next";
import { permanentRedirect } from "next/navigation";
import { headers } from "next/headers";

import { About } from "@/components/blocks/About";
import { ClosingCta } from "@/components/blocks/ClosingCta";
import { Donate } from "@/components/blocks/Donate";
import { Hero } from "@/components/blocks/Hero";
import { Marquee } from "@/components/blocks/Marquee";
import { Passes } from "@/components/blocks/Passes";
import { Services } from "@/components/blocks/Services";
import { SiteFooter } from "@/components/blocks/SiteFooter";
import { SiteHeader } from "@/components/blocks/SiteHeader";
import { Visit } from "@/components/blocks/Visit";
import { getPandalPage, listPandals, resolveHost, type PandalPage } from "@/lib/api";
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

  // The pandal's own palette, not a platform skin (FR-050b).
  const brand = page.brand;
  const theme = brand
    ? ({
        "--primary": brand.primary_colour,
        "--accent": brand.accent_colour,
        "--surface": brand.surface_colour,
        "--ink": brand.ink_colour,
      } as React.CSSProperties)
    : undefined;

  return (
    <div style={theme}>
      <SiteHeader page={page} />
      <Hero page={page} />
      <Marquee page={page} />
      <About page={page} />
      <Services page={page} />
      <Passes page={page} />
      <Donate page={page} />
      <Visit page={page} />
      <ClosingCta page={page} />
      <SiteFooter page={page} />
    </div>
  );
}

/** Shown on a bare host in development, where there is no subdomain to read. */
async function Index() {
  const pandals = await listPandals();
  return (
    <main className="shell index">
      <p className="eyebrow">eDurgaPuja</p>
      <h1 className="display">Every pandal, its own site.</h1>
      <p style={{ maxWidth: "52ch", opacity: 0.75 }}>
        Each committee is served on its own subdomain. In development those are{" "}
        <code>&lt;slug&gt;.localhost:3000</code>, which Chrome resolves with no hosts-file
        editing.
      </p>
      <ul>
        {pandals.map((pandal) => (
          <li key={pandal.slug}>
            <a href={`http://${pandal.slug}.localhost:3000`}>
              <span>{pandal.name}</span>
              <code>{pandal.slug}.localhost:3000</code>
            </a>
          </li>
        ))}
      </ul>
    </main>
  );
}
