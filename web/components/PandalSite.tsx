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
import type { PandalPage } from "@/lib/api";

/**
 * One pandal's whole page.
 *
 * Rendered identically whether it was reached by subdomain or by path — the
 * two routes differ only in how they work out *which* pandal, never in what
 * they show. That is what keeps path mode from being a second-class version.
 */
export function PandalSite({ page }: { page: PandalPage }) {
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
