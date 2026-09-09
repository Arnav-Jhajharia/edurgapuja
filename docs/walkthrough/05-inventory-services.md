# Part 5 · Inventory and services

`apps/inventory/` is sixty lines of models and eighty of operations, and it is the
part of the system where being wrong costs money. `apps/services/` builds on it.

---

## `apps/inventory/models.py`

Two abstract models. No tables are created by this app at all.

```python
class DayCapacity(BaseModel):
    date = models.DateField()
    capacity = models.PositiveIntegerField()
    issued_count = models.PositiveIntegerField(default=0)
    is_open = models.BooleanField(default=True)

    class Meta:
        abstract = True
```

**`abstract = True`** — the fields are copied into each concrete subclass.
`ServiceDayCapacity` gets them today; `PandalDayCapacity` will get the identical
set when passes arrive. One definition, two tables, no join.

**`PositiveIntegerField`** rather than `IntegerField`. It adds a database
`CHECK (capacity >= 0)`, visible in `psql`. A negative capacity is meaningless, so
the database should refuse it rather than the application remembering to.

**`issued_count` denormalises a count** that could be derived by counting bookings.
That is a deliberate trade: the count is read on every availability check, and it
is the column the `CHECK` constraint compares against. A `COUNT(*)` cannot appear
in a `CHECK`.

**`is_open`** closes a day without deleting it, so the history of what was sold
survives.

**No `unique` here** — the uniqueness is `(service, date)`, and `service` only
exists on the concrete subclass, so the constraint belongs there.

```python
class Hold(BaseModel):
    quantity = models.PositiveIntegerField()
    expires_at = models.DateTimeField()
    released_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        abstract = True
```

**Three columns that encode the whole design.** A hold is live when
`released_at IS NULL` and `expires_at > now()`. There is no status field, because
those two facts already say everything.

**`released_at` as a nullable timestamp, not a boolean.** It answers "released?"
and "when?" at once.

**No foreign key to the day here**, because the abstract class cannot know which
concrete capacity table it points at. The subclass adds it, always named `day`,
and the operations module relies on that name.

---

## `apps/inventory/operations.py`

### Imports

```python
from datetime import timedelta

from django.conf import settings
from django.db import transaction
from django.db.models import Sum
from django.utils import timezone

from apps.common.errors import CapacityUnavailableError, HoldExpiredError
```

**`Sum`** is an aggregate function that runs in the database.

**`transaction`** for `atomic`.

**The exceptions are domain errors**, so this module raises meaning rather than
HTTP status codes and stays testable without a request.

### `live_holds`

```python
def live_holds(hold_model, day):
    return hold_model.objects.filter(day=day, released_at__isnull=True,
                                     expires_at__gt=timezone.now())
```

**`hold_model` is passed in**, not imported. This is what makes the module reusable
across capacity types without inheritance or generic foreign keys — the caller
supplies the concrete classes.

**Three conditions** matching the definition of "live": belongs to this day, not
released, not expired.

**`__isnull=True`** compiles to `IS NULL`. Writing `released_at=None` also works,
but the lookup is explicit about intent.

**`expires_at__gt=timezone.now()`** — `now()` is evaluated in Python and sent as a
parameter, so every caller sees a consistent instant rather than the database's
clock drifting mid-query.

**Returns a queryset, not a list.** Nothing has been fetched yet, so callers can
count, sum or iterate as they need.

### `available`

```python
def available(hold_model, day) -> int:
    """Computed, never stored. An expired hold stops counting immediately."""
    held = live_holds(hold_model, day).aggregate(n=Sum("quantity"))["n"] or 0
    return max(0, day.capacity - day.issued_count - held)
```

**`.aggregate(n=Sum("quantity"))`** runs `SELECT SUM(quantity)` in the database and
returns `{"n": 42}`. Summing in Python would mean fetching every hold row.

**`or 0`** — `SUM` over no rows is `NULL`, which arrives as `None`, and `None`
cannot be subtracted. This is the single most commonly forgotten line when writing
an aggregate.

**`max(0, ...)`** — defensive. The arithmetic should never go negative, but
returning `-3` from a function called `available` would be worse than clamping.

**This is the heart of the design.** Availability is *derived*, so a hold that
expired one millisecond ago has already stopped occupying capacity. No cleanup job
needs to have run. There is a test that asserts exactly this.

### `place_hold`

```python
@transaction.atomic
def place_hold(day_model, hold_model, *, day_id, quantity: int, ttl_seconds: int | None = None,
               **hold_fields):
```

**`@transaction.atomic`** — everything inside commits together or not at all. It
is also what makes the row lock on the next line legal; `select_for_update()`
outside a transaction raises.

**`day_id`, not a `day` object.** Taking the ID forces the function to fetch the
row itself, *under the lock*. Accepting an object would invite a caller to pass one
they fetched earlier, whose `issued_count` is already stale.

**`**hold_fields`** collects extras — `order=order` — and passes them to the hold's
`create`. It keeps the generic function ignorant of what a service hold happens to
carry.

```python
    day = day_model.objects.select_for_update().get(pk=day_id)
    if not day.is_open:
        raise CapacityUnavailableError("Bookings for that day are closed.", available=0)
```

**`select_for_update()`** issues `SELECT ... FOR UPDATE`, taking a row-level lock.
A second transaction asking for the same row **waits** until the first commits,
then re-reads and sees its effect. This is the line that makes the race condition
impossible.

The lock covers exactly one row, so two different services — or the same service on
two different days — never wait for each other.

**`.get(pk=day_id)`** raises `DoesNotExist` if there is no such row. Deliberately
not caught: a caller passing an unknown ID is a bug, not a user error.

```python
    free = available(hold_model, day)
    if quantity > free:
        raise CapacityUnavailableError(
            f"Only {free} place{'s' if free != 1 else ''} remain.", available=free
        )
```

**Availability is computed *after* the lock is held**, which is the entire point.
Computing it before would read a value another transaction is about to change.

**`{'s' if free != 1 else ''}`** — "Only 1 place remains" rather than "1 places".
Small, and it is the difference between a message that reads like software and one
that reads like a person.

**`available=free`** rides out in the error envelope so the client can offer the
next day.

```python
    ttl = ttl_seconds or settings.CAPACITY_HOLD_TTL_SECONDS
    return hold_model.objects.create(
        day=day, quantity=quantity,
        expires_at=timezone.now() + timedelta(seconds=ttl),
        **hold_fields,
    )
```

**`ttl_seconds or settings...`** — the parameter defaults to `None`, so a caller
can override the window for a slow payment method without changing the global.

**`expires_at` computed once, at creation.** The lifetime is a property of the
hold, not of the checker, so changing the setting later cannot retroactively kill
holds already in flight.

### `issue`

The most subtle function in the project.

```python
@transaction.atomic
def issue(day_model, hold_model, *, hold_id):
    hold = hold_model.objects.select_related("day").get(pk=hold_id)
    day = day_model.objects.select_for_update().get(pk=hold.day_id)
```

**`select_related("day")`** fetches the hold and its day in one query rather than
two.

**Then the day is fetched *again*, with a lock.** That looks wasteful and is not:
the first fetch is unlocked and only tells us which day to lock. The second takes
the lock and gets a guaranteed-fresh row. Locking and reading must be the same
statement, or another transaction slips between them.

**`hold.day_id`, not `hold.day.id`** — the raw column, no extra query.

```python
    expired = hold.released_at is not None or hold.expires_at <= timezone.now()
    if expired:
        free = available(hold_model, day)
        if free < hold.quantity:
            raise HoldExpiredError("That place was taken while the payment completed.",
                                   available=free)
        hold.expires_at = timezone.now() + timedelta(seconds=60)
        hold.released_at = None
```

**This block is the late-payment case**, and it is the one most systems get wrong.

A visitor holds a place, pays, and the payment provider's callback arrives twenty
minutes later. By then the hold has lapsed. Three possible behaviours:

1. Refuse, and refund. Correct but hostile if the place is still free.
2. Issue anyway. Simple, and it oversells.
3. **Re-acquire under the lock.** Still free → honour it. Gone → refuse, and the
   caller refunds.

The third is what is implemented. `hold.released_at = None` revives the hold so
the code below treats it uniformly, and the sixty-second window is nominal — it is
released a few lines later regardless.

```python
    day.issued_count += hold.quantity
    day.save(update_fields=["issued_count", "updated_at"])
```

**`+=` in Python, not an `F()` expression** — and here that is correct, because
the row is locked. `F("issued_count") + 1` would be right without a lock; under
one, plain arithmetic on a guaranteed-fresh value is clearer.

**This is the write the `CHECK` constraint guards.** If a bug ever let it exceed
capacity, Postgres raises `IntegrityError` and the transaction rolls back.

```python
    hold.released_at = timezone.now()
    hold.save(update_fields=["expires_at", "released_at", "updated_at"])
    return day
```

**The hold is released as it is issued**, so it stops counting against
availability — otherwise the same quantity would be subtracted twice, once as
issued and once as held.

### `release_hold` and `expire_holds`

```python
@transaction.atomic
def release_hold(hold_model, *, hold_id) -> None:
    hold_model.objects.filter(pk=hold_id, released_at__isnull=True).update(
        released_at=timezone.now()
    )
```

**`.filter(...).update(...)`** — one statement, no read. It also makes the
operation idempotent: `released_at__isnull=True` means a second call matches
nothing and quietly does nothing, rather than overwriting the original timestamp.

**No lock needed.** Releasing only ever *increases* availability, so there is
nothing to race with.

```python
def expire_holds(hold_model) -> int:
    return hold_model.objects.filter(
        released_at__isnull=True, expires_at__lte=timezone.now()
    ).update(released_at=timezone.now())
```

**No `@transaction.atomic`** — a single `UPDATE` is already atomic.

**Returns the number of rows updated**, which is what `.update()` gives back.
Useful for logging.

**Housekeeping only.** Correctness does not depend on this ever running, and a
test asserts capacity is already free before it is called. It exists to stop the
holds table growing without bound and to make `available` cheaper.

---

## `apps/services/models.py`

### `ServiceType` and the field map

```python
class ServiceType(models.TextChoices):
    CURATED_TOUR = "curated_tour", "Curated tour"
    PUJA_IN_YOUR_NAME = "puja_in_your_name", "Puja in your name"
    SPECIAL_ASSISTANCE = "special_assistance", "Special assistance"
    AARTI_SLOT = "aarti_slot", "Aarti slot"
    GENERIC = "generic", "Priced service"
```

**Module-level, not nested**, because both `Service` and `validate_details` use it.

The platform owns these five *shapes*; each pandal owns its own *offerings*. That
split is what reconciled the two service catalogues that looked incompatible.

```python
TYPE_FIELDS: dict[str, set[str]] = {
    ServiceType.CURATED_TOUR: {"name", "contact_phone", "party_size", "notes"},
    ServiceType.PUJA_IN_YOUR_NAME: {"name", "contact_phone", "name_for_puja", "gotra", "sankalp",
                                     "preferred_time"},
    ...
}
```

**A module-level constant**, not a database table, because adding a field to a
form means writing code to render it anyway — so a migration buys nothing.

**Sets, not lists**, because the only operation is membership and difference.
`set(details) - allowed` is the whole validation.

### `Service`

```python
class Service(BaseModel):
    pandal = models.ForeignKey("pandals.Pandal", on_delete=models.CASCADE, related_name="services")
    type = models.CharField(max_length=24, choices=ServiceType.choices,
                            default=ServiceType.GENERIC)
    name = models.CharField(max_length=120)
    slug = models.SlugField(max_length=120)
    description = models.TextField(blank=True)
    price_paise = models.BigIntegerField()
    max_per_booking = models.PositiveSmallIntegerField(default=10)
    is_active = models.BooleanField(default=True)
    sort_order = models.PositiveSmallIntegerField(default=0)
```

**`type` shadows a Python builtin.** Acceptable as an attribute — `service.type`
never collides with the builtin in practice — and `service_type` would read
worse in every query.

**`default=ServiceType.GENERIC`** — the common case is a plain priced service, and
the bespoke forms are the exception.

**`price_paise = models.BigIntegerField()`**, no default, so it must be stated. A
free service is `0`, written deliberately.

**`max_per_booking`** stops someone booking two hundred places on a curated tour
in one transaction.

**`slug` is not globally unique** — it is unique per pandal, enforced below. Two
pandals may both have `donor-darshan`.

```python
    class Meta:
        ordering = ("sort_order", "name")
        constraints = [
            models.UniqueConstraint(fields=["pandal", "slug"], name="uniq_service_slug_per_pandal"),
            models.CheckConstraint(condition=models.Q(price_paise__gte=0),
                                   name="service_price_non_negative"),
        ]
```

**`CheckConstraint(condition=models.Q(price_paise__gte=0))`** — a negative price
would be a refund disguised as a sale. Note `condition=`; in Django 5 this
replaced the older `check=` keyword.

```python
    @property
    def allowed_detail_fields(self) -> set[str]:
        return TYPE_FIELDS[self.type]
```

A property rather than a direct dictionary lookup at each call site, so the map is
consulted in one place.

### `ServiceDayCapacity`

```python
class ServiceDayCapacity(DayCapacity):
    service = models.ForeignKey(Service, on_delete=models.CASCADE, related_name="days")

    class Meta:
        ordering = ("date",)
        verbose_name_plural = "service day capacities"
        constraints = [
            models.UniqueConstraint(fields=["service", "date"], name="uniq_service_day"),
            models.CheckConstraint(condition=models.Q(issued_count__lte=models.F("capacity")),
                                   name="service_day_issued_within_capacity"),
        ]
```

**The subclass adds the owner** — one foreign key — and the abstract parent
supplied everything else.

**`UniqueConstraint(["service", "date"])`** — one capacity row per service per
day, so `place_hold` can lock exactly one row.

**`CheckConstraint(issued_count__lte=F("capacity"))`** — the most important line
in the schema. `F("capacity")` refers to another column *on the same row*,
evaluated by Postgres, compiling to `CHECK (issued_count <= capacity)`.

No code path can breach it. Not the ORM, not raw SQL, not a `psql` session, not a
future bug. There is a test that tries via raw `.update()` and asserts the database
refuses.

**Note that a `Meta` on a subclass does not inherit the parent's.** Nothing is
lost here because the abstract parent's `Meta` only set `abstract`.

### `ServiceCapacityHold`

```python
class ServiceCapacityHold(Hold):
    day = models.ForeignKey(ServiceDayCapacity, on_delete=models.CASCADE, related_name="holds")
    order = models.ForeignKey("orders.Order", null=True, blank=True,
                              on_delete=models.SET_NULL, related_name="service_holds")

    class Meta:
        indexes = [models.Index(fields=["day", "expires_at"])]
```

**`day` must be named `day`** — `operations.py` filters on `day=day`. An informal
contract between the abstract classes and the module, and the price of avoiding
generic foreign keys.

**`order` is nullable** because a hold is placed *before* the order exists in some
flows.

**The composite index `(day, expires_at)`** matches `live_holds` exactly: filter
by day, then by expiry. This is the query that runs on every availability check.

### `ServiceBooking`

```python
    service = models.ForeignKey(Service, on_delete=models.PROTECT, related_name="bookings")
    day = models.ForeignKey(ServiceDayCapacity, on_delete=models.PROTECT, related_name="bookings")
    hold = models.OneToOneField(ServiceCapacityHold, null=True, blank=True,
                                on_delete=models.SET_NULL, related_name="booking")
    order_line = models.OneToOneField("orders.OrderLine", null=True, blank=True,
                                      on_delete=models.SET_NULL, related_name="service_booking")
```

**`PROTECT` on `service` and `day`** — a booking is a financial record, so deleting
a service someone has paid for must fail loudly.

**`OneToOneField` to the hold**, because one hold becomes one booking.

**`order_line` points *back* at the line**, which is the alternative to a generic
foreign key. `OrderLine` carries a `kind` string; the concrete model carries the
real, enforced, indexed relationship. Revenue can then be grouped by `kind` with
no join at all.

```python
    details = models.JSONField(default=dict, blank=True)
```

Validated by `validate_details` before it is written — the JSON is fenced, not
free.

### `validate_details`

```python
def validate_details(service: "Service", details: dict) -> dict:
    from apps.common.errors import ValidationFailedError

    allowed = service.allowed_detail_fields
    unknown = set(details) - allowed
    if unknown:
        raise ValidationFailedError(
            "That service does not collect those details.",
            fields=dict.fromkeys(sorted(unknown), "Not accepted for this service."),
        )
    return {k: v for k, v in details.items() if v not in (None, "")}
```

**`service: "Service"`** in quotes — a forward reference, since the function is
defined below the class. Python does not evaluate it at definition time.

**The import is inside the function.** Only needed on the error path, and it keeps
the module's import graph shallow.

**`set(details)`** — iterating a dict gives its keys, so this is the set of
submitted field names.

**`- allowed`** — set difference, giving exactly what was submitted but not
permitted.

**`dict.fromkeys(sorted(unknown), "...")`** builds `{"gotra": "Not accepted..."}`
for every offending key. `sorted` makes the output deterministic, which matters in
tests.

**`if v not in (None, "")`** strips empty values rather than storing them, so a
blank optional field does not become a stored `""`.

**Returns the cleaned dict** rather than mutating the input. The caller assigns
the result, so it is obvious at the call site that validation happened.

**Why this exists at all.** `gotra` is religious affiliation and
`assistance_type` is disability information. Only the service that actually asks
for them can store them — a curated tour cannot, even if a client sends them.
Holding data nobody requested is how a sensitive-data problem starts.

---

## `apps/services/inventory.py`

```python
from functools import partial

from apps.inventory import operations

from .models import ServiceCapacityHold, ServiceDayCapacity

available = partial(operations.available, ServiceCapacityHold)
live_holds = partial(operations.live_holds, ServiceCapacityHold)
place_hold = partial(operations.place_hold, ServiceDayCapacity, ServiceCapacityHold)
issue = partial(operations.issue, ServiceDayCapacity, ServiceCapacityHold)
release_hold = partial(operations.release_hold, ServiceCapacityHold)
expire_holds = partial(operations.expire_holds, ServiceCapacityHold)
```

**`functools.partial`** takes a function and some leading arguments, and returns a
new function with those already supplied. So

```python
place_hold = partial(operations.place_hold, ServiceDayCapacity, ServiceCapacityHold)
```

means a caller writes

```python
inventory.place_hold(day_id=..., quantity=2)
```

and the model classes are filled in automatically.

**Six lines that make the generic module ergonomic.** Without them every call site
would repeat the two class names, and a typo would silently mix service holds with
some other kind.

**This file is the seam.** When passes arrive, `apps/passes/inventory.py` is these
same six lines with `PandalDayCapacity` and `PandalCapacityHold` — no new
algorithm, no new tests for the mechanism, and the property test already proved
it.
