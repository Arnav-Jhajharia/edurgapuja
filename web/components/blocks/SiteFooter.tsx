import type { PandalPage } from "@/lib/api";
import { blockOf } from "@/lib/api";

export function SiteFooter({ page }: { page: PandalPage }) {
  const content = blockOf(page, "footer");

  return (
    <footer className="footer">
      <div className="shell">
        <div className="footer-grid">
          <div>
            <h2>{page.pandal.name}</h2>
            <p>{content?.blurb}</p>
          </div>

          <div>
            <p className="eyebrow">Navigate</p>
            <ul>
              <li><a href="#about">About</a></li>
              {page.capabilities.accepts_donations && <li><a href="#donate">Donate</a></li>}
              {page.capabilities.offers_services && (
                <li><a href="#services">Value-Added Services</a></li>
              )}
              <li><a href="#visit">Plan Your Visit</a></li>
            </ul>
          </div>

          <div>
            <p className="eyebrow">Contact</p>
            <ul>
              <li>{page.pandal.locality}, {page.pandal.city}</li>
              <li>{page.pandal.committee_name}</li>
            </ul>
          </div>
        </div>

        <div className="footer-base">
          <span>© 2026 {page.pandal.name}. All rights reserved.</span>
          <span>{page.pandal.theme.name} · {page.pandal.theme.name_local}</span>
        </div>
      </div>
    </footer>
  );
}
