from django.conf import settings
from django.shortcuts import get_object_or_404
from drf_spectacular.utils import OpenApiParameter, extend_schema
from rest_framework import permissions, viewsets
from rest_framework.filters import SearchFilter
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.ops.models import LostItem
from apps.ops.serializers import LostItemSerializer

from .models import Pandal, PandalDomainAlias
from .serializers import (
    LiveStatusSerializer,
    PandalDetailSerializer,
    PandalListSerializer,
    PandalPageSerializer,
    SiteResolveSerializer,
)


def published():
    return Pandal.objects.filter(
        publication_status=Pandal.PublicationStatus.PUBLISHED, is_active=True
    )


class SiteResolveView(APIView):
    """Turn an incoming host into a pandal, or into a redirect.

    The web tier cannot simply strip the subdomain: a renamed pandal keeps its
    old name alive as a permanent redirect (FR-248), and a committee may bring
    its own domain (FR-249). Both are lookups.
    """

    permission_classes = [permissions.AllowAny]

    @extend_schema(parameters=[OpenApiParameter("host", str, required=True)],
                   responses=SiteResolveSerializer)
    def get(self, request):
        host = (request.query_params.get("host") or "").lower().split(":")[0]

        pandal = published().filter(custom_domain=host).first()
        if pandal is None and host.endswith(f".{settings.SITE_DOMAIN}"):
            slug = host[: -len(f".{settings.SITE_DOMAIN}")]
            pandal = published().filter(slug=slug).first()
        if pandal is not None:
            return Response({"status": "ok", "slug": pandal.slug})

        alias = PandalDomainAlias.objects.filter(host=host).select_related("pandal").first()
        if alias is not None:
            return Response({"status": "redirect", "permanent": True,
                             "redirect_to": alias.pandal.canonical_url})

        return get_object_or_404(Pandal, pk=None)  # raises 404 through the error envelope


class PandalViewSet(viewsets.ReadOnlyModelViewSet):
    """Public browse. Discovery filters — distance, popularity, theme — are
    specified (FR-031 to FR-034) but have no design yet, so they are absent."""

    permission_classes = [permissions.AllowAny]
    lookup_field = "slug"
    filterset_fields = ("city", "locality")
    filter_backends = [SearchFilter]
    search_fields = ("name", "theme_name", "locality__name")

    def get_queryset(self):
        return published().select_related("city", "locality")

    def get_serializer_class(self):
        return PandalDetailSerializer if self.action == "retrieve" else PandalListSerializer


class PandalPageView(APIView):
    """One request renders the page."""

    permission_classes = [permissions.AllowAny]

    @extend_schema(responses=PandalPageSerializer)
    def get(self, request, slug: str):
        pandal = get_object_or_404(
            published()
            .select_related("city", "locality", "brand", "live_status")
            .prefetch_related("blocks", "visit_facts", "donation_offerings", "services",
                              "pass_configs__category", "services__fields"),
            slug=slug,
        )
        language = (request.headers.get("Accept-Language") or "en")[:2]
        if language not in dict(settings.LANGUAGES):
            language = "en"

        data = PandalPageSerializer(pandal, context={"language": language}).data
        response = Response(data)
        # Cached at the edge by host and language; purged on publish.
        response["Cache-Control"] = "public, max-age=60"
        response["Vary"] = "Accept-Language"
        return response


class PandalLiveStatusView(APIView):
    """Excluded from the page cache and fetched separately — a wait time that is
    a minute old is worse than useless (FR-187)."""

    permission_classes = [permissions.AllowAny]

    @extend_schema(responses=LiveStatusSerializer)
    def get(self, request, slug: str):
        pandal = get_object_or_404(published().select_related("live_status"), slug=slug)
        live = getattr(pandal, "live_status", None)
        if live is None:
            return Response(None)
        return Response(LiveStatusSerializer(live).data)


class PandalLostItemsView(APIView):
    """Outstanding items only (FR-189)."""

    permission_classes = [permissions.AllowAny]

    @extend_schema(responses=LostItemSerializer(many=True))
    def get(self, request, slug: str):
        pandal = get_object_or_404(published(), slug=slug)
        items = LostItem.objects.filter(pandal=pandal, status=LostItem.Status.LOST)
        return Response(LostItemSerializer(items, many=True).data)
