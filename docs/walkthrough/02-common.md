# Part 2 · The common app

Five files, no domain logic, and everything else depends on them. `apps/common/`
holds the pieces that would otherwise be copied into every other app: the primary
key generator, the abstract base models, the error envelope, pagination, and the
health check.

---

## `apps/common/uuid7.py`

The whole file:

```python
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
```

**`import os`** — for `os.urandom`, which reads from the operating system's
cryptographic random source. Not the `random` module, which is a deterministic
pseudo-random generator seeded from the clock and is unsuitable for anything that
must be unguessable.

**`import time`** — for `time.time()`, seconds since 1970 as a float.

**`import uuid`** — the standard library's UUID type, used at the end to wrap the
sixteen bytes.

**`def uuid7() -> uuid.UUID:`** — a plain function, because that is what Django's
`default=` wants. Passing `uuid7` hands over the function itself; Django calls it
once per row.

**`unix_ms = int(time.time() * 1000)`** — the current time in milliseconds.
`time.time()` returns something like `1789234567.891`; multiplying and truncating
gives `1789234567891`. That number fits comfortably in 48 bits, which is what the
specification allocates and is good until the year 10889.

**`rand = os.urandom(10)`** — ten random bytes, of which the layout below uses all
ten. Drawing them in one call is both faster and cleaner than ten separate calls.

**`b = bytearray(16)`** — sixteen zero bytes, mutable. A UUID is exactly 128 bits.
`bytes` would not work here because it is immutable and the next lines assign into
slices.

**`b[0:6] = unix_ms.to_bytes(6, "big")`** — the first six bytes are the timestamp,
most significant byte first. Big-endian is what makes the sort order work: when
two UUIDs are compared byte by byte, the earlier timestamp sorts first, which is
the entire point of version 7.

**`b[6] = 0x70 | (rand[0] & 0x0F)`** — byte six carries the version in its top four
bits.

- `rand[0] & 0x0F` keeps only the *low* four bits of a random byte. `0x0F` is
  `00001111`, so the `&` masks the top half away.
- `0x70` is `01110000` — the number 7 sitting in the top four bits.
- `|` combines them: `0111` then four random bits.

So the version nibble reads as 7, and four bits of entropy are preserved rather
than wasted.

**`b[7] = rand[1]`** — byte seven is entirely random. Nothing structural lives
here.

**`b[8] = 0x80 | (rand[2] & 0x3F)`** — byte eight carries the *variant* in its top
two bits.

- `0x3F` is `00111111`, so `rand[2] & 0x3F` keeps the low six bits.
- `0x80` is `10000000`, setting the top bit and clearing the next.
- The result begins `10`, which is the RFC 4122/9562 variant marker that says
  "this is a standard UUID and the other fields mean what the spec says".

**`b[9:16] = rand[3:10]`** — the last seven bytes are pure randomness. Counting up:
4 bits in byte six, 8 in byte seven, 6 in byte eight and 56 here, giving 74 random
bits per millisecond. Two UUIDs generated in the same millisecond collide with
probability around one in 10²². Not a concern.

**`return uuid.UUID(bytes=bytes(b))`** — wrap the sixteen bytes in a real `UUID`
object. `bytes(b)` converts the mutable `bytearray` back to immutable `bytes`,
which is what the constructor accepts. The `bytes=` keyword matters: `UUID()` has
several mutually exclusive constructors (`hex=`, `int=`, `bytes=`,
`bytes_le=`, `fields=`), and passing the wrong one silently means something else.

**Why not the standard library?** Python 3.14 added `uuid.uuid6/7/8`, but this
project pins 3.13 for Django compatibility, and fifteen lines is a smaller cost
than the version constraint. When the pin moves, this file can be deleted and the
import swapped.

---

## `apps/common/models.py`

### Imports

```python
from django.conf import settings
from django.db import models

from .uuid7 import uuid7
```

**`from django.conf import settings`** — not the settings module itself but a lazy
proxy. That laziness matters: this module is imported while Django is still
starting, and touching a real settings module too early raises
`ImproperlyConfigured`. The proxy defers the lookup until an attribute is
actually read.

**`from django.db import models`** — the namespace holding every field type,
`Model`, `Q`, `F`, `Index`, `UniqueConstraint` and the rest.

**`from .uuid7 import uuid7`** — a relative import; the leading dot means "from
this package". Fine within an app, and it makes moving the package painless.

### `TimeStampedModel`

```python
class TimeStampedModel(models.Model):
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        abstract = True
```

**`created_at`** — `auto_now_add=True` sets the value on the *first* save and
never again. It also makes the field non-editable, so it will not appear in a
form. `db_index=True` because nearly every list in this system sorts by it.

**`updated_at`** — `auto_now=True` overwrites the value on *every* save. Note that
it is deliberately *not* indexed: nothing sorts by it, and an index would be pure
write cost.

Both ignore any value you assign, which is exactly why the test suite writes past
timestamps with `.update()` instead — a queryset update goes straight to SQL and
skips the field's `pre_save` hook.

**`class Meta: abstract = True`** — no table. The fields are copied into each
concrete subclass.

### `BaseModel`

```python
class BaseModel(TimeStampedModel):
    id = models.UUIDField(primary_key=True, default=uuid7, editable=False)

    class Meta:
        abstract = True
```

**`id = models.UUIDField(...)`** — declaring a field named `id` replaces the
implicit `BigAutoField` Django would otherwise add.

- `primary_key=True` also implies `unique=True` and `null=False`.
- `default=uuid7` — the function, uncalled. `default=uuid7()` would evaluate once
  at import and give every row the same ID.
- `editable=False` keeps it out of forms and the admin.

`UUIDField` maps to a native Postgres `uuid` column — sixteen bytes, not a
36-character string.

**A second `class Meta`** is needed because `Meta` is not inherited in the way you
might expect: `abstract` is explicitly reset to `False` for every subclass, so
without redeclaring it here, `BaseModel` would try to create a table.

### `rupees`

```python
def rupees(paise: int) -> str:
    """Display only. Money is stored, compared and summed in paise."""
    return f"{paise / 100:,.2f}"
```

A module-level function, not a model method, because it is a pure conversion.

**`f"{paise / 100:,.2f}"`** — an f-string with a format specification. `,` inserts
thousands separators; `.2f` fixes two decimal places. So `162000` becomes
`"1,620.00"`.

`paise / 100` produces a float, which would be unacceptable in a calculation — but
this value goes straight into a string for a human to read, so the imprecision can
never propagate. The docstring exists to stop somebody reusing it in arithmetic.

### `AuditLog`

```python
class AuditLog(BaseModel):
    """Who did what, to which row (FR-255)."""

    class Action(models.TextChoices):
        CREATE = "create", "Create"
        UPDATE = "update", "Update"
        DELETE = "delete", "Delete"
        LOGIN = "login", "Login"
        PUBLISH = "publish", "Publish"
        REFUND = "refund", "Refund"
```

A nested `TextChoices` enum. Each member is `(stored value, human label)`.
Referenced as `AuditLog.Action.CREATE`, which is a string subclass — so it
compares equal to `"create"` and can be written straight into the database.

```python
    actor = models.ForeignKey(
        settings.AUTH_USER_MODEL, null=True, blank=True,
        on_delete=models.SET_NULL, related_name="audit_entries",
    )
```

**`settings.AUTH_USER_MODEL`** rather than importing `User` — the reference that
works no matter which app defines the user model, and which avoids a circular
import here (`accounts` imports `common`).

**`null=True`** because not every audited action has an actor: a webhook from
Razorpay is nobody.

**`on_delete=models.SET_NULL`** — deleting an administrator must not delete the
record of what they did. That is the whole point of an audit log.

```python
    action = models.CharField(max_length=16, choices=Action.choices)
    target_type = models.CharField(max_length=64)
    target_id = models.CharField(max_length=64, blank=True)
    summary = models.CharField(max_length=255, blank=True)
    changes = models.JSONField(default=dict, blank=True)
    ip_address = models.GenericIPAddressField(null=True, blank=True)
```

**`choices=Action.choices`** — `.choices` renders the enum as the list of pairs
Django wants. This gives validation on `full_clean()` and a
`get_action_display()` method, but note it does *not* create a database
constraint; a raw SQL insert could still write nonsense.

**`target_type` and `target_id` as plain strings** — this is a deliberate refusal
of `GenericForeignKey`. An audit row must survive the deletion of the thing it
describes, so a real foreign key would be actively wrong: it would either block
the delete or cascade away the evidence. Strings hold a tombstone.

**`changes = models.JSONField(default=dict)`** — `dict` the function, not `{}` the
literal. A mutable default shared between instances is a classic Python bug, and
Django raises a system check error if you try it.

**`GenericIPAddressField`** — validates both IPv4 and IPv6 and maps to Postgres's
native `inet` type.

```python
    class Meta:
        ordering = ("-created_at",)
        indexes = [models.Index(fields=["target_type", "target_id"])]
```

**`ordering = ("-created_at",)`** — the minus means descending. A trailing comma
makes it a tuple; without it the parentheses would be redundant grouping and the
value a bare string, which Django would reject.

**The composite index** serves "everything that happened to this object". Column
order matters — this index also helps a query filtered on `target_type` alone, but
not one on `target_id` alone.

```python
    def __str__(self) -> str:
        return f"{self.action} {self.target_type}:{self.target_id}"
```

What the admin, the shell and a failing test will show.

---

## `apps/common/errors.py`

### Imports

```python
from rest_framework import status
from rest_framework.exceptions import APIException
from rest_framework.response import Response
from rest_framework.views import exception_handler as drf_exception_handler
```

**`status`** — named constants, so `status.HTTP_409_CONFLICT` rather than `409`.

**`APIException`** — DRF's base exception. Anything inheriting from it is caught
by DRF and turned into a response rather than a 500.

**`Response`** — DRF's response class, which holds unrendered data and negotiates
the content type. Not Django's `HttpResponse`, which expects bytes.

**`exception_handler as drf_exception_handler`** — aliased on import, because this
module defines a function of the same name. Without the alias the second
definition would shadow the first and the delegation below would recurse forever.

### `DomainError`

```python
class DomainError(APIException):
    """Base for anything that should surface as a typed 4xx, never a 500."""

    status_code = status.HTTP_400_BAD_REQUEST
    default_code = "bad_request"
    default_detail = "The request could not be completed."

    def __init__(self, message: str | None = None, *, fields: dict | None = None, **extra):
        super().__init__(message or self.default_detail)
        self.fields = fields or {}
        self.extra = extra
```

**The three class attributes** are DRF's protocol. Subclasses override whichever
they need, and everything else is inherited.

**`def __init__(self, message=None, *, fields=None, **extra)`** — the `*` makes
everything after it keyword-only, so `CapacityUnavailableError("...", {"a": 1})`
is a `TypeError` rather than a silent mistake. That matters because a positional
dictionary would otherwise be swallowed.

**`super().__init__(message or self.default_detail)`** — `or` supplies the class
default when the caller passes nothing. DRF stores the result on `self.detail`.

**`self.fields = fields or {}`** — per-field messages, for the `fields` key of the
envelope. `or {}` normalises `None` to an empty dict so callers never have to test
for it.

**`self.extra = extra`** — everything else the caller passed by keyword, collected
into a dict. This is what makes

```python
raise CapacityUnavailableError("Only 2 places remain.", available=2)
```

work, and the `available: 2` then rides out in the JSON so the client can offer
the next day instead of a dead end.

### The three subclasses

```python
class ValidationFailedError(DomainError):
    status_code = status.HTTP_422_UNPROCESSABLE_ENTITY
    default_code = "validation_failed"


class CapacityUnavailableError(DomainError):
    status_code = status.HTTP_409_CONFLICT
    default_code = "capacity_unavailable"
    default_detail = "There are not enough places left."


class HoldExpiredError(DomainError):
    status_code = status.HTTP_409_CONFLICT
    default_code = "hold_expired"
    default_detail = "That reservation has expired."
```

Each is three lines because the base does the work.

**422 versus 400** — 400 means the request was malformed; 422 means it parsed
fine but the contents are unacceptable. A phone number of `"12"` is well-formed
JSON containing a bad value, so 422.

**409 Conflict** for both capacity cases — the request was valid and would have
been fine a moment earlier. It says "try something else", not "you made a
mistake", and the two distinct codes let a client tell "sold out" from "your
reservation lapsed" without reading English.

**Why exceptions at all**, rather than returning an error response? Because
`place_hold` lives three calls deep in a service module and knows nothing about
HTTP. Raising lets the domain speak in domain terms and the edge translate.

### The handler

```python
def exception_handler(exc, context):
    response = drf_exception_handler(exc, context)
    if response is None:
        return None
```

DRF calls this for every exception raised in a view. `context` carries the view
and the request.

**Delegate first.** DRF's own handler returns `None` for anything it does not
recognise — a `ZeroDivisionError`, say. Returning `None` in turn re-raises, so
Django produces a real 500 and the error reaches Sentry. That is correct:
unexpected exceptions must not be dressed up as tidy 4xx responses.

```python
    if isinstance(exc, DomainError):
        body = {"code": exc.default_code, "message": str(exc.detail)}
        if exc.fields:
            body["fields"] = exc.fields
        body.update(exc.extra)
        return Response({"error": body}, status=exc.status_code)
```

Our own exceptions, rendered into the envelope.

**`str(exc.detail)`** — DRF wraps detail strings in `ErrorDetail`, a `str`
subclass that also carries a code. `str()` unwraps it so the JSON is a plain
string.

**`if exc.fields:`** — omit the key entirely when empty, rather than sending
`"fields": {}`. Less noise for the client to check.

**`body.update(exc.extra)`** — merges `available=2` and friends in at the top
level of the error object.

```python
    detail = response.data
    if isinstance(detail, dict) and "detail" not in detail:
        # DRF field errors: {"phone": ["..."]}
        return Response(
            {"error": {"code": "validation_failed",
                       "message": "Some fields need attention.",
                       "fields": {k: v[0] if isinstance(v, list) else v
                                  for k, v in detail.items()}}},
            status=response.status_code,
        )
```

Serialiser validation errors arrive as `{"phone": ["Enter a valid number."]}` — a
dict of field names to *lists* of messages, and no `detail` key. That shape is
detected and reshaped into the same envelope.

**`v[0] if isinstance(v, list) else v`** — take the first message. Showing one
error per field is what a form needs; the rest are usually restatements.

```python
    code = getattr(exc, "default_code", "error")
    message = detail.get("detail") if isinstance(detail, dict) else str(detail)
    return Response({"error": {"code": code, "message": str(message)}},
                    status=response.status_code)
```

The fallback, for DRF's built-ins — `NotAuthenticated`, `PermissionDenied`,
`Throttled`, `NotFound`.

**`getattr(exc, "default_code", "error")`** — most DRF exceptions define
`default_code` (`"not_authenticated"`, `"permission_denied"`), which is exactly
the machine-readable string we want. The third argument is the fallback for any
that do not.

The net effect: **every error response in the system has the same shape**, whether
it came from our code, from a serialiser, or from DRF itself.

---

## `apps/common/pagination.py`

```python
from rest_framework.pagination import PageNumberPagination


class DefaultPagination(PageNumberPagination):
    page_size = 25
    page_size_query_param = "page_size"
    max_page_size = 200
```

**`PageNumberPagination`** — `?page=2`. DRF also offers `LimitOffsetPagination`
(`?limit=&offset=`) and `CursorPagination`. Page numbers are the right default for
admin tables, where a person wants to jump to page five. Cursor pagination is the
right choice for a live feed, where new rows arriving would otherwise shuffle
items between pages — the scan log will want it later.

**`page_size = 25`** — the default when the client asks for nothing.

**`page_size_query_param = "page_size"`** — enabling this lets a client ask for a
different size. It is `None` by default, which locks everyone to 25; an export
screen legitimately wants more.

**`max_page_size = 200`** — and this is why the previous line is safe.
`?page_size=1000000` is clamped to 200. Without the cap, an open pagination
parameter is a one-line denial of service.

---

## `apps/common/views.py`

```python
import logging

from django.conf import settings
from django.db import connection
from django.http import JsonResponse
from django.views.decorators.http import require_GET
from redis import Redis
from redis.exceptions import RedisError

logger = logging.getLogger(__name__)
```

**`logger = logging.getLogger(__name__)`** — the standard incantation. `__name__`
is `"apps.common.views"`, so the logger's name reflects where it lives and logging
can be configured per module.

**`from django.db import connection`** — the default database connection, used
below to issue raw SQL.

**`JsonResponse`** rather than DRF's `Response`, because a health check must not
depend on content negotiation, authentication or any DRF machinery. The fewer
moving parts, the more it means when it says "ok".

```python
@require_GET
def health(request):
    """Liveness plus its two hard dependencies."""
    checks = {"database": False, "redis": False}
```

**`@require_GET`** — returns 405 for any other method. A health endpoint has no
business accepting a POST.

**Defaults are `False`** — the checks must actively prove themselves. Starting
from `True` and setting `False` on failure would report healthy if a check were
accidentally skipped.

```python
    try:
        with connection.cursor() as cur:
            cur.execute("SELECT 1")
            checks["database"] = cur.fetchone() == (1,)
    except Exception:  # a health check must never raise
        logger.exception("health: database check failed")
```

**`SELECT 1`** — the cheapest possible round trip. It proves the connection is
open and the server is answering, without reading a table.

**`cur.fetchone() == (1,)`** — a tuple with one element. Checking the returned
value, not merely that `execute` did not raise, catches a connection that accepts
queries but is returning nonsense.

**`except Exception`** — deliberately broad, and commented. Normally catching bare
`Exception` is a smell; here it is the requirement. A health check that raises
turns into a 500 with no body, and the load balancer learns nothing about *which*
dependency failed. `logger.exception` records the traceback while the response
still reports a structured result.

```python
    try:
        checks["redis"] = bool(Redis.from_url(settings.REDIS_URL).ping())
    except (RedisError, OSError):
        logger.exception("health: redis check failed")
```

**A narrower `except` here**, because the failure modes are known: `RedisError`
for anything the client raises, `OSError` for a refused connection or DNS failure.

**`Redis.from_url(...)`** builds a fresh client rather than using Django's cache
wrapper — again, checking the dependency itself rather than a layer over it.

```python
    ok = all(checks.values())
    return JsonResponse({"status": "ok" if ok else "degraded", **checks},
                        status=200 if ok else 503)
```

**`all(checks.values())`** — true only if both passed.

**`{**checks}`** — dictionary unpacking, so the response is
`{"status": "ok", "database": true, "redis": true}` rather than nesting them. A
human reading a failing check sees immediately which dependency is down.

**`status=200 if ok else 503`** — the status code is what a load balancer or
Kubernetes probe reads; the body is for the human who then goes looking. 503
Service Unavailable is the right code: the application is running but cannot
serve.
