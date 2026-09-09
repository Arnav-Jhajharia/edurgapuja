from django.conf import settings
from rest_framework import serializers

from apps.donations.models import DonationOffering
from apps.ops.models import PandalLiveStatus
from apps.passes.serializers import PassConfigSerializer
from apps.services.models import Service
from apps.services.serializers import ServiceFieldSerializer

from .models import PageBlock, Pandal, PandalBrand, VisitFact


class BrandSerializer(serializers.ModelSerializer):
    class Meta:
        model = PandalBrand
        fields = ("primary_colour", "accent_colour", "surface_colour", "ink_colour",
                  "display_font", "body_font", "logo", "mark")


class PageBlockSerializer(serializers.ModelSerializer):
    class Meta:
        model = PageBlock
        fields = ("kind", "sort_order", "content")


class VisitFactSerializer(serializers.ModelSerializer):
    class Meta:
        model = VisitFact
        fields = ("label", "value", "sort_order")


class DonationOfferingSerializer(serializers.ModelSerializer):
    class Meta:
        model = DonationOffering
        fields = ("id", "amount_paise", "label", "description")


class ServiceSummarySerializer(serializers.ModelSerializer):
    """Carries each service's own questions, so the landing page can render a
    booking form for a service the platform has never heard of."""

    fields_ = ServiceFieldSerializer(source="fields", many=True, read_only=True)

    class Meta:
        model = Service
        fields = ("id", "name", "slug", "type", "description", "price_paise",
                  "max_per_booking", "requires_capacity", "fields_")

    def to_representation(self, instance):
        data = super().to_representation(instance)
        data["fields"] = data.pop("fields_")
        return data


class LiveStatusSerializer(serializers.ModelSerializer):
    age_seconds = serializers.IntegerField(read_only=True)
    crowd_level_display = serializers.CharField(source="get_crowd_level_display", read_only=True)

    class Meta:
        model = PandalLiveStatus
        fields = ("estimated_wait_minutes", "crowd_level", "crowd_level_display",
                  "note", "updated_at", "age_seconds")


class PandalListSerializer(serializers.ModelSerializer):
    locality_name = serializers.CharField(source="locality.name", default="", read_only=True)
    city_name = serializers.CharField(source="city.name", read_only=True)
    canonical_url = serializers.CharField(read_only=True)

    class Meta:
        model = Pandal
        fields = ("id", "name", "slug", "canonical_url", "theme_name", "theme_name_local",
                  "locality_name", "city_name", "latitude", "longitude", "opens_on")


class PandalDetailSerializer(PandalListSerializer):
    class Meta(PandalListSerializer.Meta):
        fields = (*PandalListSerializer.Meta.fields, "committee_name", "address",
                  "closes_on", "seo_title", "seo_description")


class PandalPageSerializer(serializers.Serializer):
    """Everything the landing page renders, in one payload.

    The web tier is server-rendered, so a page must be one round trip, not eight
    — this is the read Google and WhatsApp previews hit.
    """

    def to_representation(self, pandal: Pandal) -> dict:
        language = self.context.get("language", "en")
        blocks = [b for b in pandal.blocks.all()
                  if b.is_visible and b.language == language]
        if not blocks:  # fall back to English rather than rendering an empty page
            blocks = [b for b in pandal.blocks.all() if b.is_visible and b.language == "en"]

        brand = getattr(pandal, "brand", None)
        live = getattr(pandal, "live_status", None)

        return {
            "pandal": {
                "id": str(pandal.id),
                "slug": pandal.slug,
                "name": pandal.name,
                "committee_name": pandal.committee_name,
                "locality": pandal.locality.name if pandal.locality_id else "",
                "city": pandal.city.name,
                "canonical_url": pandal.canonical_url,
                "theme": {"name": pandal.theme_name, "name_local": pandal.theme_name_local},
            },
            "seo": {
                "title": pandal.seo_title or f"{pandal.name} · Durga Puja",
                "description": pandal.seo_description,
                "og_image_url": pandal.og_image.url if pandal.og_image else None,
                "locales": [code for code, _ in settings.LANGUAGES],
            },
            "capabilities": {
                "sells_passes": pandal.sells_passes,
                "accepts_donations": pandal.accepts_donations,
                "offers_services": pandal.offers_services,
            },
            "brand": BrandSerializer(brand).data if brand else None,
            "blocks": PageBlockSerializer(blocks, many=True).data,
            "visit_facts": VisitFactSerializer(pandal.visit_facts.all(), many=True).data,
            # Absent, not empty, when the capability is off — the client already
            # iterates and already reads capabilities, so turning passes on later
            # adds a block and changes no client code (FR-050a).
            "donation_offerings": (
                DonationOfferingSerializer(
                    [o for o in pandal.donation_offerings.all() if o.is_active], many=True
                ).data if pandal.accepts_donations else []
            ),
            "services": (
                ServiceSummarySerializer(
                    [s for s in pandal.services.all() if s.is_active], many=True
                ).data if pandal.offers_services else []
            ),
            # Empty until the committee switches passes on, at which point the
            # block fills and the page renders it — no client change (FR-050a).
            "passes": (
                PassConfigSerializer(
                    [c for c in pandal.pass_configs.all()
                     if c.is_active and c.category.is_active], many=True
                ).data if pandal.sells_passes else []
            ),
            "live_status": LiveStatusSerializer(live).data if live else None,
        }


class SiteResolveSerializer(serializers.Serializer):
    status = serializers.ChoiceField(choices=["ok", "redirect"])
    slug = serializers.CharField(required=False)
    redirect_to = serializers.CharField(required=False)
    permanent = serializers.BooleanField(required=False)
