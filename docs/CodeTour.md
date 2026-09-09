# A tour of the code, for someone learning Django

Written to be read beside the source. It does not narrate every `import`; it
walks every **decision**, and along the way explains the Django concept that made
the decision available. Where two reasonable options existed, both are named and
the choice is argued.

---

## 1 · How the project is laid out

```
backend/
  manage.py            the command-line entry point
  config/              project-level wiring: settings, urls, celery, wsgi
    settings/
      base.py          everything shared
      dev.py           overrides for a laptop
      test.py          overrides for the test run
  apps/                the actual domain, one folder per area
    common/  geo/  accounts/  pandals/  inventory/
    orders/  payments/  donations/  services/  ops/
  tests/               the test suite
```

**Django calls the outer thing a *project* and the inner things *apps*.** An app
is a Python package Django knows about, listed in `INSTALLED_APPS`. That listing
is what makes Django look inside it for models, migrations, admin registrations
and management commands.

The default `django-admin startproject` puts apps at the top level. Nesting them
under `apps/` is a convention, not a rule; it keeps the repository root readable
once there are ten of them. It costs one thing: every app must be referred to as
`apps.pandals`, which is why `INSTALLED_APPS` reads:

```python
    "apps.common",
    "apps.geo",
    "apps.accounts",
```

Django derives an app's **label** from the last segment — `pandals`, `accounts` —
and that label is what appears in table names (`pandals_pandal`) and in string
model references (`"geo.City"`).

### Why settings are split

`settings/base.py` holds everything true everywhere. `dev.py` and `test.py` each
start with:

```python
from .base import *  # noqa: F403
```

and then override. The alternative is one `settings.py` full of `if DEBUG:`
branches, which reads fine at fifty lines and becomes unnavigable at three
hundred. `# noqa: F403` tells the linter that a star-import is deliberate here,
because this is the one place it is the right tool.

Nothing secret is in any of them:

```python
env = environ.Env(DEBUG=(bool, False), ALLOWED_HOSTS=(list, []))
environ.Env.read_env(BASE_DIR / ".env")

SECRET_KEY = env("DJANGO_SECRET_KEY", default="insecure-dev-key-do-not-use-in-prod")
```

`django-environ` reads a `.env` file in development and plain environment
variables in production, so the same code works in both. The obviously-fake
default is deliberate: if it ever reaches production, it is recognisable in a
stack trace rather than looking like a real key.

---

## 2 · Models are tables

A Django model class is a database table. Each class attribute that is a `Field`
is a column. Django writes the SQL; you describe the shape.

```python
class State(BaseModel):
    name = models.CharField(max_length=80, unique=True)
    code = models.CharField(max_length=4, unique=True)
```

That becomes a table `geo_state` with columns `name` and `code`, both with unique
indexes. `max_length` is required on `CharField` because it becomes
`VARCHAR(80)`.

**`CharField` versus `TextField`.** `CharField` has a length limit; `TextField`
does not. In Postgres the performance is identical, so the limit is a *validation*
decision, not a storage one. `name` is capped because a state name longer than 80
characters is a bug; `address` is a `TextField` because a real address might run
long and truncating it helps nobody.

### `blank` and `null` — the confusion everyone has once

They look like the same idea. They are not.

- **`null=True`** is about the *database*: this column may hold `NULL`.
- **`blank=True`** is about *validation*: forms and serialisers may leave it empty.

```python
committee_name = models.CharField(max_length=180, blank=True)
locality = models.ForeignKey("geo.Locality", null=True, blank=True, ...)
```

`committee_name` is `blank=True` but **not** `null=True`. A missing string is
stored as `""`. Django's convention is to avoid nullable text columns, because
then there are two ways to say "empty" — `NULL` and `""` — and every query has to
handle both. `locality` is a foreign key, where there is no empty-string
equivalent, so a missing one genuinely must be `NULL`; it takes both flags,
because `null` lets the database store nothing and `blank` lets a form submit
nothing.

One exception, in `Pandal`:

```python
custom_domain = models.CharField(max_length=253, blank=True, unique=True, null=True)
```

Here `null=True` on a text field is correct, and it is forced by `unique=True`.
Postgres treats every `NULL` as distinct, so many pandals may have no custom
domain. If this stored `""` instead, the second pandal without a custom domain
would violate the unique index.

---

## 3 · Abstract base models

```python
class TimeStampedModel(models.Model):
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        abstract = True


class BaseModel(TimeStampedModel):
    id = models.UUIDField(primary_key=True, default=uuid7, editable=False)

    class Meta:
        abstract = True
```

`abstract = True` means **no table is created for this class**. Its fields are
copied into every subclass. `Pandal(BaseModel)` gets `id`, `created_at` and
`updated_at` as its own columns in `pandals_pandal`.

The alternative Django offers is *multi-table inheritance* — drop `abstract` and
Django creates a real `common_basemodel` table with an implicit join to every
child. That means every single query joins two tables forever. Abstract
inheritance is almost always what you want; concrete inheritance is a trap.

**`auto_now_add` versus `auto_now`.** `auto_now_add=True` sets the value once, on
insert. `auto_now=True` overwrites it on every save. So `created_at` never moves
and `updated_at` always tracks the last write. Both ignore anything you assign to
them, which is occasionally surprising in tests — that is why the tests use
`.update()` to force timestamps.

**Why `db_index=True` on `created_at`.** Almost every list in this system is
"newest first". An index makes that ordering cheap. Indexes are not free — they
slow writes and take space — so they are added where a query actually needs one,
not by reflex.

### Why UUIDs, and why version 7

```python
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

Django's default primary key is `BigAutoField` — 1, 2, 3. That is fast and small,
and it leaks. If a donation is `/orders/41`, anyone can try `/orders/42`, and the
count of your orders is public information.

The usual fix is `uuid4`, which is random. But random primary keys scatter inserts
across the whole B-tree index, so every insert dirties a different page. Under a
festival's write burst that matters.

**UUIDv7 puts a millisecond timestamp in the first 48 bits**, so IDs generated
near each other in time sort near each other in the index — the locality of an
auto-increment with the opacity of a random one. The bit-twiddling above is
literally the RFC 9562 layout: 48 bits of time, four bits of version (`0x70`),
then randomness, with two variant bits set to `10`.

`editable=False` keeps it out of forms and admin. `default=uuid7` passes the
*function*, not `uuid7()` — passing the call would generate one value at import
time and give every row the same ID.

---

## 4 · `pandals/models.py`, decision by decision

### `TextChoices`

```python
class PublicationStatus(models.TextChoices):
    DRAFT = "draft", "Draft"
    PENDING_REVIEW = "pending_review", "Pending review"
    PUBLISHED = "published", "Published"
```

Each entry is `(value stored in the database, label shown to a human)`. Nesting
the class inside the model scopes it: `Pandal.PublicationStatus.DRAFT`.

Why not just store the string `"draft"` directly? Because then it is spelled by
hand in a dozen places and one of them eventually says `"Draft"`. With
`TextChoices` you get an autocompleted constant, a `get_publication_status_display()`
method for free, and Django validates the value on save.

Why strings rather than integers (`1 = draft`)? Integers are smaller, but
`SELECT * FROM pandals_pandal WHERE publication_status = 2` is unreadable at
three in the morning during a festival. Storage is not the constraint here;
legibility is.

### The slug is the subdomain

```python
slug = models.SlugField(max_length=63, unique=True, validators=[validate_subdomain],
                        help_text="Also the subdomain: <slug>.edurgapuja.app")
```

`SlugField` is a `CharField` with a built-in check for letters, digits, hyphens
and underscores. That is not quite strict enough here, because this value becomes
a DNS label, so a custom validator runs as well:

```python
SUBDOMAIN_RE = re.compile(r"^[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?$")

def validate_subdomain(value: str) -> None:
    if not SUBDOMAIN_RE.match(value):
        raise ValidationError(...)
    if value in settings.RESERVED_SUBDOMAINS:
        raise ValidationError(f"'{value}' is reserved. Choose another name.")
```

`max_length=63` is not arbitrary — it is the maximum length of a DNS label. The
regular expression enforces "starts and ends alphanumeric, hyphens allowed in the
middle", which is exactly the DNS rule. The reserved-name check lives in settings
rather than in the code so it can be extended without a deployment.

**A validator is not a database constraint.** It runs in `full_clean()`, which
Django calls from forms and DRF serialisers but *not* from `Model.save()`. So a
validator protects the edges of the system, and a `CheckConstraint` protects the
database itself. Use validators for "a human typed something odd" and constraints
for "this must never be true".

### `on_delete` — the question Django forces you to answer

```python
city = models.ForeignKey("geo.City", on_delete=models.PROTECT, related_name="pandals")
locality = models.ForeignKey("geo.Locality", null=True, blank=True,
                             on_delete=models.SET_NULL, related_name="pandals")
```

`on_delete` has no default; Django makes you decide what happens to *this* row
when the row it points at is deleted. The three used in this codebase:

| Choice | Meaning | Used for |
|---|---|---|
| `PROTECT` | Refuse the delete | `Pandal.city`, `Order.pandal`, `Donation.pandal` |
| `CASCADE` | Delete this row too | `PageBlock.pandal`, `Service.pandal` |
| `SET_NULL` | Keep the row, forget the link | `Pandal.locality`, every `updated_by` |

The reasoning is consistent: **`CASCADE` where the child is meaningless without
the parent** — a page block for a deleted pandal is nothing — and **`PROTECT`
where the child is a financial record.** Deleting a pandal must not silently
delete its donations; it should fail loudly and make a human decide. `SET_NULL`
is for links that are useful but not essential: if an admin account is removed,
the live status they published should survive with the attribution dropped.

`Order.pandal` is `PROTECT` for the same reason a bank does not let you delete a
branch that has accounts.

### `related_name`

```python
city = models.ForeignKey("geo.City", ..., related_name="pandals")
```

This names the reverse accessor: `city.pandals.all()`. Without it, Django invents
`city.pandal_set`, which is clumsy. Where the reverse is never wanted:

```python
updated_by = models.ForeignKey(settings.AUTH_USER_MODEL, ..., related_name="+")
```

`"+"` means "create no reverse accessor at all". Several models point at `User`
for an audit trail; without `"+"` the `User` class would accumulate a dozen
reverse relations nobody uses, and — more practically — two fields on the same
model pointing at `User` would clash and refuse to start.

### String references and circular imports

```python
city = models.ForeignKey("geo.City", ...)
```

Rather than `from apps.geo.models import City`. Both work, but the string form
is resolved lazily by Django's app registry, which sidesteps circular imports:
`accounts.AdminMembership` points at `pandals.Pandal`, and `pandals` models
reference `settings.AUTH_USER_MODEL`, which is `accounts.User`. Written as real
imports that is a cycle. Written as strings it is fine.

Always write `settings.AUTH_USER_MODEL` rather than importing the user model
directly — it is the one reference Django guarantees works everywhere.

### Capabilities as columns, not as a derived query

```python
sells_passes = models.BooleanField(default=False)
accepts_donations = models.BooleanField(default=True)
offers_services = models.BooleanField(default=False)
```

You could work out whether a pandal sells passes by asking whether it has any
active pass configuration rows. That is tempting — no duplicated state — and it
is wrong here for two reasons. A pandal with nothing on sale *this week* is not
the same as one that never sells passes, and the landing page has to answer the
question on every request, which would mean a subquery on the hottest read in the
system. Explicit columns say what the owner meant, and cost one boolean.

### `@property` — computed, never stored

```python
@property
def canonical_host(self) -> str:
    return self.custom_domain or f"{self.slug}.{settings.SITE_DOMAIN}"

@property
def canonical_url(self) -> str:
    return f"https://{self.canonical_host}"
```

These are Python, not columns. Nothing is written to the database, and there is
no way for them to drift out of step with `slug`. The rule of thumb: **if it can
be derived, derive it.** Store it only when you need to query or index by it,
because a stored copy is a second source of truth that will eventually disagree.

The cost is that you cannot filter by a property — `Pandal.objects.filter(canonical_url=…)`
does not work, because the database has never heard of it. That is fine here; we
always look up by `slug`.

### `__str__`

```python
def __str__(self) -> str:
    return self.name
```

Every model defines one. It is what the Django admin shows in dropdowns, what a
debugger prints, and what appears in test failure messages. Skipping it gives you
`<Pandal: Pandal object (0192...)>`, which tells you nothing at the moment you
most need to know something.

---

## 5 · `Meta` — everything about the table that is not a column

```python
class Meta:
    ordering = ("name",)
    indexes = [models.Index(fields=["city", "publication_status"])]
```

**`ordering`** gives every unqualified queryset a default sort. Worth setting
wherever a list is displayed — and *necessary* wherever results are paginated,
because paginating an unordered query means the database may return rows in any
order and page two can repeat a row from page one. Django emits a warning about
exactly this, which is why `PandalLiveStatus` carries `ordering = ("pandal__name",)`.

**`indexes`** covers the queries you actually run. `["city", "publication_status"]`
is one composite index for "published pandals in Kolkata" — the browse query. The
column order matters: a composite index on `(city, status)` also serves a query
filtered only by `city`, but not one filtered only by `status`.

### Constraints — the database as the last line of defence

```python
constraints = [
    models.UniqueConstraint(fields=["pandal", "kind", "language"],
                            name="uniq_block_per_pandal_kind_language")
]
```

A pandal has one hero block per language. Enforcing that in Python means
`if PageBlock.objects.filter(...).exists()` — which two simultaneous requests both
pass before either writes. The database has no such race.

Two more interesting forms appear in this codebase.

**A partial unique index**, in `accounts/models.py`:

```python
models.UniqueConstraint(
    fields=["email"],
    condition=~models.Q(email=""),
    name="uniq_user_email_when_present",
)
```

Email is optional, so many users have `""`. A plain `unique=True` would allow
exactly one such user. `condition` makes the index apply only to rows where the
email is not empty — "unique when present". `~models.Q(...)` is a negated query
expression; `Q` objects are how you build conditions that are more than a keyword
argument.

**A check constraint**, in `services/models.py`, and this is the important one:

```python
models.CheckConstraint(condition=models.Q(issued_count__lte=models.F("capacity")),
                       name="service_day_issued_within_capacity")
```

`F("capacity")` refers to *another column on the same row*, evaluated by the
database. So this compiles to `CHECK (issued_count <= capacity)`, and no code path
— ORM, raw SQL, a psql session, a future bug — can put more bookings into a day
than the pandal allowed. There is a test that deliberately tries, via raw
`.update()` bypassing every line of application logic, and asserts Postgres
refuses it.

This is the single most important line in the schema. Application logic is the
second line of defence, not the first.

---

## 6 · The custom user model

```python
class User(AbstractBaseUser, PermissionsMixin, BaseModel):
    phone = models.CharField(max_length=20, unique=True)
    ...
    USERNAME_FIELD = "phone"
    REQUIRED_FIELDS: list[str] = []
```

Django ships a `User` with a mandatory `username` and an optional email. Here the
identity is a mobile number and there is no username at all, so we build our own.

- **`AbstractBaseUser`** supplies the password machinery and `last_login`, and
  nothing else. (The other option, `AbstractUser`, keeps Django's fields and lets
  you add to them — the right choice when you want `username` and just need extra
  columns.)
- **`PermissionsMixin`** supplies `is_superuser`, `groups` and `user_permissions`,
  which the Django admin needs.
- **`USERNAME_FIELD`** tells Django what to authenticate against.
- **`REQUIRED_FIELDS`** is what `createsuperuser` prompts for *in addition* to the
  username field and password. Empty, because a phone and a password are enough.

```python
AUTH_USER_MODEL = "accounts.User"
```

**This setting must be right before the first migration is ever run.** Changing it
afterwards on a live database is one of the genuinely painful things in Django,
because every foreign key to `auth_user` has to be rewritten. Hence the rule:
*define the custom user model first, always, even if it starts identical to the
default.*

### Why a manager

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

A **manager** is what `Model.objects` is. Django requires a custom user manager
because `createsuperuser` and the auth system call `create_user` and
`create_superuser` by name.

Two details worth noticing. `set_password` hashes; assigning to `user.password`
directly would store plaintext, and nothing would warn you. And
`set_unusable_password()` is what makes an OTP-only account possible: it writes a
value that no password can ever hash to, so the account exists and can never be
signed into with a password.

`using=self._db` respects multiple-database routing. `use_in_migrations = True`
lets migrations call this manager.

### Codes are hashed, and compared in constant time

```python
@staticmethod
def hash_code(code: str, destination: str) -> str:
    return hmac.new(settings.SECRET_KEY.encode(),
                    f"{destination}:{code}".encode(), hashlib.sha256).hexdigest()

def verify(self, code: str) -> bool:
    return hmac.compare_digest(self.code_hash, self.hash_code(code, self.destination))
```

A one-time code is a credential, so it is never stored in the clear — a database
dump would otherwise be a list of live login codes.

Two subtleties. The destination is mixed into the hash, so a code hashed for one
number cannot be replayed against another. And `hmac.compare_digest` compares in
constant time: a normal `==` returns as soon as two bytes differ, and the timing
difference is measurable over enough attempts. It costs nothing to use the safe
comparison.

Not `set_password` here, because Argon2 is deliberately slow — right for a
password, wrong for something verified thousands of times an hour under load.

---

## 7 · The capacity primitive — transactions and locks

This is the part where Django stops being a form of SQL shorthand and you have to
think about what the database is actually doing.

### The problem

Two people want the last place on a curated tour. Both read "1 available". Both
write "0 available". Two bookings, one place. This is a **race condition**, and it
is not solved by careful Python.

### The solution

```python
@transaction.atomic
def place_hold(day_model, hold_model, *, day_id, quantity: int, ...):
    day = day_model.objects.select_for_update().get(pk=day_id)
    ...
    free = available(hold_model, day)
    if quantity > free:
        raise CapacityUnavailableError(...)
    return hold_model.objects.create(day=day, quantity=quantity, ...)
```

**`@transaction.atomic`** wraps everything in one database transaction: all of it
commits, or none of it does. As a decorator it wraps a function; it also works as
a context manager (`with transaction.atomic():`), which is how the tests use it.

**`select_for_update()`** issues `SELECT … FOR UPDATE`, which takes a row-level
lock. The second transaction asking for the same row *blocks* until the first
commits — and then re-reads, seeing the first one's effect. The race is gone.

Two rules come with it. `select_for_update()` outside a transaction raises an
error, because there would be nothing to hold the lock. And the lock is on the
`pandal_day_capacity` row only, so two different services, or the same service on
two different days, never wait for each other. The Ashtami rush contends on the
one row it must and nothing else.

### Holds are rows, not a counter

```python
def live_holds(hold_model, day):
    return hold_model.objects.filter(day=day, released_at__isnull=True,
                                     expires_at__gt=timezone.now())

def available(hold_model, day) -> int:
    held = live_holds(hold_model, day).aggregate(n=Sum("quantity"))["n"] or 0
    return max(0, day.capacity - day.issued_count - held)
```

The obvious design is a `held_count` column: add on hold, subtract on release. It
is faster to read, and it has a failure mode — if the release never happens
because a process died, the capacity is gone until someone notices.

Storing holds as rows with an `expires_at` means **availability is computed, and
an expired hold stops counting the moment it expires.** No sweeper has to run for
capacity to come back. `expire_holds()` exists, but it is housekeeping; there is a
test asserting that capacity is already free *before* it runs.

`__isnull=True` and `__gt=` are Django **field lookups** — the double-underscore
syntax that turns into SQL. `aggregate` runs `SUM()` in the database and returns a
dict; `or 0` handles `SUM` of no rows, which is `NULL`, which Python sees as
`None`.

### `.update()` versus `.save()`

```python
OtpChallenge.objects.filter(pk=challenge.pk).update(attempts=F("attempts") + 1)
```

`.save()` reads a value into Python, changes it, writes it back — and two
concurrent increments both read 3 and both write 4. `.update()` with an `F()`
expression compiles to `SET attempts = attempts + 1`, computed by the database,
so both increments land.

The trade-off: `.update()` does not call `save()`, does not touch `auto_now`
fields, and does not fire signals. That is exactly why the tests use it to force
an `expires_at` into the past — it is the way to write a value that a model would
otherwise manage for you.

### Overriding `save()`

```python
def save(self, *args, **kwargs):
    self.amount_paise = self.unit_amount_paise * self.quantity
    super().save(*args, **kwargs)
```

On `OrderLine`, so a line's total can never disagree with its own price and
quantity. `*args, **kwargs` and the `super()` call are essential — Django passes
things like `update_fields` through, and swallowing them breaks the ORM in ways
that are hard to trace.

Django also offers **signals** (`post_save` and friends) for this. They are
avoided throughout this codebase: a signal is action at a distance, invisible at
the call site, and debugging one means searching the whole project for something
that listens. An explicit method call or a `save()` override says what happens
where it happens.

---

## 8 · Money, and JSON

### Money is an integer

```python
amount_paise = models.BigIntegerField()
```

Never `FloatField`: `0.1 + 0.2` is famously not `0.3` in binary floating point,
and money that does not add up is not money.

Django offers `DecimalField`, which is exact and correct. Integer paise is chosen
instead because it removes a whole category of question — no rounding mode, no
precision argument, no `Decimal` versus `float` mistakes when a value passes
through JSON to a client. Every amount is a whole number of paise; the client
divides by 100 to display. The convention is enforced by the name: a column
ending `_paise` is an integer.

`rupees()` in `common/models.py` exists for display and is never used in a
calculation.

### `JSONField` where the shape genuinely varies

```python
content = models.JSONField(default=dict, blank=True)   # PageBlock
details = models.JSONField(default=dict, blank=True)   # ServiceBooking
```

Normally a column per field is right. These two are the exception: a hero block
and a footer block share no fields, and a puja booking captures gotra and sankalp
while an accessibility booking captures wheelchair requirements. Modelling that as
columns would mean a table of mostly-empty columns, or a table per block type.

`default=dict` passes the *function* — `default={}` would share one dictionary
between every instance, a classic Python bug.

The danger with JSON is that it becomes a place to put anything. So it is fenced:

```python
TYPE_FIELDS: dict[str, set[str]] = {
    ServiceType.PUJA_IN_YOUR_NAME: {"name", "contact_phone", "name_for_puja",
                                    "gotra", "sankalp", "preferred_time"},
    ...
}

def validate_details(service, details: dict) -> dict:
    unknown = set(details) - service.allowed_detail_fields
    if unknown:
        raise ValidationFailedError(...)
    return {k: v for k, v in details.items() if v not in (None, "")}
```

Each service type declares what its form may submit; anything else is refused
rather than stored. Gotra and sankalp are religious data and assistance type is
disability data, so the only service that can store them is the one that actually
asks. Holding data nobody requested is how a sensitive-data problem starts.

---

## 9 · Errors

DRF's default error shape varies by exception type. One envelope is easier to
consume, so `common/errors.py` defines it:

```python
class DomainError(APIException):
    status_code = status.HTTP_400_BAD_REQUEST
    default_code = "bad_request"

class CapacityUnavailableError(DomainError):
    status_code = status.HTTP_409_CONFLICT
    default_code = "capacity_unavailable"
```

and a handler wired in by:

```python
"EXCEPTION_HANDLER": "apps.common.errors.exception_handler",
```

The point is that **domain code raises domain exceptions**. `place_hold` raises
`CapacityUnavailableError` and knows nothing about HTTP; the handler turns it into
a 409 with a stable machine-readable `code` the client can branch on. The
alternative — returning `Response(...)` from deep inside a service function —
drags HTTP concerns into business logic and makes it untestable without a request.

The exceptions carry structured extras:

```python
raise CapacityUnavailableError(f"Only {free} place{'s' if free != 1 else ''} remain.",
                               available=free)
```

so the client can offer the next available day rather than a dead end.

---

## 10 · Migrations

```bash
uv run python manage.py makemigrations   # write the change as a file
uv run python manage.py migrate          # apply it
```

Migrations are generated Python files describing schema changes. They are
committed to the repository, because they are the history of the database and
every environment must apply the same ones in the same order.

The check that matters in CI:

```bash
uv run python manage.py makemigrations --check --dry-run
```

This fails if a model has been edited without a migration being generated. Without
it, someone adds a field, tests pass locally against their already-migrated
database, and production breaks on deploy. It is two lines of CI and it catches a
whole class of outage.

---

## 11 · Tests

```python
pytestmark = pytest.mark.django_db
```

Every test in the module gets a database, wrapped in a transaction that is rolled
back afterwards — so tests cannot pollute each other and no cleanup is needed.

**Fixtures** are dependency injection. Declaring `def test_x(service_day)` makes
pytest build a `service_day`, which needs a `service`, which needs a `pandal`,
which needs a `city`. You ask for the thing you need and the chain is constructed.

```python
@pytest.fixture(autouse=True)
def _clean_side_state():
    cache.clear()
    MemorySender.reset()
    yield
    cache.clear()
    MemorySender.reset()
```

`autouse=True` runs it for every test without being asked. It exists because rate
limits live in the cache and issued codes live in a class attribute — **outside**
the database, so the transaction rollback does not reach them. Everything with
state outside the database needs deliberate cleanup.

### The one test that needs real transactions

```python
@pytest.mark.django_db(transaction=True)
def test_only_one_of_many_racing_visitors_gets_the_last_place(city, locality):
    barrier = threading.Barrier(8)

    def contend():
        barrier.wait()
        try:
            inventory.place_hold(day_id=day.pk, quantity=1)
            outcomes.append("held")
        except CapacityUnavailableError:
            outcomes.append("refused")
        finally:
            connection.close()
```

The normal `django_db` wraps everything in one transaction, which means other
threads cannot see the data — so a concurrency test needs `transaction=True`,
which uses real commits and truncates tables afterwards. It is slower, which is
why only this test uses it.

`threading.Barrier(8)` makes all eight threads wait until the eighth arrives, so
they hit the row at genuinely the same moment rather than in a straggle.
`connection.close()` in a `finally` matters because Django keeps one connection
per thread and a leaked one will hang the suite.

### The property test

```python
@given(ops=st.lists(operation, max_size=40))
def test_issued_plus_live_holds_never_exceeds_capacity(service, ops):
    for name, qty in ops:
        ...
        assert day.issued_count + held <= day.capacity
```

Hypothesis generates the input rather than you writing it. Instead of asserting
that a specific sequence produces a specific answer, you assert a **property that
must hold for every sequence** — and Hypothesis goes looking for a counter-example,
then shrinks it to the smallest one that still fails.

This is the right tool for an invariant. Example-based tests check the cases you
thought of; the bug is usually in one you did not.

---

## 12 · Django features deliberately not used

Worth knowing about, and worth knowing why they are absent here.

**Signals** (`post_save`, `pre_delete`). Action at a distance. An explicit call is
easier to read, easier to test, and does not fire during migrations or fixture
loading when you least expect it.

**`GenericForeignKey`** — pointing at any model via the content-types framework.
It was tempting for `OrderLine`, which needs to reference a donation or a booking.
It is avoided because it cannot be a real foreign key, so the database cannot
enforce that the target exists, and querying across it is slow. Instead `OrderLine`
carries a `kind` string and the concrete models point *back* at their line — a
real, enforced, indexable relationship, and revenue can be grouped by `kind`
without a join at all.

**Multi-table inheritance** — every query silently becomes a join.

**Fat models.** The capacity operations live in `inventory/operations.py`, not as
methods on `ServiceDayCapacity`. They span two models and take a lock, so they are
not really behaviour *of* a row; putting them in a module makes the transaction
boundary visible, and lets the same four functions serve pass capacity later
without inheritance games.

---

## Where to look next, in order

1. `apps/inventory/operations.py` — the whole file, then `tests/test_capacity.py`
   beside it. Sixty lines that contain most of the difficulty in the system.
2. `apps/pandals/models.py` — the widest range of field and relationship
   decisions.
3. `apps/accounts/models.py` — the custom user model and the credential handling.
4. `apps/orders/models.py` — small, and the reason adding passes later will be
   cheap.
