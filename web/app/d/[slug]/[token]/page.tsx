import type { Metadata } from "next";
import { notFound } from "next/navigation";

import { LinkDonate } from "@/components/LinkDonate";
import { getPandalPage, resolveDonationLink, rupees } from "@/lib/api";
import { pandalHref } from "@/lib/urls";

type Params = { params: Promise<{ slug: string; token: string }> };

/**
 * A shared donation link.
 *
 * Somebody was handed this by a committee member collecting for something
 * specific, so the page leads with that ask rather than dropping them at the
 * top of a marketing page and hoping they scroll. The pandal's own colours,
 * because the person sharing it said "our puja", not "a platform".
 */
export async function generateMetadata({ params }: Params): Promise<Metadata> {
  const { slug, token } = await params;
  const [link, page] = await Promise.all([
    resolveDonationLink(slug, token),
    getPandalPage(slug),
  ]);
  if (!link || !page) return { title: "eDurgaPuja" };

  const what = link.purpose || "the puja";
  return {
    title: `Donate to ${page.pandal.name}`,
    description: `A contribution towards ${what} at ${page.pandal.name}, ${page.pandal.city}.`,
    // A shared link should not be indexed: it is somebody's personal ask, and
    // it may be switched off tomorrow.
    robots: { index: false, follow: false },
  };
}

export default async function DonationLinkPage({ params }: Params) {
  const { slug, token } = await params;
  const [link, page] = await Promise.all([
    resolveDonationLink(slug, token),
    getPandalPage(slug),
  ]);

  if (!page) notFound();

  const brand = page.brand;
  const theme = brand
    ? ({
        "--primary": brand.primary_colour,
        "--accent": brand.accent_colour,
        "--surface": brand.surface_colour,
        "--ink": brand.ink_colour,
      } as React.CSSProperties)
    : undefined;

  // A link that has been switched off, or was never real. Say so plainly and
  // send them to the pandal's page, which still takes donations.
  if (!link || !link.is_active) {
    return (
      <div style={theme}>
        <main className="shell link-page">
          <p className="eyebrow">{page.pandal.name}</p>
          <h1 className="display">This link is no longer collecting.</h1>
          <p className="link-lede">
            It may have been closed by the committee, or the address may have a typo in it.
            You can still give to {page.pandal.name} directly.
          </p>
          <a className="btn btn-solid" href={`${pandalHref(page.pandal.slug)}#donate`}>
            Donate to {page.pandal.name}
          </a>
        </main>
      </div>
    );
  }

  return (
    <div style={theme}>
      <main className="shell link-page">
        <p className="eyebrow">
          {page.pandal.name} · {page.pandal.locality || page.pandal.city}
        </p>
        <h1 className="display">
          {link.purpose ? `Towards ${link.purpose}` : `Support ${page.pandal.name}`}
        </h1>
        <p className="link-lede">
          {link.suggested_amount_paise
            ? `Somebody from the committee asked you for ${rupees(link.suggested_amount_paise)}. `
            : ""}
          Give what you like — it reaches the committee directly, and you do not need an
          account.
        </p>

        <LinkDonate page={page} link={link} />

        <p className="link-foot">
          <a href={pandalHref(page.pandal.slug)}>
            See everything about {page.pandal.name} →
          </a>
        </p>
      </main>
    </div>
  );
}
