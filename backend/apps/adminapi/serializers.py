import re

from django.utils.text import slugify
from rest_framework import serializers

from apps.accounts.models import AdminMembership, User
from apps.accounts.serializers import PhoneField
from apps.donations.models import Donation, DonationLink, DonationOffering
from apps.geo.models import City, Locality
from apps.ops.models import LostItem, PandalLiveStatus, SupportRequest
from apps.pandals import blocks
from apps.pandals.models import Gate, PageBlock, Pandal, PandalBrand, VisitFact, Volunteer
from apps.passes import inventory as pass_inventory
from apps.passes.models import (
    PandalDayCapacity,
    Pass,
    PassCategory,
    PassConfig,
    PassProduct,
    ScanEvent,
)
from apps.services.models import (
    Service,
    ServiceBooking,
    ServiceDayCapacity,
    ServiceField,
)
from apps.sponsorship.models import (
    BrandingCreative,
    Organisation,
    Pool,
    PoolAllocation,
    PoolIssuance,
    SponsorshipPackage,
)


class AdminMeSerializer(serializers.Serializer):
    """What the panel needs to decide which of the four to render."""

    id = serializers.UUIDField()
    full_name = serializers.CharField()
    phone = serializers.CharField()
    roles = serializers.ListField(child=serializers.CharField())
    pandals = serializers.ListField(child=serializers.DictField())
    organisations = serializers.ListField(child=serializers.DictField())


class AdminLocalitySerializer(serializers.ModelSerializer):
    # `city` is write-only: read back nested under a city it would be noise, but
    # creating one needs to say which city it is in.
    city = serializers.PrimaryKeyRelatedField(queryset=City.objects.all(), write_only=True)

    class Meta:
        model = Locality
        fields = ("id", "name", "city")


class AdminCitySerializer(serializers.ModelSerializer):
    """Cities and their localities, so onboarding is a picker rather than a
    request to go and find two UUIDs."""

    state_name = serializers.CharField(source="state.name", read_only=True)
    localities = AdminLocalitySerializer(many=True, read_only=True)

    class Meta:
        model = City
        fields = ("id", "name", "state", "state_name", "localities")


class AdminPandalSerializer(serializers.ModelSerializer):
    canonical_url = serializers.CharField(read_only=True)
    city_name = serializers.CharField(source="city.name", read_only=True)
    locality_name = serializers.CharField(source="locality.name", read_only=True,
                                          default="")
    # Writable when onboarding, frozen afterwards — see validate_slug. It was
    # read-only outright, which meant a created pandal got an empty slug and the
    # second one collided on it.
    slug = serializers.SlugField(max_length=63, required=False)

    class Meta:
        model = Pandal
        fields = ("id", "name", "slug", "canonical_url", "committee_name", "contact_name",
                  "contact_phone", "contact_email", "city", "city_name", "locality",
                  "locality_name", "address", "theme_name", "theme_name_local",
                  "sells_passes", "accepts_donations", "offers_services",
                  "publication_status", "opens_on", "closes_on",
                  "is_active", "seo_title", "seo_description")
        read_only_fields = ("id", "canonical_url")

    def validate_slug(self, value):
        """The slug is the subdomain, so it is set once and then frozen.

        Changing it moves the committee's whole site to a new address. That is a
        real operation with a redirect attached (FR-248), not a field edit, so
        it does not happen by tabbing through this form.
        """
        if self.instance and value != self.instance.slug:
            raise serializers.ValidationError(
                "A pandal's address cannot be changed here — it is a subdomain people "
                "have already been given. Ask for a rename, which keeps the old one working."
            )
        return value

    def validate(self, attrs):
        if self.instance is None and not attrs.get("slug"):
            attrs["slug"] = self._free_slug(attrs.get("name", ""))
        return attrs

    @staticmethod
    def _free_slug(name: str) -> str:
        """Derive one from the name, and make it unique rather than colliding."""
        base = slugify(name)[:55] or "pandal"
        candidate, n = base, 2
        while Pandal.objects.filter(slug=candidate).exists():
            candidate = f"{base}-{n}"
            n += 1
        return candidate


HEX = re.compile(r"^#(?:[0-9a-fA-F]{3}|[0-9a-fA-F]{6}|[0-9a-fA-F]{8})$")


class AdminBrandSerializer(serializers.ModelSerializer):
    """The committee's own palette, not a platform skin (FR-050b)."""

    class Meta:
        model = PandalBrand
        fields = ("primary_colour", "accent_colour", "surface_colour", "ink_colour",
                  "display_font", "body_font")

    def validate(self, attrs):
        # These land in the page as CSS custom properties. A typo is not a
        # broken field, it is a page that renders with no colour at all — and
        # the committee sees it before anybody tells them.
        problems = {
            key: "Use a hex colour like #B45F1E."
            for key, value in attrs.items()
            if key.endswith("_colour") and value and not HEX.match(value)
        }
        if problems:
            raise serializers.ValidationError(problems)
        return attrs


class AdminPageBlockSerializer(serializers.ModelSerializer):
    name = serializers.SerializerMethodField()

    class Meta:
        model = PageBlock
        fields = ("id", "pandal", "kind", "name", "language", "sort_order",
                  "is_visible", "content")
        read_only_fields = ("id",)

    def get_name(self, block) -> str:
        return blocks.BY_KIND.get(block.kind, {}).get("name", block.kind)

    def validate(self, attrs):
        """A block may only hold what its kind renders.

        Content nobody renders is content nobody maintains: it survives a
        redesign, looks fine in the database, and quietly means nothing.
        """
        kind = attrs.get("kind", getattr(self.instance, "kind", None))
        content = attrs.get("content")
        if kind and content is not None:
            unknown = set(content) - blocks.allowed_keys(kind)
            if unknown:
                raise serializers.ValidationError({
                    "content": f"The {kind} block does not have: {', '.join(sorted(unknown))}.",
                })
        return attrs


class BlockFieldSchemaSerializer(serializers.Serializer):
    key = serializers.CharField()
    label = serializers.CharField()
    kind = serializers.CharField()
    help_text = serializers.CharField(allow_blank=True)


class BlockSchemaSerializer(serializers.Serializer):
    """What each block is made of, so the editor builds itself."""

    kind = serializers.CharField()
    name = serializers.CharField()
    description = serializers.CharField()
    fields = BlockFieldSchemaSerializer(many=True)


class AdminVisitFactSerializer(serializers.ModelSerializer):
    class Meta:
        model = VisitFact
        fields = ("id", "pandal", "label", "value", "sort_order")


class AdminDonationOfferingSerializer(serializers.ModelSerializer):
    class Meta:
        model = DonationOffering
        fields = ("id", "pandal", "amount_paise", "label", "description",
                  "sort_order", "is_active")


class AdminDonationLinkSerializer(serializers.ModelSerializer):
    path = serializers.CharField(read_only=True)
    donation_count = serializers.IntegerField(read_only=True)

    class Meta:
        model = DonationLink
        fields = ("id", "pandal", "suggested_amount_paise", "purpose", "token",
                  "path", "is_active", "donation_count", "created_at")
        read_only_fields = ("id", "token", "path", "created_at")


class AdminDonationSerializer(serializers.ModelSerializer):
    pandal_name = serializers.CharField(source="pandal.name", read_only=True)
    offering_label = serializers.CharField(source="offering.label", default="", read_only=True)
    is_anonymous = serializers.BooleanField(read_only=True)

    class Meta:
        model = Donation
        fields = ("id", "pandal", "pandal_name", "donor_name", "is_anonymous", "message",
                  "amount_paise", "offering_label", "received_at", "created_at")


class TemplateFieldSerializer(serializers.Serializer):
    key = serializers.CharField()
    label = serializers.CharField()
    kind = serializers.CharField()
    required = serializers.BooleanField()
    is_sensitive = serializers.BooleanField()
    help_text = serializers.CharField(allow_blank=True)
    options = serializers.ListField(child=serializers.CharField())


class ServiceTemplateSerializer(serializers.Serializer):
    """A starting point, not a type. Nothing branches on which one was used."""

    slug = serializers.CharField()
    name = serializers.CharField()
    description = serializers.CharField()
    requires_capacity = serializers.BooleanField()
    fields = TemplateFieldSerializer(many=True)


class AdminServiceFieldSerializer(serializers.ModelSerializer):
    class Meta:
        model = ServiceField
        fields = ("id", "service", "key", "label", "kind", "required", "help_text",
                  "options", "is_sensitive", "sort_order")

    def validate(self, attrs):
        kind = attrs.get("kind", getattr(self.instance, "kind", ServiceField.Kind.TEXT))
        options = attrs.get("options", getattr(self.instance, "options", []))
        if kind == ServiceField.Kind.SELECT and not options:
            raise serializers.ValidationError(
                {"options": "A 'choose one' question needs at least one option."}
            )
        return attrs


class AdminServiceSerializer(serializers.ModelSerializer):
    pandal_name = serializers.CharField(source="pandal.name", read_only=True)
    form = AdminServiceFieldSerializer(source="fields", many=True, read_only=True)
    #: Applied on create only, and only ever additively — see `templates.py`.
    template = serializers.CharField(write_only=True, required=False, allow_blank=True)

    class Meta:
        model = Service
        fields = ("id", "pandal", "pandal_name", "type", "name", "slug", "description",
                  "price_paise", "max_per_booking", "requires_capacity", "is_active",
                  "sort_order", "form", "template")


class AdminServiceDaySerializer(serializers.ModelSerializer):
    available = serializers.SerializerMethodField()

    class Meta:
        model = ServiceDayCapacity
        fields = ("id", "date", "capacity", "issued_count", "available", "is_open")
        read_only_fields = ("id", "issued_count")

    def get_available(self, day) -> int:
        from apps.services import inventory

        return inventory.available(day)


class AdminServiceBookingSerializer(serializers.ModelSerializer):
    service_name = serializers.CharField(source="service.name", read_only=True)
    pandal_name = serializers.CharField(source="service.pandal.name", read_only=True)
    date = serializers.DateField(source="day.date", read_only=True)

    class Meta:
        model = ServiceBooking
        fields = ("id", "service_name", "pandal_name", "date", "quantity",
                  "status", "details", "confirmed_at", "created_at")


class AdminLiveStatusSerializer(serializers.ModelSerializer):
    age_seconds = serializers.IntegerField(read_only=True)

    class Meta:
        model = PandalLiveStatus
        fields = ("estimated_wait_minutes", "crowd_level", "note", "updated_at", "age_seconds")


class AdminLostItemSerializer(serializers.ModelSerializer):
    pandal_name = serializers.CharField(source="pandal.name", read_only=True)

    class Meta:
        model = LostItem
        fields = ("id", "pandal", "pandal_name", "item", "location", "contact_phone",
                  "status", "resolved_at", "created_at")


class AdminSupportRequestSerializer(serializers.ModelSerializer):
    pandal_name = serializers.CharField(source="pandal.name", default="", read_only=True)

    class Meta:
        model = SupportRequest
        fields = ("id", "pandal", "pandal_name", "name", "contact_phone", "subject",
                  "message", "status", "resolved_at", "created_at")


class AdminVolunteerSerializer(serializers.ModelSerializer):
    name = serializers.CharField(source="user.full_name", read_only=True)
    phone = serializers.CharField(source="user.phone", read_only=True)
    gate_name = serializers.CharField(source="gate.name", default="", read_only=True)

    class Meta:
        model = Volunteer
        fields = ("id", "pandal", "user", "name", "phone", "gate", "gate_name", "is_active")


class AdminGateSerializer(serializers.ModelSerializer):
    class Meta:
        model = Gate
        fields = ("id", "pandal", "name", "is_active")


# --- sponsorship ---------------------------------------------------------

class AdminOrganisationSerializer(serializers.ModelSerializer):
    is_sub_sponsor = serializers.BooleanField(read_only=True)
    passes_held = serializers.SerializerMethodField()
    paid_to_parent_paise = serializers.SerializerMethodField()

    class Meta:
        model = Organisation
        fields = ("id", "name", "slug", "parent", "is_sub_sponsor", "contact_name",
                  "contact_phone", "contact_email", "price_per_pass_paise",
                  "passes_held", "paid_to_parent_paise", "is_active")

    def get_passes_held(self, org) -> int:
        return sum(p.available for p in org.pools.all())

    def get_paid_to_parent_paise(self, org) -> int:
        """What this organisation has actually paid its sponsor."""
        from apps.sponsorship.models import PoolTransfer

        rows = PoolTransfer.objects.filter(to_pool__organisation=org,
                                           status=PoolTransfer.Status.COMPLETED)
        return sum(t.total_paise for t in rows)


class AdminIssuanceSerializer(serializers.ModelSerializer):
    organisation_name = serializers.CharField(source="pool.organisation.name", read_only=True)
    pandal_name = serializers.CharField(source="pool.pandal.name", read_only=True)

    class Meta:
        model = PoolIssuance
        fields = ("id", "pool", "organisation_name", "pandal_name", "quantity",
                  "distributed_to", "note", "created_at")


class BuyPassesSerializer(serializers.Serializer):
    pandal = serializers.UUIDField()
    quantity = serializers.IntegerField(min_value=1)


class AdminPackageSerializer(serializers.ModelSerializer):
    # A package belongs to one pandal, and a sponsor may hold one at several
    # pandals at once — so the name alone ("Gold Sponsor") does not identify it.
    pandal_name = serializers.CharField(source="pandal.name", read_only=True)

    class Meta:
        model = SponsorshipPackage
        fields = ("id", "pandal", "pandal_name", "name", "slug", "value_paise",
                  "pass_count", "banner_placements", "benefits", "valid_from",
                  "valid_to", "is_active")


class AdminPassCategorySerializer(serializers.ModelSerializer):
    """A pandal's own names for who a holder is — Sponsor, VIP, Para Pass,
    Senior Citizen, Donor, or anything else it invents (D4). No migration."""

    class Meta:
        model = PassCategory
        fields = ("id", "pandal", "name", "slug", "description", "is_active", "sort_order")


class AdminPassConfigSerializer(serializers.ModelSerializer):
    category_name = serializers.CharField(source="category.name", read_only=True)
    product_display = serializers.CharField(source="get_product_display", read_only=True)

    class Meta:
        model = PassConfig
        fields = ("id", "pandal", "category", "category_name", "product", "product_display",
                  "from_date", "to_date", "from_time", "to_time", "price_paise",
                  "max_party_size", "slot_cap", "is_active")

    def validate(self, attrs):
        product = attrs.get("product", getattr(self.instance, "product", None))
        if product == PassProduct.CITY and (attrs.get("from_time") or attrs.get("to_time")):
            # The database refuses this too; saying it here names the field.
            raise serializers.ValidationError(
                {"from_time": "A City Pass has a date but no time."}
            )
        return attrs


class AdminPandalDaySerializer(serializers.ModelSerializer):
    available = serializers.SerializerMethodField()

    class Meta:
        model = PandalDayCapacity
        fields = ("id", "date", "capacity", "issued_count", "available", "is_open")

    def get_available(self, day) -> int:
        return pass_inventory.available(day)


class AdminPassSerializer(serializers.ModelSerializer):
    category_name = serializers.CharField(source="category.name", read_only=True)
    holder_phone = serializers.CharField(source="holder.phone", read_only=True, default="")
    legs = serializers.SerializerMethodField()

    class Meta:
        model = Pass
        fields = ("id", "pass_code", "product", "category", "category_name", "party_size",
                  "status", "source", "holder_phone", "issued_at", "legs")

    def get_legs(self, issued) -> list[dict]:
        return [
            {"id": str(leg.id), "pandal_name": leg.pandal.name, "visit_date": leg.visit_date,
             "state": leg.state, "admitted_at": leg.admitted_at}
            for leg in issued.legs.all()
        ]


class AdminScanEventSerializer(serializers.ModelSerializer):
    gate_name = serializers.CharField(source="gate.name", read_only=True)
    pass_code = serializers.CharField(source="leg.issued_pass.pass_code", read_only=True,
                                      default="")
    volunteer_name = serializers.CharField(source="volunteer.user.full_name", read_only=True,
                                           default="")

    class Meta:
        model = ScanEvent
        fields = ("id", "gate", "gate_name", "pass_code", "result", "scanned_at",
                  "received_at", "device_id", "volunteer_name", "override_reason")


class PassCategoryCountSerializer(serializers.Serializer):
    category = serializers.CharField()
    count = serializers.IntegerField()


class PassSummarySerializer(serializers.Serializer):
    """Typed so the generated client knows the shape of the Passes screen."""

    capacity = serializers.IntegerField()
    issued = serializers.IntegerField()
    available = serializers.IntegerField()
    legs_pending = serializers.IntegerField()
    legs_visited = serializers.IntegerField()
    revenue_paise = serializers.IntegerField()
    scans_admitted = serializers.IntegerField()
    scans_refused = serializers.IntegerField()
    by_category = PassCategoryCountSerializer(many=True)


class AdminStaffSerializer(serializers.ModelSerializer):
    """Who can sign in to which console.

    Sign-in is by mobile and one-time code, so granting access *is* naming a
    phone number — there is no credential to generate, send or ever display
    (FR-237). The number is the invitation.
    """

    phone = PhoneField(write_only=True)
    user_phone = serializers.CharField(source="user.phone", read_only=True)
    user_name = serializers.CharField(source="user.full_name", read_only=True)
    pandal_name = serializers.CharField(source="pandal.name", read_only=True, default="")
    organisation_name = serializers.CharField(source="organisation.name", read_only=True,
                                              default="")
    role_display = serializers.CharField(source="get_role_display", read_only=True)

    class Meta:
        model = AdminMembership
        fields = ("id", "phone", "user_phone", "user_name", "role", "role_display",
                  "pandal", "pandal_name", "organisation", "organisation_name", "is_active")

    def create(self, validated):
        phone = validated.pop("phone")
        # An account may not exist yet, and that is the ordinary case: most
        # committee members have never used the app. Creating it here means
        # their first sign-in works rather than failing at the code screen.
        user, _ = User.objects.get_or_create(phone=phone)
        membership, _ = AdminMembership.objects.update_or_create(
            user=user, role=validated["role"],
            pandal=validated.get("pandal"), organisation=validated.get("organisation"),
            defaults={"is_active": True},
        )
        return membership


class AdminUserSerializer(serializers.ModelSerializer):
    """The Super Admin's directory of everyone with an account.

    Read-only and deliberately thin: a platform operator needs to find a person
    and see what authority they hold, not to browse donor histories. Anything
    beyond that belongs behind a support request with a reason attached.
    """

    full_name = serializers.CharField(read_only=True)
    grants = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = ("id", "phone", "full_name", "email", "phone_verified_at",
                  "date_joined", "is_active", "grants")

    def get_grants(self, user) -> list[str]:
        return [
            f"{m.get_role_display()}"
            + (f" · {m.pandal.name}" if m.pandal_id
               else f" · {m.organisation.name}" if m.organisation_id else "")
            for m in user.memberships.all()
        ]


class AdminPoolSerializer(serializers.ModelSerializer):
    organisation_name = serializers.CharField(source="organisation.name", read_only=True)
    pandal_name = serializers.CharField(source="pandal.name", read_only=True)
    available = serializers.IntegerField(read_only=True)

    class Meta:
        model = Pool
        fields = ("id", "organisation", "organisation_name", "pandal", "pandal_name",
                  "granted", "transferred_out", "issued", "available")


class AdminAllocationSerializer(serializers.ModelSerializer):
    organisation_name = serializers.CharField(source="organisation.name", read_only=True)
    pandal_name = serializers.CharField(source="pandal.name", read_only=True)
    package_name = serializers.CharField(source="package.name", default="", read_only=True)

    class Meta:
        model = PoolAllocation
        fields = ("id", "pandal", "pandal_name", "organisation", "organisation_name",
                  "package", "package_name", "pass_count", "value_paise", "status",
                  "responded_at", "created_at")
        read_only_fields = ("id", "status", "responded_at", "created_at")


class AdminCreativeSerializer(serializers.ModelSerializer):
    organisation_name = serializers.CharField(source="organisation.name", read_only=True)
    pandal_name = serializers.CharField(source="pandal.name", read_only=True)
    placement_name = serializers.CharField(source="placement.name", read_only=True)

    class Meta:
        model = BrandingCreative
        fields = ("id", "organisation", "organisation_name", "pandal", "pandal_name",
                  "placement", "placement_name", "name", "target_url", "start_date",
                  "end_date", "price_paise", "status", "rejection_reason", "created_at")
        read_only_fields = ("id", "status", "created_at")


class TransferSerializer(serializers.Serializer):
    to_organisation = serializers.UUIDField()
    quantity = serializers.IntegerField(min_value=1)
    price_per_pass_paise = serializers.IntegerField(min_value=0, default=0)


class IssueSerializer(serializers.Serializer):
    quantity = serializers.IntegerField(min_value=1)
    distributed_to = serializers.CharField(max_length=180, required=False, allow_blank=True)
    # Given a date, the issuance mints real passes and takes the pandal's
    # capacity for that day. Without one it only moves the pool's counter, which
    # is what a sponsor doing its own paper distribution wants.
    visit_date = serializers.DateField(required=False, allow_null=True)
    category = serializers.UUIDField(required=False, allow_null=True)


# --- dashboard shapes ----------------------------------------------------
# These views assemble figures rather than serialise a model, but they still
# need a declared response or every generated client types them as `any`.

class RevenueLineSerializer(serializers.Serializer):
    kind = serializers.CharField()
    count = serializers.IntegerField()
    total_paise = serializers.IntegerField()


class RevenueSerializer(serializers.Serializer):
    orders = serializers.IntegerField()
    total_paise = serializers.IntegerField()
    by_kind = RevenueLineSerializer(many=True)


class SponsorOverviewSerializer(serializers.Serializer):
    organisations = AdminOrganisationSerializer(many=True)
    pools = AdminPoolSerializer(many=True)
    totals = serializers.DictField(child=serializers.IntegerField())
    pending_allocations = AdminAllocationSerializer(many=True)


class PlatformDashboardSerializer(serializers.Serializer):
    pandals = serializers.DictField(child=serializers.IntegerField())
    users = serializers.IntegerField()
    revenue_paise = serializers.IntegerField()
    donations = serializers.DictField(child=serializers.IntegerField())
    service_bookings = serializers.IntegerField()
    support = serializers.DictField(child=serializers.IntegerField())
    lost_items = serializers.DictField(child=serializers.IntegerField())
    sponsors = serializers.DictField(child=serializers.IntegerField())
    branding = serializers.DictField(child=serializers.IntegerField())
