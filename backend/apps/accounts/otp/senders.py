"""Pluggable OTP transports.

The code itself is generated, hashed, expired and verified in `service.py` — a
sender only delivers it. That matters for the choice made here: MSG91 offers an
OTP product that would generate and check the code for us, and using it would
mean throwing away the attempt limits, the supersede-on-reissue rule and the
constant-time comparison that are already written and tested. So MSG91 is used
as an SMS transport (the Flow API) and nothing more.

Which transport is live is decided by whether credentials exist, not by an
environment name — a staging box with real credentials should send real
messages, and a production box without them should not silently pretend to.
"""

import logging
from typing import Protocol

import httpx
from django.conf import settings

logger = logging.getLogger(__name__)


class OtpDeliveryError(Exception):
    """The message could not be handed to the network.

    Distinct from a rejected code: nobody has been sent anything, so the caller
    should not leave a live challenge behind that the person cannot answer.
    """


class OtpSender(Protocol):
    def send(self, destination: str, code: str, *, channel: str) -> None: ...


class ConsoleSender:
    """Development. Logs the code instead of spending an SMS credit."""

    name = "console"

    def send(self, destination: str, code: str, *, channel: str) -> None:
        logger.info("OTP for %s via %s: %s", destination, channel, code)


class MemorySender:
    """Tests. Keeps the last code per destination so assertions can read it."""

    name = "memory"
    sent: dict[str, str] = {}

    def send(self, destination: str, code: str, *, channel: str) -> None:
        type(self).sent[destination] = code

    @classmethod
    def last_code(cls, destination: str) -> str | None:
        return cls.sent.get(destination)

    @classmethod
    def reset(cls) -> None:
        cls.sent.clear()


def msg91_mobile(destination: str) -> str:
    """E.164 as MSG91 wants it: digits only, country code included, no plus.

    Numbers reach us as `+919876543210`. A ten-digit number with no country code
    is assumed Indian, because that is what the platform serves and the
    alternative is silently failing to deliver.
    """
    digits = "".join(ch for ch in destination if ch.isdigit())
    if len(digits) == 10:
        return f"{settings.MSG91_DEFAULT_COUNTRY_CODE}{digits}"
    return digits


class Msg91Sender:
    """Delivers over MSG91's Flow API against a DLT-approved template."""

    name = "msg91"

    @property
    def sender_id(self) -> str:
        # MSG91 calls the six-character DLT header both things; either will do.
        return settings.MSG_91_SENDER or settings.MSG_91_SENDER_ID

    def send(self, destination: str, code: str, *, channel: str) -> None:
        payload = {
            "template_id": settings.MSG91_TEMPLATE_ID,
            "short_url": "0",
            "recipients": [{
                "mobiles": msg91_mobile(destination),
                # The key has to match the variable in the approved template.
                settings.MSG91_CODE_VARIABLE: code,
            }],
        }
        if self.sender_id:
            payload["sender"] = self.sender_id

        try:
            response = httpx.post(
                f"{settings.MSG91_BASE_URL}/flow/",
                headers={"authkey": settings.MSG_91_AUTH_KEY,
                         "Content-Type": "application/json",
                         "Accept": "application/json"},
                json=payload,
                timeout=15,
            )
        except httpx.HTTPError as problem:
            raise OtpDeliveryError(f"MSG91 unreachable: {problem}") from problem

        if response.status_code != 200:
            # The body carries MSG91's reason, and it is worth logging: a
            # rejected template or an unapproved header fails every send until
            # somebody reads it.
            raise OtpDeliveryError(
                f"MSG91 returned {response.status_code}: {response.text[:200]}"
            )

        body = response.json() if response.content else {}
        if str(body.get("type", "success")).lower() == "error":
            raise OtpDeliveryError(f"MSG91 refused the message: {body.get('message')}")

        # Never the code, and never the whole number.
        logger.info("OTP sent via MSG91 to ***%s", msg91_mobile(destination)[-4:])


def default_sender() -> OtpSender:
    """MSG91 when it is configured, the console when it is not.

    Configuration decides, not DEBUG: a staging box with real credentials should
    send real messages, and a box without them must not quietly pretend to.
    """
    if settings.MSG_91_AUTH_KEY and settings.MSG91_TEMPLATE_ID:
        return Msg91Sender()
    return ConsoleSender()
