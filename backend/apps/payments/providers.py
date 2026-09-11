"""Payment providers.

Two of them, because a puja committee losing an evening to one gateway's outage
is a real failure mode and switching should be a setting rather than a release.
Razorpay is the default: Route lets the platform take its fee and settle the
remainder to each committee as a sub-merchant, which keeps us out of
payment-aggregator territory. Cashfree covers the same ground and is the
fallback.

The two differ in ways that matter and are easy to get wrong:

* **Order creation.** Razorpay wants amounts in paise; Cashfree wants rupees as
  a decimal. Getting that backwards is a hundredfold error in either direction.
* **Webhook signatures.** Razorpay signs the raw body with HMAC-SHA256 as hex.
  Cashfree signs `timestamp + body` and base64-encodes it, so the timestamp
  header is part of the proof rather than metadata.

Signature verification is real for both and needs no SDK. Order creation is
stubbed until credentials exist, so the whole flow is testable without network.
"""

import base64
import hashlib
import hmac
import secrets
from dataclasses import dataclass
from typing import Protocol

from django.conf import settings

#: Razorpay's floor. Below this the gateway refuses the order outright, so it is
#: better refused here where the message can say why.
MINIMUM_PAISE = 100


class SignatureError(Exception):
    """Raised when a payment cannot be proven to have come from the provider."""


class PaymentAmountError(Exception):
    """The amount is one the gateway will not accept."""


class PaymentRejectedError(Exception):
    """The gateway understood the request and refused it."""


class PaymentUnavailableError(Exception):
    """The gateway could not be reached, or failed on its own side."""


@dataclass(frozen=True)
class ProviderOrder:
    provider: str
    provider_order_id: str
    key_id: str


class PaymentProvider(Protocol):
    name: str

    def create_order(self, *, amount_paise: int, receipt: str) -> ProviderOrder: ...
    def verify_webhook(self, raw_body: bytes, signature: str, timestamp: str = "") -> None: ...


class RazorpayProvider:
    name = "razorpay"

    def _client(self):
        import razorpay

        return razorpay.Client(auth=(settings.RAZORPAY_KEY_ID, settings.RAZORPAY_KEY_SECRET))

    def create_order(self, *, amount_paise: int, receipt: str) -> ProviderOrder:
        """Create the order Standard Checkout opens against.

        Razorpay takes **paise**, which is what the rest of this codebase
        already holds money in, so nothing is converted here — the conversion
        that does exist is Cashfree's, which wants rupees as a decimal.
        """
        import razorpay.errors

        if amount_paise < MINIMUM_PAISE:
            raise PaymentAmountError(
                f"Razorpay will not take less than ₹{MINIMUM_PAISE / 100:.0f}."
            )

        try:
            created = self._client().order.create({
                "amount": amount_paise,
                "currency": "INR",
                # Ours, echoed back on the order and in the dashboard, so a
                # support question can be traced to one of our orders.
                "receipt": receipt[:40],
                # Razorpay captures automatically rather than leaving the
                # payment authorised and waiting for a second call.
                "payment_capture": 1,
            })
        except razorpay.errors.BadRequestError as problem:
            raise PaymentRejectedError(str(problem)) from problem
        except Exception as problem:
            # Anything else — network, 5xx, a bad key — is ours to retry, not
            # the donor's to puzzle over.
            raise PaymentUnavailableError(str(problem)) from problem

        return ProviderOrder(provider=self.name,
                             provider_order_id=created["id"],
                             key_id=settings.RAZORPAY_KEY_ID)

    def verify_handoff(self, *, order_id: str, payment_id: str, signature: str) -> None:
        """Check the signature the browser hands back after the modal closes.

        A different thing from the webhook signature, and easy to confuse: the
        webhook signs the whole request body, this signs `order_id|payment_id`
        with the API secret. The browser is not trusted, so this is what stops
        somebody posting a made-up payment id and having it marked paid.
        """
        secret = settings.RAZORPAY_KEY_SECRET
        if not secret:
            raise SignatureError("Razorpay key secret is not configured.")

        expected = hmac.new(secret.encode(), f"{order_id}|{payment_id}".encode(),
                            hashlib.sha256).hexdigest()
        if not hmac.compare_digest(expected, signature or ""):
            raise SignatureError("Payment signature did not verify.")

    def verify_webhook(self, raw_body: bytes, signature: str, timestamp: str = "") -> None:
        secret = settings.RAZORPAY_WEBHOOK_SECRET
        if not secret:
            raise SignatureError("Webhook secret is not configured.")
        expected = hmac.new(secret.encode(), raw_body, hashlib.sha256).hexdigest()
        # Constant-time: a normal == leaks how much of the signature matched.
        if not hmac.compare_digest(expected, signature or ""):
            raise SignatureError("Webhook signature did not verify.")


class CashfreeProvider:
    name = "cashfree"

    def create_order(self, *, amount_paise: int, receipt: str) -> ProviderOrder:
        raise NotImplementedError(
            "Cashfree order creation needs live credentials; configure CASHFREE_APP_ID."
        )

    def verify_webhook(self, raw_body: bytes, signature: str, timestamp: str = "") -> None:
        """Cashfree signs `timestamp + body`, base64 of the HMAC.

        The timestamp is part of what is signed, not a hint — verifying the body
        alone would accept a replay of yesterday's captured event with today's
        header, which is exactly the attack the scheme exists to stop.
        """
        secret = settings.CASHFREE_SECRET_KEY
        if not secret:
            raise SignatureError("Webhook secret is not configured.")
        if not timestamp:
            raise SignatureError("Webhook timestamp is missing.")

        signed = timestamp.encode() + raw_body
        digest = hmac.new(secret.encode(), signed, hashlib.sha256).digest()
        expected = base64.b64encode(digest).decode()
        if not hmac.compare_digest(expected, signature or ""):
            raise SignatureError("Webhook signature did not verify.")


class StubProvider(RazorpayProvider):
    """Used when no credentials are configured. Creates plausible identifiers so
    the checkout flow can be exercised; verification is inherited and real."""

    def create_order(self, *, amount_paise: int, receipt: str) -> ProviderOrder:
        return ProviderOrder(provider=self.name,
                             provider_order_id=f"order_{secrets.token_hex(8)}",
                             key_id=settings.RAZORPAY_KEY_ID or "rzp_test_stub")


class StubCashfreeProvider(CashfreeProvider):
    def create_order(self, *, amount_paise: int, receipt: str) -> ProviderOrder:
        return ProviderOrder(provider=self.name,
                             provider_order_id=f"cf_{secrets.token_hex(8)}",
                             key_id=settings.CASHFREE_APP_ID or "cf_test_stub")


#: Which provider each name resolves to, and whether it is configured for real.
def _razorpay() -> PaymentProvider:
    return RazorpayProvider() if settings.RAZORPAY_KEY_ID else StubProvider()


def _cashfree() -> PaymentProvider:
    return CashfreeProvider() if settings.CASHFREE_APP_ID else StubCashfreeProvider()


BUILDERS = {"razorpay": _razorpay, "cashfree": _cashfree}


def available() -> list[str]:
    """Which providers a client may ask for. Order matters: the first is the
    default, and a client that expresses no preference gets it."""
    names = [n.strip() for n in settings.PAYMENT_PROVIDERS.split(",") if n.strip()]
    return [n for n in names if n in BUILDERS] or ["razorpay"]


def get_provider(name: str = "") -> PaymentProvider:
    """Resolve a provider by name, falling back to the configured default.

    An unknown or disabled name falls back rather than failing: a client asking
    for a provider we have turned off should still be able to pay.
    """
    allowed = available()
    chosen = name if name in allowed else allowed[0]
    return BUILDERS[chosen]()
