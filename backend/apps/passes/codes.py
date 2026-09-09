"""The code that admits.

Two decisions meet here and they pull in opposite directions:

* **D1** — the code is short-lived. It is generated at the gate and, if it is
  not used within three minutes, it is generated again.
* **D5** — entry must work offline. In a crowd of fifty thousand there is no
  mobile data, on the visitor's phone or on the gate's.

A server-minted code satisfies the first and fails the second. So the code is
derived, not minted: at purchase each leg gets a secret (`LegSecret`), the
visitor's device keeps it, and both sides compute the same value from that
secret and the clock. Nothing is transmitted at the gate. This is TOTP with a
three-minute step, which is exactly what D1 describes.

The gate verifies against a manifest — the secrets for one pandal on one day,
downloaded while it still had signal. That does mean gate devices hold secrets;
the containment is that a manifest covers one pandal for one date and a leg can
be admitted only once, so a leaked manifest buys an attacker nothing that the
`one_admission_per_leg` index does not already refuse.

The code is *not* the authorisation. `Pass.status` and `PassLeg.state` decide
whether somebody may enter; this only proves the phone at the gate is the phone
that bought the pass.
"""

import base64
import hashlib
import hmac
import secrets
import time

# Three minutes, from D1. A code is valid for the step it was generated in.
STEP_SECONDS = 180
# Accept the neighbouring step in each direction. Gate devices run on their own
# clocks and a volunteer's tablet drifting ninety seconds must not turn away a
# visitor holding a genuine pass.
DRIFT_STEPS = 1
DIGITS = 8

PAYLOAD_PREFIX = "EDP1"


def new_secret() -> str:
    """64 random bytes, base64. Stored per leg, never reused across legs."""
    return base64.b64encode(secrets.token_bytes(64)).decode()


def counter_for(at: float | None = None) -> int:
    return int((at if at is not None else time.time()) // STEP_SECONDS)


def derive(secret: str, counter: int) -> str:
    """HMAC-SHA256 truncated to eight digits, the same on phone and gate."""
    digest = hmac.new(base64.b64decode(secret), str(counter).encode(), hashlib.sha256).digest()
    # Dynamic truncation, as in RFC 4226: take four bytes at an offset the digest
    # itself chooses, so no fixed slice of the HMAC is ever exposed.
    offset = digest[-1] & 0x0F
    truncated = int.from_bytes(digest[offset:offset + 4], "big") & 0x7FFFFFFF
    return str(truncated % 10 ** DIGITS).zfill(DIGITS)


def current(secret: str, at: float | None = None) -> str:
    return derive(secret, counter_for(at))


def payload_for(leg_id, secret: str, at: float | None = None) -> str:
    """What the phone renders as a QR code."""
    counter = counter_for(at)
    return f"{PAYLOAD_PREFIX}:{leg_id}:{counter}:{derive(secret, counter)}"


def parse(payload: str) -> tuple[str, int, str] | None:
    """Split a scanned payload, or None if it is not one of ours at all."""
    parts = (payload or "").strip().split(":")
    if len(parts) != 4 or parts[0] != PAYLOAD_PREFIX:
        return None
    leg_id, counter, code = parts[1], parts[2], parts[3]
    if not counter.lstrip("-").isdigit():
        return None
    return leg_id, int(counter), code


def verify(secret: str, counter: int, code: str, at: float | None = None) -> bool:
    """True when the code matches and its step is close enough to now.

    Compared in constant time: an attacker who could time this could otherwise
    recover a valid code digit by digit within its three-minute life.
    """
    now = counter_for(at)
    if abs(counter - now) > DRIFT_STEPS:
        return False
    return hmac.compare_digest(derive(secret, counter), code)
