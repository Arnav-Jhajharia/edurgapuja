import type { PandalPage } from "@/lib/api";

export function SiteHeader({ page }: { page: PandalPage }) {
  const initials = page.pandal.name
    .split(" ")
    .map((w) => w[0])
    .join("")
    .slice(0, 2)
    .toUpperCase();

  return (
    <header className="header">
      <div className="header-inner">
        <a className="brandmark" href="#top">
          <span className="brandmark-badge">{initials}</span>
          <span>
            <span className="brandmark-name">{page.pandal.name}</span>
            <br />
            <span className="eyebrow">
              {page.pandal.theme.name} · {page.pandal.locality}
            </span>
          </span>
        </a>

        <nav className="nav">
          <a href="#about">About</a>
          {/* Absent, not disabled, while the pandal sells no passes (FR-048). */}
          {page.capabilities.sells_passes && <a href="#donor-pass">Get Donor Pass</a>}
          {page.capabilities.accepts_donations && <a href="#donate">Donate</a>}
          {page.capabilities.offers_services && <a href="#services">Value-Added Services</a>}
          <a href="#visit">Plan Your Visit</a>
        </nav>

        <div className="header-actions">
          {page.capabilities.accepts_donations && (
            <a className="btn btn-ghost" href="#donate">
              Donate Now
            </a>
          )}
          {page.capabilities.sells_passes && (
            <a className="btn btn-solid" href="#donor-pass">
              Get Donor Pass
            </a>
          )}
        </div>
      </div>
    </header>
  );
}
