"use client";

import { useCallback, useEffect, useState, type ReactNode } from "react";

import { ApiError } from "@/lib/admin";

export function Tile({ label, value }: { label: string; value: ReactNode }) {
  return (
    <div className="tile">
      <span>{label}</span>
      <strong>{value}</strong>
    </div>
  );
}

export function Panel({ title, note, actions, children }: {
  title: string; note?: string; actions?: ReactNode; children: ReactNode;
}) {
  return (
    <section className="panel">
      <div className="panel-head">
        <div>
          <h2>{title}</h2>
          {note && <p>{note}</p>}
        </div>
        {actions}
      </div>
      {children}
    </section>
  );
}

export function Table({ columns, rows, empty }: {
  columns: string[]; rows: ReactNode[][]; empty: string;
}) {
  if (rows.length === 0) return <p className="empty">{empty}</p>;
  return (
    <table>
      <thead><tr>{columns.map((c) => <th key={c}>{c}</th>)}</tr></thead>
      <tbody>
        {rows.map((row, i) => (
          <tr key={i}>{row.map((cell, j) => <td key={j}>{cell}</td>)}</tr>
        ))}
      </tbody>
    </table>
  );
}

/** Status → pill tone. The six tones are the guide's; everything the API can
    return maps onto one of them. */
const TONE: Record<string, string> = {
  received: "ok", confirmed: "ok", approved: "ok", accepted: "ok", published: "ok",
  resolved: "ok", found: "ok", active: "ok", completed: "ok", admitted: "ok",
  pending: "wait", pending_review: "wait", held: "wait", new: "wait", lost: "wait",
  open: "wait", manual_override: "wait",
  upcoming: "upcoming", scheduled: "upcoming",
  visited: "visited", used: "visited",
  draft: "off", off: "off", inactive: "off",
  rejected: "bad", failed: "bad", expired: "bad", declined: "bad", cancelled: "bad",
  duplicate: "bad", invalid: "bad", sold_out: "bad",
};

/** A status chip. `label` overrides the text when the value is only the tone —
    a role grant is coloured like an active state but reads as its own words. */
export function Pill({ value, label }: { value: string; label?: string }) {
  return (
    <span className={`pill pill-${TONE[value] ?? "off"}`}>
      {label ?? value.replace(/_/g, " ")}
    </span>
  );
}

/** Load once, and give the caller a way to reload after a write. */
export function useLoad<T>(fn: () => Promise<T>, deps: unknown[] = []) {
  const [data, setData] = useState<T | null>(null);
  const [error, setError] = useState("");
  const [nonce, setNonce] = useState(0);

  useEffect(() => {
    let live = true;
    fn().then((d) => live && setData(d))
        .catch((e) => live && setError(e instanceof ApiError ? e.message : "Could not load."));
    return () => { live = false; };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [...deps, nonce]);

  return { data, error, reload: useCallback(() => setNonce((n) => n + 1), []) };
}

/** A form that reports what the server said, rather than swallowing it. */
export function Form({ submit, children, label = "Save", onDone }: {
  submit: () => Promise<unknown>; children: ReactNode; label?: string; onDone?: () => void;
}) {
  const [busy, setBusy] = useState(false);
  const [message, setMessage] = useState<{ tone: string; text: string } | null>(null);

  return (
    <form className="form" onSubmit={async (event) => {
      event.preventDefault();
      setBusy(true); setMessage(null);
      try {
        await submit();
        setMessage({ tone: "ok", text: "Saved." });
        onDone?.();
      } catch (caught) {
        setMessage({
          tone: "error",
          text: caught instanceof ApiError ? caught.message : "That did not work.",
        });
      } finally { setBusy(false); }
    }}>
      {children}
      <button className="abtn" disabled={busy}>{busy ? "Working…" : label}</button>
      {message && <p className="msg" data-tone={message.tone}>{message.text}</p>}
    </form>
  );
}

export function Field({ label, ...props }: { label: string } & React.InputHTMLAttributes<HTMLInputElement>) {
  return (
    <label>
      <span>{label}</span>
      <input {...props} />
    </label>
  );
}

export function Select({ label, children, ...props }: { label: string; children: ReactNode }
  & React.SelectHTMLAttributes<HTMLSelectElement>) {
  return (
    <label>
      <span>{label}</span>
      <select {...props}>{children}</select>
    </label>
  );
}

/** Copies to the clipboard and says so — the recording's Copy button. */
export function CopyButton({ text }: { text: string }) {
  const [done, setDone] = useState(false);
  return (
    <button className="abtn abtn-quiet" onClick={async () => {
      try {
        await navigator.clipboard.writeText(text);
        setDone(true);
        setTimeout(() => setDone(false), 1600);
      } catch { /* clipboard blocked; the link is on screen anyway */ }
    }}>{done ? "Copied" : "Copy"}</button>
  );
}
