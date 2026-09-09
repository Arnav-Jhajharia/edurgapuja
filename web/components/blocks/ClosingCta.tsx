import type { PandalPage } from "@/lib/api";
import { blockOf } from "@/lib/api";

export function ClosingCta({ page }: { page: PandalPage }) {
  const content = blockOf(page, "closing_cta");
  if (!content) return null;

  return (
    <section className="section on-primary">
      <div className="shell closing">
        <h2 className="display">{content.headline}</h2>
        <p>{content.body}</p>
        <div className="hero-actions">
          {page.capabilities.accepts_donations && (
            <a className="btn btn-solid" href="#donate">
              Donate Now
            </a>
          )}
          {page.capabilities.offers_services && (
            <a className="btn btn-ghost" href="#services">
              Explore Services
            </a>
          )}
        </div>
      </div>
    </section>
  );
}
