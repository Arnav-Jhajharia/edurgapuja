"use client";

import type { ReactNode } from "react";

/**
 * The panel a visitor buys from — a `<form>` once they are signed in, a plain
 * `<div>` before that.
 *
 * HTML forms cannot nest, and the sign-in step has to be a form of its own so
 * that pressing Enter sends the code rather than attempting the purchase.
 * Switching the element is the honest way to get both.
 */
export function Card({ signedIn, onSubmit, className = "offer-card", children }: {
  signedIn: boolean;
  onSubmit: (event: React.FormEvent) => void;
  className?: string;
  children: ReactNode;
}) {
  if (!signedIn) return <div className={className}>{children}</div>;
  return <form className={className} onSubmit={onSubmit}>{children}</form>;
}
