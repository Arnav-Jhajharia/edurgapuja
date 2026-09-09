"""Verifying a PAN, through Sandbox (sandbox.co.in).

Two-step API: authenticate with the key pair to get a bearer token, then submit
the check. The token is cached, because Sandbox rate-limits authentication far
harder than verification and a donation page that authenticates per donor will
find that out on Ashtami.

As with payments, a stub stands in when no credentials are configured, so the
whole flow — including the refusal path — is exercisable with no network and no
real PAN. The stub is deliberately opinionated about what it accepts, so tests
can prove both outcomes.
"""

import logging
import re
from dataclasses import dataclass

import httpx
from django.conf import settings
from django.core.cache import cache

logger = logging.getLogger(__name__)

#: Five letters, four digits, one letter. The fourth letter says what kind of
#: holder it is — `P` for an individual — but that is not checked here: a HUF or
#: a trust may legitimately donate.
PAN_PATTERN = re.compile(r"^[A-Z]{5}[0-9]{4}[A-Z]$")

# Where the bearer token is cached, not a secret itself.
TOKEN_CACHE_KEY = "kyc:sandbox:token"  # noqa: S105
TOKEN_TTL_SECONDS = 60 * 50  # Sandbox tokens last an hour; refresh before that.


class KycUnavailableError(Exception):
    """The provider could not be reached or answered incomprehensibly.

    Distinct from a failed check on purpose: "we could not ask" and "the answer
    was no" must not look the same to a donor.
    """


@dataclass(frozen=True)
class PanResult:
    verified: bool
    name_on_record: str = ""
    reference: str = ""
    reason: str = ""


def normalise_pan(value: str) -> str:
    return (value or "").strip().upper().replace(" ", "")


class SandboxProvider:
    name = "sandbox"

    def _token(self) -> str:
        if cached := cache.get(TOKEN_CACHE_KEY):
            return cached

        response = httpx.post(
            f"{settings.SANDBOX_BASE_URL}/authenticate",
            headers={
                "x-api-key": settings.SANDBOX_API_KEY,
                "x-api-secret": settings.SANDBOX_API_SECRET,
                "x-api-version": settings.SANDBOX_API_VERSION,
            },
            timeout=15,
        )
        if response.status_code != 200:
            raise KycUnavailableError(f"Sandbox authenticate returned {response.status_code}")

        token = response.json().get("access_token", "")
        if not token:
            raise KycUnavailableError("Sandbox authenticate returned no token")

        cache.set(TOKEN_CACHE_KEY, token, TOKEN_TTL_SECONDS)
        return token

    def verify_pan(self, *, pan: str, name: str, date_of_birth: str = "") -> PanResult:
        try:
            response = httpx.post(
                f"{settings.SANDBOX_BASE_URL}/kyc/pan/verify",
                headers={
                    "Authorization": self._token(),
                    "x-api-key": settings.SANDBOX_API_KEY,
                    "x-api-version": settings.SANDBOX_API_VERSION,
                    "Content-Type": "application/json",
                },
                json={
                    "@entity": "in.co.sandbox.kyc.pan_verification.request",
                    "pan": pan,
                    "name_as_per_pan": name,
                    "date_of_birth": date_of_birth,
                    # Sandbox requires an explicit consent flag and a stated
                    # reason. Both are recorded on their side, which is the
                    # point of them.
                    "consent": "Y",
                    "reason": "Donation reporting under section 80G",
                },
                timeout=20,
            )
        except httpx.HTTPError as problem:
            raise KycUnavailableError(str(problem)) from problem

        if response.status_code >= 500:
            raise KycUnavailableError(f"Sandbox returned {response.status_code}")

        body = response.json() if response.content else {}
        data = body.get("data", body)

        status = str(data.get("status", "")).upper()
        if status == "VALID":
            return PanResult(
                verified=True,
                name_on_record=data.get("full_name") or data.get("name_as_per_pan") or "",
                reference=str(body.get("transaction_id") or data.get("transaction_id") or ""),
            )

        return PanResult(
            verified=False,
            reason=data.get("message") or "That PAN could not be verified.",
            reference=str(body.get("transaction_id") or ""),
        )


class StubKycProvider:
    """Stands in with no credentials.

    Accepts any well-formed PAN except ones beginning `AAAAA`, which always
    fail — so both paths are reachable in development and in tests without a
    real number ever being sent anywhere.
    """

    name = "sandbox-stub"

    def verify_pan(self, *, pan: str, name: str, date_of_birth: str = "") -> PanResult:
        if pan.startswith("AAAAA"):
            return PanResult(verified=False, reason="That PAN could not be verified.",
                             reference="stub")
        return PanResult(verified=True, name_on_record=name or "Verified Holder",
                         reference="stub")


def get_kyc_provider():
    if settings.SANDBOX_API_KEY and settings.SANDBOX_API_SECRET:
        return SandboxProvider()
    logger.info("KYC running on the stub provider; no Sandbox credentials configured")
    return StubKycProvider()
