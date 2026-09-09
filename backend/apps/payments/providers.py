"""Payment providers.

Razorpay is the intended provider, because Route lets the platform take its fee
and settle the remainder to each committee as a sub-merchant — which keeps us out
of payment-aggregator territory. Whether we use it that way is Q8, still open,
so the split configuration is not here yet.

Signature verification is real and needs no SDK. Order creation is stubbed until
credentials exist, so the whole flow is testable end to end without network.
"""

import hashlib
import hmac
import secrets
from dataclasses import dataclass
from typing import Protocol

from django.conf import settings


class SignatureError(Exception):
    """Raised when a webhook cannot be proven to have come from the provider."""


@dataclass(frozen=True)
class ProviderOrder:
    provider: str
    provider_order_id: str
    key_id: str


class PaymentProvider(Protocol):
    name: str

    def create_order(self, *, amount_paise: int, receipt: str) -> ProviderOrder: ...
    def verify_webhook(self, raw_body: bytes, signature: str) -> None: ...


class RazorpayProvider:
    name = "razorpay"

    def create_order(self, *, amount_paise: int, receipt: str) -> ProviderOrder:
        raise NotImplementedError(
            "Razorpay order creation needs live credentials; configure RAZORPAY_KEY_ID."
        )

    def verify_webhook(self, raw_body: bytes, signature: str) -> None:
        secret = settings.RAZORPAY_WEBHOOK_SECRET
        if not secret:
            raise SignatureError("Webhook secret is not configured.")
        expected = hmac.new(secret.encode(), raw_body, hashlib.sha256).hexdigest()
        # Constant-time: a normal == leaks how much of the signature matched.
        if not hmac.compare_digest(expected, signature or ""):
            raise SignatureError("Webhook signature did not verify.")


class StubProvider(RazorpayProvider):
    """Used when no credentials are configured. Creates plausible identifiers so
    the checkout flow can be exercised; verification is inherited and real."""

    def create_order(self, *, amount_paise: int, receipt: str) -> ProviderOrder:
        return ProviderOrder(provider=self.name,
                             provider_order_id=f"order_{secrets.token_hex(8)}",
                             key_id=settings.RAZORPAY_KEY_ID or "rzp_test_stub")


def get_provider() -> PaymentProvider:
    return RazorpayProvider() if settings.RAZORPAY_KEY_ID else StubProvider()
