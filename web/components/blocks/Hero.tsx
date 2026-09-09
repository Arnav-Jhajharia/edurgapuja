import type { PandalPage } from "@/lib/api";
import { blockOf } from "@/lib/api";

export function Hero({ page }: { page: PandalPage }) {
  const content = blockOf(page, "hero");
  if (!content) return null;

  return (
    <section className="hero" id="top">
      <div className="shell hero-grid">
        <div>
          <p className="eyebrow">{content.eyebrow}</p>
          <h1 className="display">{content.headline}</h1>
          <p>{content.standfirst}</p>

          <div className="hero-actions">
            {page.capabilities.accepts_donations && (
              <a className="btn btn-solid" href="#donate">
                {content.primary_cta ?? "Donate Now"}
              </a>
            )}
            {page.capabilities.offers_services && (
              <a className="btn btn-ghost" href="#services">
                {content.secondary_cta ?? "Explore Services"}
              </a>
            )}
          </div>

          <div className="hero-meta">
            <span className="eyebrow">Theme</span>
            <strong>
              {page.pandal.theme.name}
              {page.pandal.theme.name_local ? ` (${page.pandal.theme.name_local})` : ""}
            </strong>
          </div>
        </div>

        <div className="hero-figure" aria-hidden="true">
          <span>{page.pandal.theme.name_local?.slice(0, 2) || "ॐ"}</span>
        </div>
      </div>
    </section>
  );
}
