"""Pluggable OTP transports.

MSG91 or Gupshup goes in here once DLT template registration clears — that has a
lead time, so it is a schedule item rather than a code one.
"""

import logging
from typing import Protocol

logger = logging.getLogger(__name__)


class OtpSender(Protocol):
    def send(self, destination: str, code: str, *, channel: str) -> None: ...


class ConsoleSender:
    """Development. Prints the code instead of spending an SMS credit."""

    def send(self, destination: str, code: str, *, channel: str) -> None:
        logger.info("OTP for %s via %s: %s", destination, channel, code)


class MemorySender:
    """Tests. Keeps the last code per destination so assertions can read it."""

    sent: dict[str, str] = {}

    def send(self, destination: str, code: str, *, channel: str) -> None:
        type(self).sent[destination] = code

    @classmethod
    def last_code(cls, destination: str) -> str | None:
        return cls.sent.get(destination)

    @classmethod
    def reset(cls) -> None:
        cls.sent.clear()
