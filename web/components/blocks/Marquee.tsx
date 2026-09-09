import type { PandalPage } from "@/lib/api";
import { blockOf } from "@/lib/api";

export function Marquee({ page }: { page: PandalPage }) {
  const content = blockOf(page, "marquee");
  const items: string[] = content?.items ?? [];
  if (!items.length) return null;

  return (
    <div className="marquee">
      <p className="eyebrow" style={{ margin: 0 }}>
        {items.map((item, index) => (
          <span key={item}>
            {item}
            {index < items.length - 1 ? " ·" : ""}
          </span>
        ))}
      </p>
    </div>
  );
}
