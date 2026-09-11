"use client";

/**
 * Razorpay Standard Checkout.
 *
 * Every purchase on this platform — a donation, a service booking, a pass —
 * already ends the same way: an order exists and the server hands back a
 * payment intent. So this is written once against that intent rather than
 * three times against three flows.
 *
 * The secret never comes near here. The browser gets a key id and an order id,
 * both of which are public by design, and the signature it hands back is
 * checked server-side against a secret it has never seen.
 */

import { ApiError, api } from "@/lib/visitor";

export type PaymentIntent = {
  provider: string;
  provider_order_id: string;
  key_id: string;
  amount_paise: number;
  currency: string;
};

export type CheckoutResult =
  | { status: "paid"; orderId: string; receipt: string }
  | { status: "dismissed" }
  | { status: "failed"; message: string };

declare global {
  interface Window {
    Razorpay?: new (options: Record<string, unknown>) => {
      open(): void;
      on(event: string, handler: (payload: any) => void): void;
    };
  }
}

const SCRIPT = "https://checkout.razorpay.com/v1/checkout.js";

/** Load the widget once, lazily. Loading it on every page would cost every
    visitor a request for something most of them never open. */
let loading: Promise<void> | null = null;

function loadCheckout(): Promise<void> {
  if (typeof window === "undefined") return Promise.reject(new Error("no window"));
  if (window.Razorpay) return Promise.resolve();
  if (loading) return loading;

  loading = new Promise<void>((resolve, reject) => {
    const existing = document.querySelector<HTMLScriptElement>(`script[src="${SCRIPT}"]`);
    if (existing) {
      existing.addEventListener("load", () => resolve());
      existing.addEventListener("error", () => reject(new Error("could not load checkout")));
      return;
    }
    const script = document.createElement("script");
    script.src = SCRIPT;
    script.async = true;
    script.onload = () => resolve();
    script.onerror = () => { loading = null; reject(new Error("could not load checkout")); };
    document.body.appendChild(script);
  });
  return loading;
}

/**
 * Open the modal and settle up.
 *
 * Resolves rather than rejects on dismissal, because closing the modal is an
 * ordinary thing a person does and not an error to be reported as one.
 */
export async function openCheckout(intent: PaymentIntent, about: {
  name: string;
  description: string;
  prefillPhone?: string;
  prefillName?: string;
  themeColour?: string;
}): Promise<CheckoutResult> {
  if (intent.provider !== "razorpay") {
    return { status: "failed", message: `${intent.provider} checkout is not wired up yet.` };
  }

  await loadCheckout();
  const Checkout = window.Razorpay;
  if (!Checkout) return { status: "failed", message: "Could not load the payment window." };

  return new Promise<CheckoutResult>((resolve) => {
    let settled = false;
    const settle = (result: CheckoutResult) => {
      if (!settled) { settled = true; resolve(result); }
    };

    const razorpay = new Checkout({
      key: intent.key_id,
      order_id: intent.provider_order_id,
      amount: intent.amount_paise,
      currency: intent.currency || "INR",
      name: about.name,
      description: about.description,
      prefill: { contact: about.prefillPhone ?? "", name: about.prefillName ?? "" },
      theme: { color: about.themeColour ?? "#7B0D1E" },
      // Dismissal is a choice, not a failure. Without this the promise never
      // settles and the button stays spinning for ever.
      modal: { ondismiss: () => settle({ status: "dismissed" }) },
      handler: async (response: {
        razorpay_order_id: string;
        razorpay_payment_id: string;
        razorpay_signature: string;
      }) => {
        try {
          // The browser is not trusted. This is checked against the key secret
          // server-side before anything is marked paid.
          const body = await api<{ status: string; order_id: string; receipt_number: string }>(
            "/payments/verify", { method: "POST", json: response },
          );
          settle({ status: "paid", orderId: body.order_id, receipt: body.receipt_number });
        } catch (caught) {
          settle({
            status: "failed",
            message: caught instanceof ApiError
              ? caught.message
              : "We could not confirm that payment. If money left your account, it is safe — "
                + "the committee will see it shortly.",
          });
        }
      },
    });

    razorpay.on("payment.failed", (payload: any) => {
      settle({
        status: "failed",
        message: payload?.error?.description || "The payment did not go through.",
      });
    });

    razorpay.open();
  });
}
