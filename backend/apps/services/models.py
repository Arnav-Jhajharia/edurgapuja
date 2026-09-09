"""Value-added services.

C6 resolved: a service belongs to its pandal, and so does the shape of its form.

An earlier cut of this had the platform own five form shapes and let a pandal
pick one. That made five a ceiling — a committee wanting a bhog coupon, a
pushpanjali slot or a dhunuchi-naach registration had to wait for a migration.
Now a service declares its own fields (`ServiceField`), and the five shapes
survive as *starting points* in `templates.py` rather than as a closed set.

What did **not** change is the property that mattered: a booking may only submit
fields its service declares, and anything else is refused rather than stored.
Gotra, sankalp and assistance requirements are sensitive, and holding data
nobody asked for is how a sensitive-data problem starts (FR-258). The fence is
still there — the pandal now decides where it stands.
"""

from django.conf import settings
from django.db import models

from apps.common.models import BaseModel
from apps.inventory.models import DayCapacity, Hold


class Service(BaseModel):
    """One offering by one pandal.

    Ballygunge's 'Donor Darshan', somebody's 'VIP Darshan Fast-Track' and a
    third committee's 'Dhunuchi Naach Registration' are all rows here, with
    whatever fields each of them decided to ask for.
    """

    pandal = models.ForeignKey("pandals.Pandal", on_delete=models.CASCADE, related_name="services")

    # Free text, deliberately. It was a five-value enum and that turned out to
    # be a ceiling rather than a taxonomy: a committee's idea of what it offers
    # is not the platform's to enumerate. Used for grouping and display only —
    # nothing branches on it.
    type = models.CharField(max_length=40, blank=True, default="",
                            help_text="A label for grouping, e.g. 'Darshan' or 'Prasad'. Optional.")

    name = models.CharField(max_length=120)
    slug = models.SlugField(max_length=120)
    description = models.TextField(blank=True)
    price_paise = models.BigIntegerField()
    max_per_booking = models.PositiveSmallIntegerField(default=10)

    # Not everything a pandal sells has a daily ceiling. An aarti slot has
    # finite seats and a tour is a small group, but prasad posted to your house
    # does not run out at four o'clock — and forcing a capacity row on it means
    # a service that silently cannot be booked.
    requires_capacity = models.BooleanField(
        default=True,
        help_text="Off for something with no daily limit, like a postal delivery.",
    )

    is_active = models.BooleanField(default=True)
    sort_order = models.PositiveSmallIntegerField(default=0)

    class Meta:
        ordering = ("sort_order", "name")
        constraints = [
            models.UniqueConstraint(fields=["pandal", "slug"], name="uniq_service_slug_per_pandal"),
            models.CheckConstraint(condition=models.Q(price_paise__gte=0),
                                   name="service_price_non_negative"),
        ]

    def __str__(self) -> str:
        return f"{self.name} · {self.pandal.name}"

    @property
    def allowed_detail_fields(self) -> set[str]:
        return {f.key for f in self.fields.all()}


class ServiceField(BaseModel):
    """One question a service's booking form asks.

    This is the table that makes a service anything the pandal wants. The kinds
    are deliberately few and generic — they describe how to render an input and
    how to check what comes back, not what the question means.
    """

    class Kind(models.TextChoices):
        TEXT = "text", "Short text"
        TEXTAREA = "textarea", "Long text"
        PHONE = "phone", "Mobile number"
        EMAIL = "email", "Email"
        NUMBER = "number", "Number"
        DATE = "date", "Date"
        TIME = "time", "Time"
        SELECT = "select", "Choose one"
        CHECKBOX = "checkbox", "Yes or no"

    service = models.ForeignKey(Service, on_delete=models.CASCADE, related_name="fields")

    # The key the booking JSON uses. Stable: renaming the label is a display
    # change, renaming the key would orphan every booking already stored.
    key = models.SlugField(max_length=40)
    label = models.CharField(max_length=80)
    kind = models.CharField(max_length=10, choices=Kind.choices, default=Kind.TEXT)
    required = models.BooleanField(default=False)
    help_text = models.CharField(max_length=200, blank=True)
    #: For SELECT. Ignored by every other kind.
    options = models.JSONField(default=list, blank=True)

    # Marks a field as personal rather than logistical — gotra, a disability, a
    # name to be chanted. It does not change validation; it is what an export or
    # a retention sweep filters on, and what tells an admin screen to warn
    # before showing the column.
    is_sensitive = models.BooleanField(default=False)

    sort_order = models.PositiveSmallIntegerField(default=0)

    class Meta:
        ordering = ("sort_order", "id")
        constraints = [
            models.UniqueConstraint(fields=["service", "key"], name="uniq_field_key_per_service"),
        ]

    def __str__(self) -> str:
        return f"{self.label} ({self.kind}) · {self.service.name}"


class ServiceDayCapacity(DayCapacity):
    """An aarti slot has finite seats and a curated tour is a small group, so a
    service genuinely needs capacity in v1 — which is why the primitive gets
    built and proven here (Scope §4.3). Services with `requires_capacity` off
    have no rows here at all."""

    service = models.ForeignKey(Service, on_delete=models.CASCADE, related_name="days")

    class Meta:
        ordering = ("date",)
        verbose_name_plural = "service day capacities"
        constraints = [
            models.UniqueConstraint(fields=["service", "date"], name="uniq_service_day"),
            models.CheckConstraint(condition=models.Q(issued_count__lte=models.F("capacity")),
                                   name="service_day_issued_within_capacity"),
        ]

    def __str__(self) -> str:
        return f"{self.service.name} {self.date}: {self.issued_count}/{self.capacity}"


class ServiceCapacityHold(Hold):
    day = models.ForeignKey(ServiceDayCapacity, on_delete=models.CASCADE, related_name="holds")
    order = models.ForeignKey("orders.Order", null=True, blank=True,
                              on_delete=models.SET_NULL, related_name="service_holds")

    class Meta:
        indexes = [models.Index(fields=["day", "expires_at"])]


class ServiceBooking(BaseModel):
    class Status(models.TextChoices):
        HELD = "held", "Held, awaiting payment"
        CONFIRMED = "confirmed", "Confirmed"
        EXPIRED = "expired", "Hold expired"
        CANCELLED = "cancelled", "Cancelled"
        REFUNDED = "refunded", "Refunded"

    service = models.ForeignKey(Service, on_delete=models.PROTECT, related_name="bookings")
    # Null for a service with no daily limit — there is no day row to point at.
    day = models.ForeignKey(ServiceDayCapacity, null=True, blank=True,
                            on_delete=models.PROTECT, related_name="bookings")
    hold = models.OneToOneField(ServiceCapacityHold, null=True, blank=True,
                                on_delete=models.SET_NULL, related_name="booking")
    order_line = models.OneToOneField("orders.OrderLine", null=True, blank=True,
                                      on_delete=models.SET_NULL, related_name="service_booking")

    user = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True,
                             on_delete=models.SET_NULL, related_name="service_bookings")
    quantity = models.PositiveSmallIntegerField(default=1)
    status = models.CharField(max_length=12, choices=Status.choices, default=Status.HELD)

    #: Validated against the service type's allowed fields before it is stored.
    details = models.JSONField(default=dict, blank=True)

    confirmed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ("-created_at",)
        indexes = [models.Index(fields=["service", "status"])]
        constraints = [
            models.CheckConstraint(condition=models.Q(quantity__gt=0),
                                   name="service_booking_quantity_positive")
        ]

    def __str__(self) -> str:
        return f"{self.service.name} ×{self.quantity} ({self.status})"


def validate_details(service: "Service", details: dict) -> dict:
    """Check a booking's answers against the questions its service actually asks.

    Two properties, both unchanged from when the platform owned the form:

    * **Unknown keys are refused, never stored.** Gotra, a disability, a name to
      be chanted — these only exist because a service asked for them, and a
      service that did not ask must not be able to hold them (FR-258).
    * **A required question must be answered.** Otherwise a pandal's form is
      decoration and the volunteer finds out at the gate.

    What changed is who declares the questions. The kinds below describe how to
    check an answer, not what it means, which is why five of them cover every
    service anybody has asked for.
    """
    from apps.common.errors import ValidationFailedError

    declared = {f.key: f for f in service.fields.all()}

    unknown = set(details) - set(declared)
    if unknown:
        raise ValidationFailedError(
            "That service does not ask for those details.",
            fields=dict.fromkeys(sorted(unknown), "Not a question this service asks."),
        )

    cleaned: dict = {}
    problems: dict[str, str] = {}

    for key, field in declared.items():
        raw = details.get(key)
        blank = raw is None or (isinstance(raw, str) and not raw.strip())

        if blank:
            if field.required:
                problems[key] = f"{field.label} is required."
            continue

        try:
            cleaned[key] = _coerce(field, raw)
        except ValueError as problem:
            problems[key] = str(problem)

    if problems:
        raise ValidationFailedError("Some answers need attention.", fields=problems)
    return cleaned


def _coerce(field: "ServiceField", raw):
    """Turn one submitted answer into what should be stored, or say why not."""
    kind = field.kind

    if kind == ServiceField.Kind.NUMBER:
        try:
            return int(str(raw).strip())
        except (TypeError, ValueError):
            raise ValueError(f"{field.label} should be a number.") from None

    if kind == ServiceField.Kind.CHECKBOX:
        if isinstance(raw, bool):
            return raw
        return str(raw).strip().lower() in {"true", "yes", "1", "on"}

    if kind == ServiceField.Kind.SELECT:
        value = str(raw).strip()
        if field.options and value not in field.options:
            raise ValueError(f"Choose one of: {', '.join(map(str, field.options))}.")
        return value

    if kind in {ServiceField.Kind.DATE, ServiceField.Kind.TIME}:
        import datetime as _dt
        parse = _dt.date.fromisoformat if kind == ServiceField.Kind.DATE else _dt.time.fromisoformat
        try:
            parse(str(raw).strip())
        except ValueError:
            expected = ("a date like 2026-10-12" if kind == ServiceField.Kind.DATE
                        else "a time like 18:30")
            raise ValueError(f"{field.label} should be {expected}.") from None
        return str(raw).strip()

    if kind == ServiceField.Kind.EMAIL:
        value = str(raw).strip()
        if "@" not in value or "." not in value.split("@")[-1]:
            raise ValueError(f"{field.label} should be an email address.")
        return value

    if kind == ServiceField.Kind.PHONE:
        # Deliberately forgiving: this is a number somebody will be called on,
        # not a credential. The account's own phone is verified by OTP.
        value = "".join(ch for ch in str(raw) if ch.isdigit() or ch == "+")
        if len(value.lstrip("+")) < 8:
            raise ValueError(f"{field.label} does not look like a phone number.")
        return value

    return str(raw).strip()


# Module-level aliases so drf-spectacular's ENUM_NAME_OVERRIDES can reach these
# nested choice sets; it resolves one attribute deep, not two. Without them
# every "status" field in the generated client is named Status<hash>Enum.
BOOKING_STATUS_CHOICES = ServiceBooking.Status.choices
SERVICE_FIELD_KIND_CHOICES = ServiceField.Kind.choices
