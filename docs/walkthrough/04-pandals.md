# Part 4 · Pandals

Two files. `validators.py` is fifteen lines; `models.py` holds five models and
the widest range of field decisions in the project.

---

## `apps/pandals/validators.py`

```python
import re

from django.conf import settings
from django.core.exceptions import ValidationError

SUBDOMAIN_RE = re.compile(r"^[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?$")
```

**`re.compile` at module level.** Compiling once at import and reusing the pattern
avoids re-parsing it on every validation. `re.match(pattern_string, ...)` would
also cache internally, but the explicit form makes the cost obvious and names the
pattern.

**`r"..."`** — a raw string, so backslashes reach the regex engine untouched.
There are none here, but it is the habit worth having.

Reading the pattern:

- `^` and `$` anchor it to the whole string. Without them, `re.match` would
  accept `"good-name!!!"` because it only checks the start.
- `[a-z0-9]` — the first character must be a letter or digit. No leading hyphen.
- `(?:...)` — a **non-capturing** group. `(...)` would capture, which costs a
  little and implies you want the text back. You do not.
- `[a-z0-9-]{0,61}` — up to 61 middle characters, hyphens now allowed.
- `[a-z0-9]` — the last character, again no hyphen.
- `?` — the whole group is optional, so a single-character name like `a` is legal.

1 + 61 + 1 = 63, the maximum length of a DNS label. Uppercase is absent because
DNS is case-insensitive and permitting it would mean two names that look
different but collide.

```python
def validate_subdomain(value: str) -> None:
    if not SUBDOMAIN_RE.match(value):
        raise ValidationError(
            "Use lowercase letters, digits and hyphens only, "
            "not starting or ending with a hyphen, up to 63 characters."
        )
    if value in settings.RESERVED_SUBDOMAINS:
        raise ValidationError(f"'{value}' is reserved. Choose another name.")
```

**Returns `None`.** A Django validator signals failure by raising and success by
returning nothing. It is not a predicate.

**`django.core.exceptions.ValidationError`**, not DRF's. Model-level validators
raise Django's; DRF catches and translates it.

**The message describes the rule, not the violation.** "Use lowercase letters…"
tells the user what to do. "Invalid subdomain" does not.

**`value in settings.RESERVED_SUBDOMAINS`** — a `set`, so membership is
constant-time, and it lives in settings so a name can be reserved without a
deployment.

**When this runs.** Validators fire during `full_clean()`, which DRF serialisers
and Django forms call. `Model.save()` does **not** call it. So this protects the
edges; the database protects itself.

---

## `apps/pandals/models.py`

### Imports

```python
from django.conf import settings
from django.db import models

from apps.common.models import BaseModel

from .validators import validate_subdomain
```

Three import groups separated by blank lines — standard library, third-party
(Django counts as third-party here), then local. Ruff enforces the ordering.

### `Pandal` — the choices

```python
class Pandal(BaseModel):
    class PublicationStatus(models.TextChoices):
        DRAFT = "draft", "Draft"
        PENDING_REVIEW = "pending_review", "Pending review"
        PUBLISHED = "published", "Published"
```

Three states in a workflow, matching the draft → review → publish requirement.
Nested inside the model because only this model uses it, so it is reached as
`Pandal.PublicationStatus.DRAFT`.

### Identity and addressing

```python
    name = models.CharField(max_length=140)
    slug = models.SlugField(max_length=63, unique=True, validators=[validate_subdomain],
                            help_text="Also the subdomain: <slug>.edurgapuja.app")
```

**`name` is not unique.** Two committees genuinely might both be "Sarbojanin", and
the slug is what has to be distinct.

**`SlugField`** — a `CharField` with a built-in slug validator. The custom
validator runs *in addition*, tightening it to DNS rules.

**`validators=[...]`** takes a list, so several can stack.

**`help_text`** appears in the admin and in the generated OpenAPI schema. It is
the cheapest documentation there is, and it lives next to the thing it describes.

```python
    custom_domain = models.CharField(max_length=253, blank=True, unique=True, null=True,
                                     help_text="Unused in v1 (FR-249)")
```

**`max_length=253`** — the maximum length of a full domain name, as opposed to the
63 of a single label.

**`null=True` on a text field**, which the rest of the project avoids. It is
forced by `unique=True`: Postgres treats every `NULL` as distinct, so many pandals
can have no custom domain. With `""` instead, the second one would collide.

**Built now, unused now.** Adding a nullable column later is a cheap migration, so
this is arguably premature — it is here because the shape of the feature is
already decided and a column is one line.

### Contact and location

```python
    committee_name = models.CharField(max_length=180, blank=True)
    contact_name = models.CharField(max_length=120, blank=True)
    contact_phone = models.CharField(max_length=20, blank=True)
    contact_email = models.EmailField(blank=True)
```

All optional, because a pandal record is created before all of this is known.
`contact_phone` is a plain `CharField` and is deliberately *not* normalised — it
is a display string for staff to ring, not an identity.

```python
    city = models.ForeignKey("geo.City", on_delete=models.PROTECT, related_name="pandals")
    locality = models.ForeignKey("geo.Locality", null=True, blank=True,
                                 on_delete=models.SET_NULL, related_name="pandals")
    address = models.TextField(blank=True)
    latitude = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)
    longitude = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)
```

**`city` is required and `PROTECT`ed**; **`locality` is optional and `SET_NULL`**.
Every pandal is in a city; not every one has a known neighbourhood.

**`DecimalField` for coordinates, not `FloatField`.** `max_digits=9,
decimal_places=6` gives three digits before the point (enough for ±180) and six
after, which is about 11 centimetres of precision. Exact decimal storage means a
coordinate written is the coordinate read.

**`TextField` for the address** because a real Kolkata address is longer than you
expect and truncating it helps nobody.

### Theme

```python
    theme_name = models.CharField(max_length=120, blank=True)
    theme_name_local = models.CharField(max_length=120, blank=True,
                                        help_text="The theme in Bengali, e.g. প্রথা")
```

Two columns rather than a JSON blob, because there are exactly two and both are
shown together on the hero block. Django and Postgres store text as UTF-8
throughout, so Bengali needs no special handling.

### Capabilities

```python
    sells_passes = models.BooleanField(default=False)
    accepts_donations = models.BooleanField(default=True)
    offers_services = models.BooleanField(default=False)
```

**Three booleans, not one `TextChoices`**, because they are independent — a pandal
may do any combination.

**The defaults encode the product decision.** A new pandal takes donations and
nothing else, which is the v1 shape. `sells_passes` defaults to `False` and there
is a test asserting it, so the switch ships off.

**Not derived.** Working this out from whether related rows exist would mean a
subquery on the hottest read in the system, and it could not distinguish "sells
nothing this week" from "never sells".

### Lifecycle

```python
    publication_status = models.CharField(max_length=16, choices=PublicationStatus.choices,
                                          default=PublicationStatus.DRAFT)
    published_at = models.DateTimeField(null=True, blank=True)
    opens_on = models.DateField(null=True, blank=True)
    closes_on = models.DateField(null=True, blank=True)
    is_active = models.BooleanField(default=True)
```

**`max_length=16`** fits the longest value, `"pending_review"` at 14.

**Two independent lifecycles.** `publication_status` is editorial — is the page
live? `opens_on`/`closes_on` are operational — is the pandal receiving visitors?
A page can be published in September for a pandal that opens in October.

**`DateField`, not `DateTimeField`.** A pandal opens on a day, not at an instant.
Storing a time you do not have invites a fake one.

**`is_active`** as a soft delete. Deleting a pandal would cascade through its page
blocks and be blocked by its donations; deactivating hides it and keeps the
history.

### SEO

```python
    seo_title = models.CharField(max_length=180, blank=True)
    seo_description = models.CharField(max_length=320, blank=True)
    og_image = models.ImageField(upload_to="pandals/og/", null=True, blank=True)
```

**`max_length` chosen from the medium.** Google truncates titles around 60
characters and descriptions around 160; the limits here are generous but bounded.

**`ImageField`** is a `FileField` that also validates the upload is an image and
exposes `.width` and `.height`. It requires Pillow, which is why that dependency
exists.

**`upload_to="pandals/og/"`** — the subdirectory under `MEDIA_ROOT`. The database
column stores a path string, not the bytes.

**`null=True` on a file field** is the conventional exception: the column holds a
path, and no path is genuinely `NULL`.

### Meta

```python
    class Meta:
        ordering = ("name",)
        indexes = [models.Index(fields=["city", "publication_status"])]
```

**One composite index** for the browse query — published pandals in a city.
Column order matters: this index also serves a query filtered by `city` alone, but
not one by `publication_status` alone.

### Properties

```python
    @property
    def is_published(self) -> bool:
        return self.publication_status == self.PublicationStatus.PUBLISHED and self.is_active
```

Both conditions in one place, so no caller can check one and forget the other.

Being a property, it cannot be used in a query — `filter(is_published=True)` will
not work, because the database has never heard of it. A queryset method or a
custom manager would be the answer if that were needed often.

```python
    @property
    def canonical_host(self) -> str:
        return self.custom_domain or f"{self.slug}.{settings.SITE_DOMAIN}"

    @property
    def canonical_url(self) -> str:
        return f"https://{self.canonical_host}"
```

**`or`** gives the fallback: a custom domain when set, otherwise the subdomain.
This works because `""` is falsy, so the blank default falls through correctly.

**Derived, never stored.** There is no way for these to drift out of step with the
slug.

---

## `PandalDomainAlias`

```python
class PandalDomainAlias(BaseModel):
    host = models.CharField(max_length=253, unique=True)
    pandal = models.ForeignKey(Pandal, on_delete=models.CASCADE, related_name="domain_aliases")

    class Meta:
        verbose_name_plural = "pandal domain aliases"
```

**The full host, not the slug.** Storing `"ballygunge-cultural-2025.edurgapuja.app"`
rather than a bare label means custom domains can also be aliased later, with no
schema change.

**`unique=True`** — one host resolves to one pandal, and the database enforces it
rather than a check in the lookup.

**`CASCADE`** — aliases for a deleted pandal are dead weight.

**`verbose_name_plural`** because Django would otherwise render "pandal domain
aliass".

---

## `PandalBrand`

```python
class PandalBrand(BaseModel):
    pandal = models.OneToOneField(Pandal, on_delete=models.CASCADE, related_name="brand")
    primary_colour = models.CharField(max_length=9, default="#B45F1E")
    accent_colour = models.CharField(max_length=9, default="#E0A66A")
    surface_colour = models.CharField(max_length=9, default="#FBF3E8")
    ink_colour = models.CharField(max_length=9, default="#3A1D0C")
    display_font = models.CharField(max_length=80, blank=True)
    body_font = models.CharField(max_length=80, blank=True)
    logo = models.ImageField(upload_to="pandals/logo/", null=True, blank=True)
    mark = models.ImageField(upload_to="pandals/mark/", null=True, blank=True)
```

**`OneToOneField`** — a `ForeignKey` with `unique=True` on the column, so one
pandal has at most one brand. The accessor is singular, `pandal.brand`, and
returns the object itself rather than a manager.

**Why a separate table at all**, rather than eight more columns on `Pandal`?
Because branding is edited by a different screen at a different time, and it keeps
the hot `Pandal` row narrower. The cost is a join — which is why the page query
will use `select_related("brand")`.

**`max_length=9`** — `#RRGGBBAA` is nine characters, so an alpha channel fits.

**Real defaults, not blanks.** A pandal with no brand set still renders in
sensible colours rather than unstyled.

**Fonts as names, not files.** The web tier maps a name to a webfont; storing the
file here would mean serving fonts from the API.

---

## `PageBlock`

```python
class PageBlock(BaseModel):
    class Kind(models.TextChoices):
        HERO = "hero", "Hero"
        MARQUEE = "marquee", "Marquee"
        ABOUT = "about", "About"
        DONOR_PASS = "donor_pass", "Donor Pass"
        DONATE = "donate", "Donate"
        SERVICES = "services", "Value-Added Services"
        VISIT = "visit", "Plan Your Visit"
        CLOSING_CTA = "closing_cta", "Closing call to action"
        FOOTER = "footer", "Footer"
```

Nine kinds, taken from the reference landing page. **`DONOR_PASS` exists in v1
even though no pandal can use it yet** — when the pass switch is turned on, the
block becomes available with no migration.

```python
    pandal = models.ForeignKey(Pandal, on_delete=models.CASCADE, related_name="blocks")
    kind = models.CharField(max_length=16, choices=Kind.choices)
    language = models.CharField(max_length=5, choices=settings.LANGUAGES, default="en")
    sort_order = models.PositiveSmallIntegerField(default=0)
    is_visible = models.BooleanField(default=True)
    content = models.JSONField(default=dict, blank=True)
```

**`language` on the block**, not on the pandal. Translation happens per block, so
a page can be fully translated into Bengali while its footer still falls back to
English.

**`sort_order`** — the page is an ordered list, and the order is data. Reordering
is an admin drag, not a deployment.

**`is_visible`** to hide a block without deleting its content. Deleting would lose
the copy.

**`content = models.JSONField(default=dict)`** — the deliberate exception to
"a column per field". A hero block and a footer share no fields, and modelling
nine block types as columns would mean a table of mostly-empty columns or nine
tables.

**`default=dict`**, the function. `default={}` would share one dictionary across
every instance — Django raises a system check error if you try, but the bug is
worth recognising.

```python
    class Meta:
        ordering = ("sort_order",)
        constraints = [
            models.UniqueConstraint(fields=["pandal", "kind", "language"],
                                    name="uniq_block_per_pandal_kind_language")
        ]
```

**One block of each kind per pandal per language.** Enforced by the database, not
by a check in the view — two simultaneous requests would both pass an
`if not exists()` test.

---

## `VisitFact`

```python
class VisitFact(BaseModel):
    pandal = models.ForeignKey(Pandal, on_delete=models.CASCADE, related_name="visit_facts")
    label = models.CharField(max_length=80)
    value = models.CharField(max_length=200)
    sort_order = models.PositiveSmallIntegerField(default=0)

    class Meta:
        ordering = ("sort_order",)
```

**Rows, not columns.** The reference page shows four cards — Pandal Location, Puja
Dates, Darshan Timings, Visitor Information. Four columns named after them would
work until a pandal wanted a fifth for "Nearest Metro", which would then be a
migration.

Label-and-value rows let a committee say something nobody anticipated, which is
the right trade for content that is purely display. The cost is that you cannot
query it — `filter(parking="free")` is impossible — and that is acceptable because
nothing ever will.
