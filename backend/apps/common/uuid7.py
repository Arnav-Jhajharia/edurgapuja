"""UUIDv7 — time-ordered UUIDs (RFC 9562).

Opaque to the outside world like uuid4, but monotonic enough that B-tree inserts
stay local instead of scattering across the index.
"""

import os
import time
import uuid


def uuid7() -> uuid.UUID:
    unix_ms = int(time.time() * 1000)
    rand = os.urandom(10)
    b = bytearray(16)
    b[0:6] = unix_ms.to_bytes(6, "big")
    b[6] = 0x70 | (rand[0] & 0x0F)      # version 7
    b[7] = rand[1]
    b[8] = 0x80 | (rand[2] & 0x3F)      # variant 10
    b[9:16] = rand[3:10]
    return uuid.UUID(bytes=bytes(b))
