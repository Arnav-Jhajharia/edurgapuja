import type { PandalPage } from "@/lib/api";
import { blockOf } from "@/lib/api";

export function About({ page }: { page: PandalPage }) {
  const content = blockOf(page, "about");
  if (!content) return null;
  const pillars: { title: string; body: string }[] = content.pillars ?? [];

  return (
    <section className="section shell" id="about">
      <div className="section-head">
        <div>
          <p className="eyebrow">01 / About {page.pandal.name}</p>
          <h2 className="display">{content.headline}</h2>
        </div>
        <p>{content.body}</p>
      </div>

      {pillars.length > 0 && (
        <>
          <div className="rule" />
          <div className="grid-3">
            {pillars.map((pillar, index) => (
              <div className="pillar" key={pillar.title}>
                <p className="eyebrow">{String(index + 1).padStart(2, "0")}</p>
                <h3>{pillar.title}</h3>
                <p>{pillar.body}</p>
              </div>
            ))}
          </div>
        </>
      )}
    </section>
  );
}
