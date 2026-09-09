# Part 3 · Geography and accounts

Two apps. `geo` is small and shows relationships at their simplest. `accounts`
is the largest file in the project and holds the custom user model, the admin
roles, and the one-time-code machinery.

---

## `apps/geo/models.py`

Three models, one chain: a state has cities, a city has localities.

```python
class State(BaseModel):
    name = models.CharField(max_length=80, unique=True)
    code = models.CharField(max_length=4, unique=True)

    class Meta:
        ordering = ("name",)

    def __str__(self) -> str:
        return self.name
```

**`unique=True` on both fields** creates a unique index each. Two states cannot
share a name, and two cannot share a code. `max_length=4` because Indian state
codes are two letters — the extra room is free and costs nothing to have.

**`ordering = ("name",)`** so any dropdown of states is alphabetical without the
caller asking.

```python
class City(BaseModel):
    state = models.ForeignKey(State, on_delete=models.PROTECT, related_name="cities")
    name = models.CharField(max_length=80)

    class Meta:
        ordering = ("name",)
        verbose_name_plural = "cities"
        constraints = [models.UniqueConstraint(fields=["state", "name"], name="uniq_city_in_state")]
```

**`ForeignKey(State, ...)`** — the class directly, not the string `"geo.State"`,
because `State` is defined above in the same file. Both forms work; the string is
only needed to break an import cycle.

**`on_delete=models.PROTECT`** — deleting a state that still has cities raises
rather than quietly removing them.

**`related_name="cities"`** — so `state.cities.all()` rather than
`state.city_set.all()`.

**`name` is not `unique=True`** on its own, and that is the point of the next
line. There is a Kolkata in West Bengal; there could be a Hyderabad in two
states.

**`UniqueConstraint(fields=["state", "name"])`** — unique *in combination*. Two
cities may share a name as long as they are in different states. This is the
common shape for "unique within a parent".

**`verbose_name_plural = "cities"`** — Django pluralises by appending `s`, giving
"citys" in the admin. English needs help here.

```python
class Locality(BaseModel):
    """'South Kolkata', 'Ballygunge' — how pandals are grouped and found."""

    city = models.ForeignKey(City, on_delete=models.CASCADE, related_name="localities")
    name = models.CharField(max_length=80)
```

**`on_delete=models.CASCADE`** here, where `City` used `PROTECT`. The reasoning
differs by level: a city is reference data that other things point at, so deleting
one should be hard. A locality is a subdivision of its city and is meaningless
without it, so it can go with it.

```python
    def __str__(self) -> str:
        return f"{self.name}, {self.city.name}"
```

Note `self.city.name` — reading `.city` triggers a query if the city was not
already loaded. In an admin dropdown of 200 localities that is 200 queries. It is
acceptable here because the lists are short; on a bigger table this is exactly
where you would reach for `select_related`.

---

## `apps/accounts/models.py`

### Imports

```python
import hashlib
import hmac

from django.conf import settings
from django.contrib.auth.base_user import AbstractBaseUser, BaseUserManager
from django.contrib.auth.models import PermissionsMixin
from django.db import models
from django.utils import timezone

from apps.common.models import BaseModel
```

**`hashlib`** provides the hash algorithms; **`hmac`** wraps one with a secret key
and provides a constant-time comparison. Both are used to store one-time codes.

**`AbstractBaseUser`** — the minimal user: a password, a `last_login`, and the
methods Django's auth system calls.

**`BaseUserManager`** — a manager with `normalize_email` and the contract that
`createsuperuser` expects.

**`PermissionsMixin`** — adds `is_superuser`, `groups`, `user_permissions` and the
`has_perm` family. Needed by the Django admin.

**`from django.utils import timezone`** — not `datetime`. With `USE_TZ = True`,
`timezone.now()` returns an *aware* datetime in UTC. `datetime.now()` returns a
naive one, and mixing the two raises `TypeError` when you subtract them. Use
`timezone.now()` everywhere.

### `ProfileType`

```python
class ProfileType(BaseModel):
    name = models.CharField(max_length=60, unique=True)
    slug = models.SlugField(max_length=60, unique=True)
    description = models.CharField(max_length=255, blank=True)
    is_active = models.BooleanField(default=True)
    sort_order = models.PositiveSmallIntegerField(default=0)

    class Meta:
        ordering = ("sort_order", "name")
```

The five categories — Senior Citizens, Press and so on — as **rows rather than
choices**. A `TextChoices` enum would need a migration and a deployment to add a
sixth; a table needs an insert.

**`slug`** is the stable machine name. The label can be reworded — "Senior
Citizens" to "Senior Citizen" — without breaking any client that stored the slug.

**`is_active`** rather than deleting. Retiring a category must not orphan the
visitors already tagged with it.

**`sort_order`** with `PositiveSmallIntegerField` — a two-byte integer, 0 to
32767. Plenty, and smaller than the default four-byte `IntegerField`.

**`ordering = ("sort_order", "name")`** — two keys: primary by explicit order,
then alphabetically among ties. Without the second key, rows sharing a
`sort_order` come back in whatever order Postgres feels like, which changes
between runs.

### `UserManager`

```python
class UserManager(BaseUserManager):
    use_in_migrations = True

    def create_user(self, phone: str, password: str | None = None, **extra):
        if not phone:
            raise ValueError("A phone number is required.")
        extra["email"] = self.normalize_email(extra.get("email", "")) or ""
        user = self.model(phone=phone, **extra)
        if password:
            user.set_password(password)
        else:
            user.set_unusable_password()
        user.save(using=self._db)
        return user
```

**`use_in_migrations = True`** lets a data migration call this manager. Without
it, Django refuses to serialise the manager into a migration file.

**`if not phone: raise ValueError`** — a `ValueError`, not a Django
`ValidationError`, because this is a programming error rather than bad user input.
By the time you are calling `create_user` the input should already have been
validated.

**`self.normalize_email(...)`** lowercases the domain part of an address —
`A@Example.COM` becomes `A@example.com` — because domains are case-insensitive and
local parts technically are not.

**`extra.get("email", "") or ""`** — the trailing `or ""` converts `None` to `""`.
Necessary because `email` is `null=False` on the model, and passing `None` would be
an `IntegrityError` rather than an empty string.

**`self.model(phone=phone, **extra)`** — `self.model` is the class the manager is
attached to. Written this way rather than `User(...)` so the manager keeps working
if the model is subclassed.

**`set_password` versus `set_unusable_password`** — the first hashes and stores.
The second writes a marker no hash can ever match, which is how an OTP-only
account can exist: it is real, it can sign in by code, and no password will ever
work for it.

**`user.save(using=self._db)`** — respects database routing. A single-database
project does not need it, and it costs nothing to be correct.

```python
    def create_superuser(self, phone: str, password: str, **extra):
        extra.setdefault("is_staff", True)
        extra.setdefault("is_superuser", True)
        extra.setdefault("is_active", True)
        return self.create_user(phone, password, **extra)
```

**`setdefault`** rather than assignment, so an explicit `is_staff=False` from a
caller is respected. `password` is required here, unlike in `create_user`.

### `User`

```python
class User(AbstractBaseUser, PermissionsMixin, BaseModel):
```

Three parents. Python resolves attributes left to right, so `AbstractBaseUser`
wins any collision. `BaseModel` is last and contributes the UUID primary key and
the timestamps.

```python
    class Gender(models.TextChoices):
        FEMALE = "female", "Female"
        MALE = "male", "Male"
        OTHER = "other", "Other"
        UNDISCLOSED = "undisclosed", "Prefer not to say"
```

An explicit "prefer not to say" rather than leaving the field blank, because blank
means "we never asked" and this means "they chose not to answer". Those are
different facts.

```python
    phone = models.CharField(max_length=20, unique=True,
                             help_text="E.164, e.g. +919876543210")
```

**`unique=True`** is what makes it usable as the login identifier.

**`max_length=20`** — E.164 allows at most fifteen digits plus a `+`; twenty
leaves room.

**Not `PhoneNumberField`** from a third-party package. A plain `CharField` plus
one normalisation function keeps the dependency count down, and the rule is
enforced at the one place numbers enter the system.

```python
    first_name = models.CharField(max_length=60, blank=True)
    last_name = models.CharField(max_length=60, blank=True)
    email = models.EmailField(blank=True)
    date_of_birth = models.DateField(null=True, blank=True)
```

All `blank=True`, because sign-up captures only the phone number and the profile
is filled in afterwards. `date_of_birth` also takes `null=True` — there is no
empty-string equivalent for a date, so a missing one genuinely has to be `NULL`.

**`EmailField`** is a `CharField` with an email validator attached and a default
`max_length` of 254, which is the RFC limit.

```python
    state = models.ForeignKey("geo.State", null=True, blank=True,
                              on_delete=models.SET_NULL, related_name="+")
    city = models.ForeignKey("geo.City", null=True, blank=True,
                             on_delete=models.SET_NULL, related_name="+")
```

**`related_name="+"`** on both — no reverse accessor is created. Without it you
would get `state.user_set`, which nobody wants, and it would collide with the
reverse from `Pandal.city`.

**`SET_NULL`** — if reference data is reorganised, a user's row survives with the
field cleared. Losing a user because a city was renamed would be absurd.

```python
    profile_types = models.ManyToManyField(ProfileType, blank=True, related_name="users")
```

Many-to-many because a visitor can be both Press and a Senior Citizen, and each
category applies to many visitors. Django creates the join table
`accounts_user_profile_types` behind this, holding `user_id` and `profiletype_id`
with a unique constraint on the pair.

**`blank=True`** on a many-to-many affects forms only. There is no `null=True`
here — an empty relation is simply zero rows in the join table, so the concept
does not apply, and Django warns if you try.

```python
    preferred_language = models.CharField(max_length=5, choices=settings.LANGUAGES, default="en")
    phone_verified_at = models.DateTimeField(null=True, blank=True)
```

**`choices=settings.LANGUAGES`** reuses the setting, so the supported languages
are declared once.

**`phone_verified_at` as a timestamp, not a boolean.** A nullable datetime answers
both "is it verified?" (is it null?) and "when?" — and the second question always
gets asked eventually. This pattern repeats throughout the project:
`consumed_at`, `resolved_at`, `captured_at`, `released_at`.

```python
    is_active = models.BooleanField(default=True)
    is_staff = models.BooleanField(default=False)
    date_joined = models.DateTimeField(default=timezone.now)
```

**`is_active`** is checked by Django's authentication backend: a user with it set
to `False` cannot log in. It is the correct way to suspend an account, because
deleting one would cascade through their donations.

**`is_staff`** controls access to `/admin/` only. It is unrelated to the
`AdminMembership` roles below, which govern the API.

**`default=timezone.now`** — the function, not `timezone.now()`. Calling it would
freeze the value at import time and stamp every user with the moment the server
booted.

```python
    objects = UserManager()

    USERNAME_FIELD = "phone"
    REQUIRED_FIELDS: list[str] = []
```

**`objects = UserManager()`** — replaces the default manager, which is what makes
`User.objects.create_user(...)` work.

**`REQUIRED_FIELDS`** is what `createsuperuser` prompts for *in addition to* the
username field and password. The annotation `: list[str]` is there because an
empty list gives a type checker nothing to infer from.

```python
    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["email"], condition=~models.Q(email=""),
                name="uniq_user_email_when_present",
            )
        ]
```

A **partial unique index**. Email is optional, so many users have `""`; a plain
`unique=True` would permit exactly one of them. `condition=~models.Q(email="")`
applies the index only where the email is non-empty. `~` negates a `Q` object,
which is how conditions more complex than a keyword argument get expressed.

```python
    @property
    def full_name(self) -> str:
        return f"{self.first_name} {self.last_name}".strip()
```

**`.strip()`** handles the case where only one of the two is set, which would
otherwise leave a leading or trailing space.

```python
    @property
    def profile_completeness(self) -> int:
        filled = sum(bool(v) for v in (
            self.first_name, self.last_name, self.email,
            self.date_of_birth, self.gender, self.city_id,
        ))
        return round(filled / 6 * 100)
```

**`sum(bool(v) for v in (...))`** — `bool` is `True` or `False`, and Python sums
them as 1 and 0. A compact way to count truthy values.

**`self.city_id`, not `self.city`** — the raw column, so no query is issued. Using
`self.city` here would mean a database round trip every time a profile is
serialised, purely to compute a percentage.

### `Role` and `AdminMembership`

```python
class Role(models.TextChoices):
    SUPER_ADMIN = "super_admin", "Super Admin"
    PANDAL_ADMIN = "pandal_admin", "Pandal Admin"
```

Module-level rather than nested, because two models use it — `AdminMembership` and
`StaffInvitation`. Only two roles in v1; sponsor and sub-sponsor arrive with
passes.

```python
class AdminMembership(BaseModel):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="memberships")
    role = models.CharField(max_length=24, choices=Role.choices)
    pandal = models.ForeignKey("pandals.Pandal", null=True, blank=True,
                               on_delete=models.CASCADE, related_name="memberships")
    is_active = models.BooleanField(default=True)
```

**`user` cascades** — a deleted user's grants are meaningless.

**`pandal` is nullable**, and that nullability carries meaning: a row with a
pandal is scoped to it; a row without one is platform-wide. A Super Admin has
`pandal = NULL`.

**`"pandals.Pandal"` as a string** — a real import would be circular, since
`pandals` models reference `settings.AUTH_USER_MODEL`.

```python
    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["user", "role", "pandal"], name="uniq_membership_scope")
        ]
```

One grant of one role at one scope. Note the subtlety: in Postgres, `NULL` is not
equal to `NULL`, so this constraint does **not** prevent two platform-wide
super-admin rows for the same user. Enforcing that needs a second partial
constraint with `condition=Q(pandal__isnull=True)`. Worth knowing before it
surprises you.

### `StaffInvitation`

```python
    token_hash = models.CharField(max_length=64, db_index=True)
    expires_at = models.DateTimeField()
    accepted_at = models.DateTimeField(null=True, blank=True)
```

**`token_hash`, never the token.** The raw token goes out once in a link and is
never stored, so a database leak yields no usable invitations. 64 characters
because SHA-256 in hex is exactly 64.

**`db_index=True`** because the lookup is by hash — the incoming link is hashed
and matched.

```python
    @staticmethod
    def hash_token(raw: str) -> str:
        return hmac.new(settings.SECRET_KEY.encode(), raw.encode(), hashlib.sha256).hexdigest()
```

**`@staticmethod`** — no `self`, because hashing needs no instance. It lives on
the class so the algorithm sits next to the field it fills.

**HMAC rather than a plain hash.** A bare `sha256(token)` could be attacked with a
precomputed table; keying it with `SECRET_KEY` means an attacker with the database
but not the key can do nothing with it.

**`.encode()`** turns `str` into `bytes`, which is what the hashing functions
take.

```python
    @property
    def is_usable(self) -> bool:
        return self.accepted_at is None and self.expires_at > timezone.now()
```

Both conditions: not already used, and not expired. `is None` rather than `not
self.accepted_at`, because a datetime is always truthy and the distinction that
matters is null-versus-set.

### `OtpChallenge`

```python
    class Purpose(models.TextChoices):
        LOGIN = "login", "Login or sign-up"
        WEB_CHECKOUT = "web_checkout", "Web checkout"
        ADMIN_LOGIN = "admin_login", "Admin login"
```

Purpose is part of the identity of a challenge. A code issued for a web checkout
must not authenticate an admin session, and the lookup in `verify()` filters on it
— there is a test for exactly this.

```python
    code_hash = models.CharField(max_length=64)
    expires_at = models.DateTimeField()
    attempts = models.PositiveSmallIntegerField(default=0)
    max_attempts = models.PositiveSmallIntegerField(default=5)
    consumed_at = models.DateTimeField(null=True, blank=True)
    request_ip = models.GenericIPAddressField(null=True, blank=True)
```

**`max_attempts` stored per row**, not read from settings at check time. So
changing the setting does not retroactively grant more attempts to codes already
in flight.

**`request_ip`** for abuse investigation — spotting one address requesting codes
for hundreds of numbers.

```python
    @staticmethod
    def hash_code(code: str, destination: str) -> str:
        return hmac.new(settings.SECRET_KEY.encode(),
                        f"{destination}:{code}".encode(), hashlib.sha256).hexdigest()
```

**The destination is mixed in**, so a hash computed for one number cannot be
replayed against another. The `:` separator prevents ambiguity — without it,
`("12", "3456")` and `("123", "456")` would hash identically.

```python
    @property
    def is_live(self) -> bool:
        return (self.consumed_at is None
                and self.attempts < self.max_attempts
                and self.expires_at > timezone.now())

    def verify(self, code: str) -> bool:
        return hmac.compare_digest(self.code_hash, self.hash_code(code, self.destination))
```

**Three ways a challenge dies**: spent, exhausted, expired. All checked before the
code is even compared.

**`hmac.compare_digest`** compares in constant time. A normal `==` on strings
returns as soon as two characters differ, and that timing difference is measurable
over enough attempts. It costs nothing to use the safe comparison.

---

## `apps/accounts/phone.py`

```python
import phonenumbers
from django.conf import settings

from apps.common.errors import ValidationFailedError


def normalise(raw: str) -> str:
    """Everything downstream stores and compares E.164 only (FR-016)."""
    try:
        parsed = phonenumbers.parse(raw, settings.DEFAULT_PHONE_REGION)
    except phonenumbers.NumberParseException as exc:
        raise ValidationFailedError("That does not look like a phone number.",
                                    fields={"phone": "Enter a valid mobile number."}) from exc
    if not phonenumbers.is_valid_number(parsed):
        raise ValidationFailedError("That does not look like a phone number.",
                                    fields={"phone": "Enter a valid mobile number."})
    return phonenumbers.format_number(parsed, phonenumbers.PhoneNumberFormat.E164)
```

**`phonenumbers`** is the Python port of Google's libphonenumber, which knows the
numbering plan of every country — including which prefixes are actually assigned.

**`phonenumbers.parse(raw, "IN")`** — the region tells it how to read a number
with no country code, so `9876543210` becomes `+91 98765 43210`.

**Two separate checks.** `parse` raises when the input is not number-shaped at
all; `is_valid_number` catches strings that parse but are not real numbers, such
as `+91 1234567890`. Both are needed.

**`raise ... from exc`** sets `__cause__`, so the traceback shows the original
parse error underneath ours. Losing that makes debugging harder for no gain.

**`format_number(..., E164)`** produces the single canonical form —
`+919876543210`, no spaces, no dashes. Because every number is normalised on the
way in, the same person typing `98765 43210` on the web and `+91 9876543210` in
the app reaches one account.

---

## `apps/accounts/otp/senders.py`

```python
class OtpSender(Protocol):
    def send(self, destination: str, code: str, *, channel: str) -> None: ...
```

**`Protocol`** is structural typing: any class with a matching `send` method
satisfies it, with no inheritance required. This is the Python equivalent of a
Go interface, and it means a future `Msg91Sender` need not import anything from
here.

The `...` body is the convention for a stub.

```python
class ConsoleSender:
    def send(self, destination: str, code: str, *, channel: str) -> None:
        logger.info("OTP for %s via %s: %s", destination, channel, code)
```

**`logger.info("...%s...", a, b)`** with `%s` placeholders and separate arguments,
not an f-string. The formatting is then deferred until the message is actually
emitted — if the log level is above INFO, the interpolation never happens.

```python
class MemorySender:
    sent: dict[str, str] = {}

    def send(self, destination: str, code: str, *, channel: str) -> None:
        type(self).sent[destination] = code

    @classmethod
    def last_code(cls, destination: str) -> str | None:
        return cls.sent.get(destination)

    @classmethod
    def reset(cls) -> None:
        cls.sent.clear()
```

**`sent` is a class attribute**, shared by every instance. That is deliberate: the
service constructs a fresh sender on each call, so per-instance state would be
lost immediately.

**`type(self).sent[...]`** rather than `self.sent[...]`. Assigning through
`self` would create an *instance* attribute shadowing the class one; going through
the class writes where `last_code` reads.

**`reset()`** exists because this dictionary lives outside the database, so the
test transaction rollback does not clear it. The `autouse` fixture calls it.

---

## `apps/accounts/otp/service.py`

The exception classes first:

```python
class OtpRateLimitedError(DomainError):
    status_code = status.HTTP_429_TOO_MANY_REQUESTS
    default_code = "otp_rate_limited"
    default_detail = "Please wait before requesting another code."
```

429 Too Many Requests, with the code the API contract promises. Three of these,
one per failure mode.

```python
@dataclass(frozen=True)
class IssuedOtp:
    challenge: OtpChallenge
    resend_after_seconds: int
```

**`@dataclass`** generates `__init__`, `__repr__` and `__eq__` from the
annotations. **`frozen=True`** makes it immutable, which is right for a return
value nobody should be editing.

Returning a small object rather than a tuple means callers write
`issued.resend_after_seconds` instead of `issued[1]`.

```python
def _sender():
    return import_string(settings.OTP_SENDER_BACKEND)()
```

**`import_string`** turns `"apps.accounts.otp.senders.ConsoleSender"` into the
class. The trailing `()` instantiates it. Resolved on every call, not at import,
so the test settings can swap it.

**The leading underscore** marks it private by convention.

```python
def _cooldown_key(destination: str) -> str:
    return f"otp:cooldown:{destination}"
```

Cache keys built by a function rather than inline, so the format is defined once
and the tests can construct the same key to clear it. The `otp:` prefix namespaces
them within a shared Redis.

### `issue`

```python
def issue(destination: str, *, purpose: str = OtpChallenge.Purpose.LOGIN,
          channel: str = OtpChallenge.Channel.SMS, ip: str | None = None) -> IssuedOtp:
```

**`*`** makes everything after it keyword-only, so a call site cannot silently
pass a purpose where a channel was meant.

```python
    if cache.get(_cooldown_key(destination)):
        raise OtpRateLimitedError(retry_after=settings.OTP_RESEND_COOLDOWN_SECONDS)

    sent_this_hour = cache.get_or_set(_hourly_key(destination), 0, timeout=3600)
    if sent_this_hour >= settings.OTP_MAX_SENDS_PER_HOUR:
        raise OtpRateLimitedError("Too many codes requested. Try again later.", retry_after=3600)
```

**Two independent limits.** The cooldown stops rapid re-sends; the hourly cap
stops slow grinding. Both live in the cache rather than the database, because they
are ephemeral and this path runs on every sign-in attempt.

**`cache.get_or_set(key, 0, timeout=3600)`** reads the counter, initialising it to
zero with a one-hour lifetime if absent. The window is therefore a rolling hour
from the first request.

**`retry_after=...`** rides out in the error envelope through `DomainError.extra`,
so the client can display a countdown instead of guessing.

```python
    OtpChallenge.objects.filter(
        destination=destination, purpose=purpose, consumed_at__isnull=True
    ).update(consumed_at=timezone.now())
```

**The line that guarantees one live code at a time.** Every unconsumed challenge
for this destination and purpose is marked consumed before a new one is created.

**`.update()` rather than looping and saving** — one SQL statement, and no race
with a concurrent request.

**`consumed_at__isnull=True`** — the double-underscore lookup for `IS NULL`.

```python
    code = f"{secrets.randbelow(10 ** settings.OTP_CODE_LENGTH):0{settings.OTP_CODE_LENGTH}d}"
```

Dense, so unpacking it:

- **`10 ** 6`** is 1,000,000.
- **`secrets.randbelow(1000000)`** gives 0 to 999,999 from a cryptographically
  secure source. Not `random.randint`, which is predictable from previous outputs.
- **`:06d`** formats as a decimal padded to six digits, so `42` becomes `"000042"`.
  Without the padding, one code in ten would be short and leak information about
  itself.
- The format spec is itself built from the setting, hence the nested braces.

```python
    challenge = OtpChallenge.objects.create(
        channel=channel,
        destination=destination,
        purpose=purpose,
        code_hash=OtpChallenge.hash_code(code, destination),
        expires_at=timezone.now() + timedelta(seconds=settings.OTP_TTL_SECONDS),
        max_attempts=settings.OTP_MAX_ATTEMPTS,
        request_ip=ip,
    )

    _sender().send(destination, code, channel=channel)
```

**The hash is stored; the code is not.** The plaintext exists only in this local
variable and in the message that goes out.

**Sending happens after the row is created.** The other order would risk an SMS
going out for a challenge that failed to save.

```python
    cache.set(_cooldown_key(destination), 1, timeout=settings.OTP_RESEND_COOLDOWN_SECONDS)
    try:
        cache.incr(_hourly_key(destination))
    except ValueError:
        cache.set(_hourly_key(destination), 1, timeout=3600)
```

**The cooldown key's value is irrelevant** — only its existence matters, and it
expires on its own.

**`cache.incr`** is atomic in Redis, so concurrent requests cannot both read 3 and
both write 4. It raises `ValueError` if the key vanished between the `get_or_set`
above and here, which the fallback handles.

### `verify`

```python
def verify(destination: str, code: str,
           *, purpose: str = OtpChallenge.Purpose.LOGIN) -> OtpChallenge:
    challenge = (OtpChallenge.objects
                 .filter(destination=destination, purpose=purpose)
                 .order_by("-created_at").first())
    if challenge is None or not challenge.is_live:
        raise OtpExpiredError
```

**Only the newest challenge is consulted.** A superseded code therefore fails as
`otp_invalid` rather than `otp_expired` — indistinguishable from a typo, which is
the safe way round, and there is a test asserting it.

**`.first()`** returns `None` rather than raising when there is nothing, unlike
`.get()`.

**`raise OtpExpiredError`** — the class, not an instance. Python instantiates it
for you.

```python
    if not challenge.verify(code):
        OtpChallenge.objects.filter(pk=challenge.pk).update(attempts=F("attempts") + 1)
        challenge.refresh_from_db(fields=["attempts"])
        raise OtpInvalidError(attempts_left=max(0, challenge.max_attempts - challenge.attempts))
```

**`F("attempts") + 1`** increments in the database, so two simultaneous wrong
guesses both count. Reading into Python and adding one would lose an increment.

**`refresh_from_db(fields=["attempts"])`** — after an `F()` update the in-memory
object is stale, and reading `challenge.attempts` would give the old value. Naming
the field re-reads one column rather than the whole row.

**`max(0, ...)`** guards against a negative count if attempts somehow exceeded the
maximum.

```python
    challenge.consumed_at = timezone.now()
    challenge.save(update_fields=["consumed_at", "updated_at"])
    return challenge
```

**`update_fields=[...]`** writes only those columns instead of all of them.
Narrower `UPDATE`, less to conflict with a concurrent write. `updated_at` must be
listed explicitly — `auto_now` only fires for fields included in the update.

**Consumed on success**, which is what makes a code single-use.
