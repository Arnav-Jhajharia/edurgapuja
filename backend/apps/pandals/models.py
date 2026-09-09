from django.conf import settings
from django.db import models

from apps.common.models import BaseModel

from .validators import validate_subdomain


class Pandal(BaseModel):
    """A puja committee's pandal, and the site it is served on.

    Carries no capacity: passes are out of v1 scope, and the pandal-day
    inventory arrives with them (Scope §2).
    """

    class PublicationStatus(models.TextChoices):
        DRAFT = "draft", "Draft"
        PENDING_REVIEW = "pending_review", "Pending review"
        PUBLISHED = "published", "Published"

    name = models.CharField(max_length=140)
    slug = models.SlugField(max_length=63, unique=True, validators=[validate_subdomain],
                            help_text="Also the subdomain: <slug>.edurgapuja.app")
    custom_domain = models.CharField(max_length=253, blank=True, unique=True, null=True,
                                     help_text="Unused in v1 (FR-249)")

    committee_name = models.CharField(max_length=180, blank=True)
    contact_name = models.CharField(max_length=120, blank=True)
    contact_phone = models.CharField(max_length=20, blank=True)
    contact_email = models.EmailField(blank=True)

    city = models.ForeignKey("geo.City", on_delete=models.PROTECT, related_name="pandals")
    locality = models.ForeignKey("geo.Locality", null=True, blank=True,
                                 on_delete=models.SET_NULL, related_name="pandals")
    address = models.TextField(blank=True)
    latitude = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)
    longitude = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)

    theme_name = models.CharField(max_length=120, blank=True)
    theme_name_local = models.CharField(max_length=120, blank=True,
                                        help_text="The theme in Bengali, e.g. প্রথা")

    # Capabilities — what this pandal actually does (FR-045). Explicit columns,
    # not derived, so a pandal with nothing on sale this week is still
    # distinguishable from one that never sells.
    sells_passes = models.BooleanField(default=False)
    accepts_donations = models.BooleanField(default=True)
    offers_services = models.BooleanField(default=False)

    publication_status = models.CharField(max_length=16, choices=PublicationStatus.choices,
                                          default=PublicationStatus.DRAFT)
    published_at = models.DateTimeField(null=True, blank=True)
    opens_on = models.DateField(null=True, blank=True)
    closes_on = models.DateField(null=True, blank=True)
    is_active = models.BooleanField(default=True)

    # SEO — load-bearing, because a WhatsApp forward is how a page actually spreads.
    seo_title = models.CharField(max_length=180, blank=True)
    seo_description = models.CharField(max_length=320, blank=True)
    og_image = models.ImageField(upload_to="pandals/og/", null=True, blank=True)

    class Meta:
        ordering = ("name",)
        indexes = [models.Index(fields=["city", "publication_status"])]

    def __str__(self) -> str:
        return self.name

    @property
    def is_published(self) -> bool:
        return self.publication_status == self.PublicationStatus.PUBLISHED and self.is_active

    @property
    def canonical_host(self) -> str:
        return self.custom_domain or f"{self.slug}.{settings.SITE_DOMAIN}"

    @property
    def canonical_url(self) -> str:
        return f"https://{self.canonical_host}"


class PandalDomainAlias(BaseModel):
    """An old subdomain, kept alive forever as a permanent redirect (FR-248).

    A pandal's name will already be on a banner and in WhatsApp forwards by the
    time anyone wants to change it.
    """

    host = models.CharField(max_length=253, unique=True)
    pandal = models.ForeignKey(Pandal, on_delete=models.CASCADE, related_name="domain_aliases")

    class Meta:
        verbose_name_plural = "pandal domain aliases"

    def __str__(self) -> str:
        return f"{self.host} → {self.pandal.slug}"


class PandalBrand(BaseModel):
    """A pandal page is that committee's brand, not a platform skin (FR-050b)."""

    pandal = models.OneToOneField(Pandal, on_delete=models.CASCADE, related_name="brand")
    primary_colour = models.CharField(max_length=9, default="#B45F1E")
    accent_colour = models.CharField(max_length=9, default="#E0A66A")
    surface_colour = models.CharField(max_length=9, default="#FBF3E8")
    ink_colour = models.CharField(max_length=9, default="#3A1D0C")
    display_font = models.CharField(max_length=80, blank=True)
    body_font = models.CharField(max_length=80, blank=True)
    logo = models.ImageField(upload_to="pandals/logo/", null=True, blank=True)
    mark = models.ImageField(upload_to="pandals/mark/", null=True, blank=True)

    def __str__(self) -> str:
        return f"brand · {self.pandal.name}"


class PageBlock(BaseModel):
    """The landing page is an ordered list of blocks (FR-050a).

    Turning a capability on adds a block; it does not redesign the page. Content
    is JSON shaped by `kind`, because every block on the reference page carries
    bespoke prose rather than a fixed field set.
    """

    class Kind(models.TextChoices):
        HERO = "hero", "Hero"
        MARQUEE = "marquee", "Marquee"
        ABOUT = "about", "About"
        PASSES = "passes", "Passes"
        DONATE = "donate", "Donate"
        SERVICES = "services", "Value-Added Services"
        VISIT = "visit", "Plan Your Visit"
        CLOSING_CTA = "closing_cta", "Closing call to action"
        FOOTER = "footer", "Footer"

    pandal = models.ForeignKey(Pandal, on_delete=models.CASCADE, related_name="blocks")
    kind = models.CharField(max_length=16, choices=Kind.choices)
    language = models.CharField(max_length=5, choices=settings.LANGUAGES, default="en")
    sort_order = models.PositiveSmallIntegerField(default=0)
    is_visible = models.BooleanField(default=True)
    content = models.JSONField(default=dict, blank=True)

    class Meta:
        ordering = ("sort_order",)
        constraints = [
            models.UniqueConstraint(fields=["pandal", "kind", "language"],
                                    name="uniq_block_per_pandal_kind_language")
        ]

    def __str__(self) -> str:
        return f"{self.pandal.slug} · {self.kind}"


class VisitFact(BaseModel):
    """The 'Plan Your Visit' cards — label and value, so a pandal can say
    something we did not anticipate."""

    pandal = models.ForeignKey(Pandal, on_delete=models.CASCADE, related_name="visit_facts")
    label = models.CharField(max_length=80)
    value = models.CharField(max_length=200)
    sort_order = models.PositiveSmallIntegerField(default=0)

    class Meta:
        ordering = ("sort_order",)

    def __str__(self) -> str:
        return f"{self.label}: {self.value}"


class Gate(BaseModel):
    """A named scanning position — 'Gate 1', 'Gate 2', 'Ticket Desk'.

    Belongs to the pandal rather than to the pass system: it is a physical
    entrance that exists whether or not anything is scanned at it.
    """

    pandal = models.ForeignKey(Pandal, on_delete=models.CASCADE, related_name="gates")
    name = models.CharField(max_length=60)
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ("pandal__name", "name")
        constraints = [
            models.UniqueConstraint(fields=["pandal", "name"], name="uniq_gate_name_per_pandal")
        ]

    def __str__(self) -> str:
        return f"{self.pandal.name} · {self.name}"


class Volunteer(BaseModel):
    """Gate staff. Deactivating one immediately ends their ability to scan."""

    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE,
                             related_name="volunteer_postings")
    pandal = models.ForeignKey(Pandal, on_delete=models.CASCADE, related_name="volunteers")
    gate = models.ForeignKey(Gate, null=True, blank=True, on_delete=models.SET_NULL,
                             related_name="volunteers")
    is_active = models.BooleanField(default=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["user", "pandal"], name="uniq_volunteer_per_pandal")
        ]

    def __str__(self) -> str:
        return f"{self.user} @ {self.pandal.name}"
