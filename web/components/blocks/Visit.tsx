import type { PandalPage } from "@/lib/api";
import { blockOf } from "@/lib/api";

export function Visit({ page }: { page: PandalPage }) {
  if (page.visit_facts.length === 0) return null;
  const content = blockOf(page, "visit");
  const live = page.live_status;

  return (
    <section className="section shell" id="visit">
      <div className="section-head">
        <div>
          <p className="eyebrow">03 / Visitor Experience</p>
          <h2 className="display">{content?.headline ?? "Plan Your Visit."}</h2>
        </div>
        <div>
          <p>{content?.standfirst}</p>
          {live && (
            /* Fetched separately from the cached page — a wait time a minute old
               is worse than useless (FR-187). */
            <p className="live" style={{ marginTop: 14 }}>
              <i />
              {live.estimated_wait_minutes} min wait · {live.crowd_level_display} crowd
            </p>
          )}
        </div>
      </div>

      <div className="grid-4">
        {page.visit_facts.map((fact, index) => (
          <div className="fact" key={fact.label}>
            <p className="eyebrow">{String(index + 1).padStart(2, "0")}</p>
            <h3>{fact.label}</h3>
            <p>{fact.value}</p>
          </div>
        ))}
      </div>
    </section>
  );
}
