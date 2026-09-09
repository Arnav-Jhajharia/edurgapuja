import type { Metadata } from "next";
import { notFound } from "next/navigation";

import { PandalSite } from "@/components/PandalSite";
import { getPandalPage } from "@/lib/api";

type Params = { params: Promise<{ slug: string }> };

/**
 * A pandal's page, addressed by path.
 *
 * The same page the subdomain serves — it names the pandal in the URL instead
 * of in the host. This exists because a wildcard certificate is not always
 * available, and a committee waiting on DNS is still a committee with a puja
 * next month.
 *
 * The subdomain route is untouched and still works wherever it resolves, so
 * this is an addition rather than a replacement.
 */
export async function generateMetadata({ params }: Params): Promise<Metadata> {
  const { slug } = await params;
  const page = await getPandalPage(slug);
  if (!page) return { title: "eDurgaPuja" };

  return {
    title: page.seo.title,
    description: page.seo.description,
    // From the API, which knows which shape this deployment serves — pointing a
    // canonical link at an address that does not resolve is worse than an ugly
    // one.
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

export default async function PandalByPath({ params }: Params) {
  const { slug } = await params;
  const page = await getPandalPage(slug);
  if (!page) notFound();
  return <PandalSite page={page} />;
}
