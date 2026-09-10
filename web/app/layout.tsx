import type { Metadata } from "next";
import { DM_Serif_Display, Poppins } from "next/font/google";

import "./globals.css";

// The brand guide names two faces and no more: DM Serif Display for headings
// and key highlights, Poppins for everything else.
const display = DM_Serif_Display({
  subsets: ["latin"],
  weight: "400",
  variable: "--font-display",
});

const body = Poppins({
  subsets: ["latin"],
  weight: ["300", "400", "500", "600"],
  variable: "--font-body",
});

// The small uppercase labels used to be set in a monospace face. The guide has
// no third font, so `--font-mono` now points at Poppins too — every rule that
// reads it keeps working, and the letterspacing is what carries the look.
export const metadata: Metadata = {
  title: "eDurgaPuja · Celebrate. Connect. Contribute.",
  description: "Bengal's spirit, now closer than ever. Pandal pages, donations, "
             + "value-added services and entry passes.",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en" className={`${display.variable} ${body.variable}`}>
      <body>{children}</body>
    </html>
  );
}
