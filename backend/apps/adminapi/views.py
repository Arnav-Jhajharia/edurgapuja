"""The admin API behind all four panels.

One API, four panels. The panel a person sees is decided by the roles in
`/admin/me`, but every queryset here is narrowed by `request.admin` regardless —
so choosing a different tab in the client shows a different screen, never
somebody else's data (FR-231, FR-233).
"""

import datetime as dt
import json

from django.core.serializers.json import DjangoJSONEncoder
from django.db.models import Count, Q, Sum
from django.shortcuts import get_object_or_404
from django.utils import timezone
from drf_spectacular.utils import extend_schema
from rest_framework import mixins, status, viewsets
from rest_framework.decorators import action
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.throttling import ScopedRateThrottle
from rest_framework.views import APIView
from rest_framework_simplejwt.tokens import RefreshToken

from apps.accounts import passwords
from apps.accounts.models import AdminMembership, OtpChallenge, Role, User
from apps.accounts.otp import service as otp_service
from apps.accounts.serializers import (
    OtpRequestSerializer,
    OtpVerifySerializer,
    PasswordLoginSerializer,
)
from apps.accounts.views import client_ip
from apps.common.errors import ValidationFailedError
from apps.donations.models import Donation, DonationLink, DonationOffering
from apps.geo.models import City, Locality
from apps.ops.models import LostItem, PandalLiveStatus, SupportRequest
from apps.orders.models import Order, OrderLine
from apps.pandals import blocks as page_blocks
from apps.pandals import onboarding
from apps.pandals.models import Gate, PageBlock, Pandal, PandalBrand, VisitFact, Volunteer
from apps.passes import sponsor_issue
from apps.passes.models import (
    PandalDayCapacity,
    Pass,
    PassCategory,
    PassConfig,
    PassConfigChange,
    PassLeg,
    ScanEvent,
)
from apps.services.models import (
    Service,
    ServiceBooking,
    ServiceDayCapacity,
    ServiceField,
)
from apps.services.templates import TEMPLATES, apply_template
from apps.sponsorship import operations as pools
from apps.sponsorship.models import (
    BrandingCreative,
    Organisation,
    Pool,
    PoolAllocation,
    PoolIssuance,
    SponsorshipPackage,
)

from . import serializers as s
from .permissions import IsAdmin, IsPandalAdmin, IsSponsorAdmin, IsSuperAdmin
from .scope import context_for

# --------------------------------------------------------------------------
# Signing in
# --------------------------------------------------------------------------

class AdminOtpRequestView(APIView):
    """Administrators sign in by mobile and one-time code, like everyone else
    (D11). The same machinery, a different purpose."""

    permission_classes = [AllowAny]

    @extend_schema(request=OtpRequestSerializer, responses=None)
    def post(self, request):
        payload = OtpRequestSerializer(data=request.data)
        payload.is_valid(raise_exception=True)

        issued = otp_service.issue(payload.validated_data["phone"],
                                   purpose=OtpChallenge.Purpose.ADMIN_LOGIN,
                                   ip=client_ip(request))
        return Response({"resend_after_seconds": issued.resend_after_seconds})


class AdminOtpVerifyView(APIView):
    permission_classes = [AllowAny]

    @extend_schema(request=OtpVerifySerializer, responses=None)
    def post(self, request):
        payload = OtpVerifySerializer(data=request.data)
        payload.is_valid(raise_exception=True)
        data = payload.validated_data

        otp_service.verify(data["phone"], data["code"],
                           purpose=OtpChallenge.Purpose.ADMIN_LOGIN)

        user = User.objects.filter(phone=data["phone"]).first()
        admin = context_for(user)
        if user is None or not admin.is_any_admin:
            # Verified, but nobody here. Deliberately indistinguishable from a
            # wrong code, so this endpoint cannot be used to discover admins.
            raise ValidationFailedError("That number cannot sign in to the admin.")

        refresh = RefreshToken.for_user(user)
        return Response({"access": str(refresh.access_token), "refresh": str(refresh),
                         "roles": sorted(admin.roles)})


class AdminPasswordLoginView(APIView):
    """Phone and password into the console, as an alternative to a code (D11).

    Same shape as the OTP door and the same silence: a number that is not an
    administrator's is refused in words indistinguishable from a wrong password,
    so this cannot be used to discover who the administrators are.
    """

    permission_classes = [AllowAny]
    throttle_classes = [ScopedRateThrottle]
    throttle_scope = "login"

    @extend_schema(request=PasswordLoginSerializer, responses=None)
    def post(self, request):
        payload = PasswordLoginSerializer(data=request.data)
        payload.is_valid(raise_exception=True)

        user = passwords.authenticate(phone=payload.validated_data["phone"],
                                      password=payload.validated_data["password"])
        admin = context_for(user)
        if not admin.is_any_admin:
            raise passwords.InvalidCredentialsError

        refresh = RefreshToken.for_user(user)
        return Response({"access": str(refresh.access_token), "refresh": str(refresh),
                         "roles": sorted(admin.roles)})


class AdminMeView(APIView):
    """Which panels to offer, and what each is scoped to."""

    permission_classes = [IsAdmin]

    @extend_schema(responses=s.AdminMeSerializer)
    def get(self, request):
        admin = request.admin
        pandals = (Pandal.objects.all() if admin.is_super
                   else Pandal.objects.filter(id__in=admin.pandal_ids))
        organisations = (Organisation.objects.all() if admin.is_super
                         else Organisation.objects.filter(id__in=admin.organisation_ids))

        return Response({
            "id": str(request.user.id),
            "full_name": request.user.full_name,
            "phone": request.user.phone,
            "roles": sorted(admin.roles),
            "pandals": [{"id": str(p.id), "name": p.name, "slug": p.slug,
                         "sells_passes": p.sells_passes} for p in pandals],
            "organisations": [{"id": str(o.id), "name": o.name,
                               "is_sub_sponsor": o.is_sub_sponsor} for o in organisations],
        })


# --------------------------------------------------------------------------
# A base that does the scoping once
# --------------------------------------------------------------------------

class PandalScopedViewSet(viewsets.ModelViewSet):
    """Everything a Pandal Admin manages, narrowed to their own pandals.

    Subclasses set `model` and `serializer_class` and get the rest. The scoping
    lives here so no subclass can forget it.
    """

    permission_classes = [IsPandalAdmin]
    model = None
    select_related: tuple[str, ...] = ()

    @property
    def queryset(self):
        """Declared so schema generation can find the model. Never used to
        serve a request — `get_queryset` below does the scoping."""
        return self.model.objects.none()

    def get_queryset(self):
        if getattr(self, "swagger_fake_view", False):
            return self.model.objects.none()
        queryset = self.model.objects.all()
        if self.select_related:
            queryset = queryset.select_related(*self.select_related)
        queryset = self.request.admin.pandals(queryset)
        if pandal := self.request.query_params.get("pandal"):
            queryset = queryset.filter(pandal_id=pandal)
        return queryset

    def perform_create(self, serializer):
        pandal = serializer.validated_data.get("pandal")
        if pandal and not self.request.admin.owns_pandal(pandal.id):
            raise ValidationFailedError("That pandal is not yours.")
        serializer.save()


class PandalViewSet(viewsets.ModelViewSet):
    serializer_class = s.AdminPandalSerializer
    permission_classes = [IsPandalAdmin]
    # No "delete": a pandal is retired by unpublishing it, never removed — its
    # donations and bookings have to stay auditable. "put" is listed because
    # Django checks this list before it ever looks at an @action's own methods,
    # so leaving it out silently 405s the live-status action below; a PUT to the
    # pandal record itself is refused in update() instead, where it can say why.
    http_method_names = ["get", "put", "patch", "post", "head", "options"]

    queryset = Pandal.objects.none()  # for schema generation only

    def get_queryset(self):
        if getattr(self, "swagger_fake_view", False):
            return Pandal.objects.none()
        return self.request.admin.pandals(
            Pandal.objects.select_related("city", "locality")
        )

    def create(self, request, *args, **kwargs):
        """Only a Super Admin onboards a committee (FR-238).

        Creating the row is the easy half. A new pandal is scaffolded with a
        palette and a full page of starter copy, because a committee that opens
        a blank subdomain has no idea which of twenty things to fill in first.
        """
        if not request.admin.is_super:
            raise ValidationFailedError("Only a Super Admin can add a pandal.")

        response = super().create(request, *args, **kwargs)
        pandal = Pandal.objects.get(pk=response.data["id"])
        onboarding.scaffold(pandal)
        return response

    @extend_schema(request=None, responses=None)
    @action(detail=True, methods=["post"])
    def scaffold(self, request, pk=None):
        """Fill in any block this page is missing, leaving written ones alone.

        For a pandal onboarded before a block existed, and for anyone who has
        deleted one and wants it back with something in it.
        """
        pandal = self.get_object()
        return Response({"blocks_created": onboarding.scaffold(pandal)})

    def update(self, request, *args, **kwargs):
        if not kwargs.get("partial"):
            raise ValidationFailedError(
                "Use PATCH to change a pandal — a PUT would blank every field you did not send."
            )
        return super().update(request, *args, **kwargs)

    @action(detail=True, methods=["get", "patch"])
    def brand(self, request, pk=None):
        pandal = self.get_object()
        brand, _ = PandalBrand.objects.get_or_create(pandal=pandal)
        if request.method == "GET":
            return Response(s.AdminBrandSerializer(brand).data)
        serializer = s.AdminBrandSerializer(brand, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data)

    @action(detail=True, methods=["get"])
    def blocks(self, request, pk=None):
        pandal = self.get_object()
        return Response(s.AdminPageBlockSerializer(pandal.blocks.all(), many=True).data)

    @action(detail=True, methods=["patch"], url_path=r"blocks/(?P<kind>[a-z_]+)")
    def block(self, request, pk=None, kind=None):
        """Edit one block, creating it if the page does not have one yet.

        A committee that has never touched its About section has no row for it,
        and asking them to "add a block" before they can write in it would be a
        detail of our storage leaking into their afternoon.
        """
        pandal = self.get_object()
        if kind not in page_blocks.BY_KIND:
            raise ValidationFailedError(f"There is no {kind} block on the page.")

        block, _ = PageBlock.objects.get_or_create(
            pandal=pandal, kind=kind, language=request.data.get("language", "en"),
            defaults={"sort_order": page_blocks.ORDER[kind]},
        )
        serializer = s.AdminPageBlockSerializer(block, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data)

    @extend_schema(responses=s.BlockSchemaSerializer(many=True))
    @action(detail=False, methods=["get"], url_path="page-schema")
    def page_schema(self, request):
        """What every block is made of, so the editor builds itself rather than
        hard-coding a shape that drifts from what the page renders."""
        return Response(page_blocks.BLOCKS)

    @action(detail=True, methods=["post"])
    def publish(self, request, pk=None):
        """draft → pending_review → published (FR-037)."""
        pandal = self.get_object()
        target = request.data.get("status", Pandal.PublicationStatus.PUBLISHED)
        if target not in Pandal.PublicationStatus.values:
            raise ValidationFailedError("Unknown publication status.")
        if target == Pandal.PublicationStatus.PUBLISHED and not request.admin.is_super:
            raise ValidationFailedError("A Super Admin publishes a page.")

        pandal.publication_status = target
        pandal.published_at = timezone.now() if target == "published" else None
        pandal.save(update_fields=["publication_status", "published_at", "updated_at"])
        return Response(s.AdminPandalSerializer(pandal).data)

    @action(detail=True, methods=["get", "put"], url_path="live-status")
    def live_status(self, request, pk=None):
        pandal = self.get_object()
        live, _ = PandalLiveStatus.objects.get_or_create(pandal=pandal)
        if request.method == "GET":
            return Response(s.AdminLiveStatusSerializer(live).data)
        serializer = s.AdminLiveStatusSerializer(live, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save(updated_by=request.user)
        return Response(serializer.data)


class CityViewSet(mixins.ListModelMixin, viewsets.GenericViewSet):
    """Cities and their localities. Any admin may read this — it is a lookup
    table, not somebody's data."""

    permission_classes = [IsAdmin]
    serializer_class = s.AdminCitySerializer

    queryset = City.objects.none()  # for schema generation only

    def get_queryset(self):
        if getattr(self, "swagger_fake_view", False):
            return City.objects.none()
        return City.objects.select_related("state").prefetch_related("localities").order_by("name")


class LocalityViewSet(mixins.ListModelMixin, mixins.CreateModelMixin, viewsets.GenericViewSet):
    """A Super Admin may add a locality, because onboarding a committee in a
    para nobody has entered yet should not be a database ticket."""

    serializer_class = s.AdminLocalitySerializer

    queryset = Locality.objects.none()  # for schema generation only

    def get_permissions(self):
        return [IsSuperAdmin()] if self.request.method == "POST" else [IsAdmin()]

    def get_queryset(self):
        if getattr(self, "swagger_fake_view", False):
            return Locality.objects.none()
        queryset = Locality.objects.order_by("name")
        if city := self.request.query_params.get("city"):
            queryset = queryset.filter(city_id=city)
        return queryset


class VisitFactViewSet(PandalScopedViewSet):
    model = VisitFact
    serializer_class = s.AdminVisitFactSerializer


class DonationOfferingViewSet(PandalScopedViewSet):
    model = DonationOffering
    serializer_class = s.AdminDonationOfferingSerializer


class DonationLinkViewSet(PandalScopedViewSet):
    model = DonationLink
    serializer_class = s.AdminDonationLinkSerializer
    select_related = ("pandal",)

    def get_queryset(self):
        # annotate() adds a GROUP BY, which drops the model's Meta ordering — and
        # paginating an unordered queryset lets a row appear on two pages.
        return (super().get_queryset()
                .annotate(donation_count=Count("donations"))
                .order_by("-created_at"))

    def perform_create(self, serializer):
        super().perform_create(serializer)
        serializer.instance.created_by = self.request.user
        serializer.instance.save(update_fields=["created_by", "updated_at"])


class DonationViewSet(mixins.ListModelMixin, mixins.RetrieveModelMixin, viewsets.GenericViewSet):
    """Read only. A donation is a financial record, not something to edit."""

    permission_classes = [IsPandalAdmin]
    serializer_class = s.AdminDonationSerializer

    queryset = Donation.objects.none()  # for schema generation only

    def get_queryset(self):
        if getattr(self, "swagger_fake_view", False):
            return Donation.objects.none()
        queryset = self.request.admin.pandals(
            Donation.objects.select_related("pandal", "offering")
        )
        if pandal := self.request.query_params.get("pandal"):
            queryset = queryset.filter(pandal_id=pandal)
        if received := self.request.query_params.get("received"):
            queryset = queryset.filter(received_at__isnull=(received == "false"))
        return queryset


class ServiceViewSet(PandalScopedViewSet):
    model = Service
    serializer_class = s.AdminServiceSerializer
    select_related = ("pandal",)

    def get_queryset(self):
        return super().get_queryset().prefetch_related("fields")

    def perform_create(self, serializer):
        """A new service starts with a form rather than none.

        A service with no questions cannot be booked usefully, and an admin who
        has just typed a name and a price should not have to discover that. The
        template only ever adds, so choosing one is a head start, not a
        commitment — every question can be renamed, reordered or deleted.
        """
        template = serializer.validated_data.pop("template", "") or "blank"
        super().perform_create(serializer)
        apply_template(serializer.instance, template)

    def perform_update(self, serializer):
        serializer.validated_data.pop("template", None)
        serializer.save()

    @extend_schema(responses=s.ServiceTemplateSerializer(many=True))
    @action(detail=False, methods=["get"])
    def templates(self, request):
        """Starting points for a form. Suggestions, not a catalogue — a service
        may end up asking nothing any of these ask."""
        return Response([
            {"slug": t["slug"], "name": t["name"], "description": t["description"],
             "requires_capacity": t["requires_capacity"],
             "fields": [{"key": f["key"], "label": f["label"], "kind": f["kind"],
                         "required": f["required"], "is_sensitive": f["is_sensitive"],
                         "help_text": f["help_text"], "options": f["options"]}
                        for f in t["fields"]]}
            for t in TEMPLATES
        ])

    @extend_schema(request=None, responses=s.AdminServiceFieldSerializer(many=True))
    @action(detail=True, methods=["post"], url_path="apply-template")
    def apply_template_action(self, request, pk=None):
        """Add a template's questions to a service that already exists."""
        service = self.get_object()
        apply_template(service, request.data.get("template", ""))
        return Response(s.AdminServiceFieldSerializer(self._form(service), many=True).data)

    @action(detail=True, methods=["get", "put"])
    def capacity(self, request, pk=None):
        """Places per day. PUT replaces the whole schedule for this service."""
        service = self.get_object()
        if request.method == "GET":
            return Response(s.AdminServiceDaySerializer(service.days.all(), many=True).data)

        for row in request.data.get("days", []):
            ServiceDayCapacity.objects.update_or_create(
                service=service, date=dt.date.fromisoformat(row["date"]),
                defaults={"capacity": row["capacity"], "is_open": row.get("is_open", True)},
            )
        return Response(s.AdminServiceDaySerializer(service.days.all(), many=True).data)

    @extend_schema(request=None, responses=s.AdminServiceFieldSerializer(many=True))
    @action(detail=True, methods=["put"])
    def reorder(self, request, pk=None):
        """Reorder the form. Takes the keys in the order they should be asked."""
        service = self.get_object()
        for order, key in enumerate(request.data.get("keys", []), start=1):
            service.fields.filter(key=key).update(sort_order=order * 10)
        return Response(s.AdminServiceFieldSerializer(self._form(service), many=True).data)

    @staticmethod
    def _form(service):
        """Read the questions back from the database, not from the prefetch.

        `get_queryset` prefetches `fields` for the list screen, and a prefetched
        related manager keeps answering from its cache — so an action that has
        just written would otherwise hand back what it replaced.
        """
        return ServiceField.objects.filter(service=service).order_by("sort_order", "id")


class ServiceFieldViewSet(viewsets.ModelViewSet):
    """The questions one service asks.

    Scoped through the service to the pandal: a committee builds its own forms
    and cannot reach anybody else's.
    """

    permission_classes = [IsPandalAdmin]
    serializer_class = s.AdminServiceFieldSerializer

    queryset = ServiceField.objects.none()  # for schema generation only

    def get_queryset(self):
        if getattr(self, "swagger_fake_view", False):
            return ServiceField.objects.none()
        queryset = self.request.admin.pandals(
            ServiceField.objects.select_related("service"), field="service__pandal",
        )
        if service := self.request.query_params.get("service"):
            queryset = queryset.filter(service_id=service)
        return queryset

    def perform_create(self, serializer):
        service = serializer.validated_data.get("service")
        if service and not self.request.admin.owns_pandal(service.pandal_id):
            raise ValidationFailedError("That service is not yours.")
        serializer.save()

    def perform_update(self, serializer):
        """The key is the name every stored booking answered under.

        Changing it would orphan them all — the answers would still be in the
        JSON under the old key and nothing would read them again. The label is
        what a visitor sees and is free to change.
        """
        if "key" in serializer.validated_data:
            if serializer.validated_data["key"] != serializer.instance.key:
                raise ValidationFailedError(
                    "A question's key cannot change once it exists — bookings are stored "
                    "under it. Change the label instead, or delete and add a new question.",
                    fields={"key": "Cannot be changed."},
                )
        serializer.save()

class ServiceBookingViewSet(mixins.ListModelMixin, viewsets.GenericViewSet):
    permission_classes = [IsPandalAdmin]
    serializer_class = s.AdminServiceBookingSerializer

    queryset = ServiceBooking.objects.none()  # for schema generation only

    def get_queryset(self):
        if getattr(self, "swagger_fake_view", False):
            return ServiceBooking.objects.none()
        queryset = ServiceBooking.objects.select_related("service", "service__pandal", "day")
        if not self.request.admin.is_super:
            queryset = queryset.filter(service__pandal_id__in=self.request.admin.pandal_ids)
        if pandal := self.request.query_params.get("pandal"):
            queryset = queryset.filter(service__pandal_id=pandal)
        return queryset


class LostItemViewSet(PandalScopedViewSet):
    model = LostItem
    serializer_class = s.AdminLostItemSerializer
    select_related = ("pandal",)

    @action(detail=True, methods=["post"], url_path="mark-found")
    def mark_found(self, request, pk=None):
        item = self.get_object()
        item.mark_found()
        return Response(s.AdminLostItemSerializer(item).data)


class SupportRequestViewSet(PandalScopedViewSet):
    model = SupportRequest
    serializer_class = s.AdminSupportRequestSerializer
    select_related = ("pandal",)

    def get_queryset(self):
        queryset = super().get_queryset()
        if state := self.request.query_params.get("status"):
            queryset = queryset.filter(status=state)
        return queryset

    @action(detail=True, methods=["post"], url_path="resolve")
    def resolve(self, request, pk=None):
        support_request = self.get_object()
        support_request.mark_resolved(by=request.user)
        return Response(s.AdminSupportRequestSerializer(support_request).data)


class GateViewSet(PandalScopedViewSet):
    model = Gate
    serializer_class = s.AdminGateSerializer


class VolunteerViewSet(PandalScopedViewSet):
    model = Volunteer
    serializer_class = s.AdminVolunteerSerializer
    select_related = ("pandal", "user", "gate")


class PackageViewSet(PandalScopedViewSet):
    model = SponsorshipPackage
    serializer_class = s.AdminPackageSerializer


# --------------------------------------------------------------------------
# Sponsor and sub-sponsor
# --------------------------------------------------------------------------

class SponsorOverviewView(APIView):
    """The figures the Sponsor and Sub-Sponsor panels open on.

    Pools are reported per pandal *and* as a rollup, because a pool belongs to an
    (organisation, pandal) pair (D6) — the single aggregate in the client's
    mockup is the rollup, not a balance.
    """

    permission_classes = [IsSponsorAdmin]

    @extend_schema(responses=s.SponsorOverviewSerializer)
    def get(self, request):
        admin = request.admin
        organisations = (Organisation.objects.all() if admin.is_super
                         else Organisation.objects.filter(id__in=admin.organisation_ids))
        pool_rows = Pool.objects.filter(organisation__in=organisations).select_related(
            "organisation", "pandal"
        )

        totals = pool_rows.aggregate(
            granted=Sum("granted"), transferred_out=Sum("transferred_out"), issued=Sum("issued")
        )
        granted = totals["granted"] or 0
        transferred = totals["transferred_out"] or 0
        issued = totals["issued"] or 0

        return Response({
            "organisations": s.AdminOrganisationSerializer(organisations, many=True).data,
            "packages": s.AdminPackageSerializer(
                SponsorshipPackage.objects.filter(
                    allocations__organisation__in=organisations,
                    allocations__status=PoolAllocation.Status.ACCEPTED,
                ).distinct(), many=True,
            ).data,
            "allocations": s.AdminAllocationSerializer(
                PoolAllocation.objects.filter(organisation__in=organisations)
                .select_related("pandal", "organisation", "package"), many=True,
            ).data,
            "issuances": s.AdminIssuanceSerializer(
                PoolIssuance.objects.filter(pool__organisation__in=organisations)
                .select_related("pool__organisation", "pool__pandal")[:50], many=True,
            ).data,
            "pools": s.AdminPoolSerializer(pool_rows, many=True).data,
            "totals": {"granted": granted, "transferred_out": transferred,
                       "issued": issued, "available": granted - transferred - issued},
            "pending_allocations": s.AdminAllocationSerializer(
                PoolAllocation.objects.filter(organisation__in=organisations,
                                              status=PoolAllocation.Status.PENDING)
                .select_related("pandal", "organisation", "package"),
                many=True,
            ).data,
        })


class AllocationViewSet(mixins.ListModelMixin, mixins.CreateModelMixin,
                        viewsets.GenericViewSet):
    permission_classes = [IsAdmin]
    serializer_class = s.AdminAllocationSerializer

    queryset = PoolAllocation.objects.none()  # for schema generation only

    def get_queryset(self):
        if getattr(self, "swagger_fake_view", False):
            return PoolAllocation.objects.none()
        admin = self.request.admin
        queryset = PoolAllocation.objects.select_related("pandal", "organisation", "package")
        if admin.is_super:
            return queryset
        # A pandal admin sees what it granted; a sponsor sees what it was offered.
        return queryset.filter(
            Q(pandal_id__in=admin.pandal_ids) | Q(organisation_id__in=admin.organisation_ids)
        )

    def perform_create(self, serializer):
        pandal = serializer.validated_data["pandal"]
        if not self.request.admin.owns_pandal(pandal.id):
            raise ValidationFailedError("That pandal is not yours.")
        serializer.save(created_by=self.request.user)

    @action(detail=True, methods=["post"])
    def accept(self, request, pk=None):
        """Acceptance, not allocation, is what credits a pool (FR-152)."""
        allocation = self.get_object()
        if not request.admin.owns_organisation(allocation.organisation_id):
            raise ValidationFailedError("That allocation was not offered to you.")
        pool = pools.accept_allocation(allocation_id=allocation.pk)
        return Response(s.AdminPoolSerializer(pool).data)

    @action(detail=True, methods=["post"])
    def decline(self, request, pk=None):
        allocation = self.get_object()
        if not request.admin.owns_organisation(allocation.organisation_id):
            raise ValidationFailedError("That allocation was not offered to you.")
        return Response(s.AdminAllocationSerializer(
            pools.decline_allocation(allocation_id=allocation.pk)
        ).data)


class PoolViewSet(mixins.ListModelMixin, mixins.RetrieveModelMixin, viewsets.GenericViewSet):
    permission_classes = [IsSponsorAdmin]
    serializer_class = s.AdminPoolSerializer

    queryset = Pool.objects.none()  # for schema generation only

    def get_queryset(self):
        if getattr(self, "swagger_fake_view", False):
            return Pool.objects.none()
        admin = self.request.admin
        queryset = Pool.objects.select_related("organisation", "pandal")
        return queryset if admin.is_super else queryset.filter(
            organisation_id__in=admin.organisation_ids
        )

    @action(detail=True, methods=["post"])
    def transfer(self, request, pk=None):
        """Sell passes down to a sub-sponsor. The rules — only to your own
        child, only at the same pandal, only as deep as policy allows — are
        enforced in `sponsorship.operations`, not here."""
        pool = self.get_object()
        payload = s.TransferSerializer(data=request.data)
        payload.is_valid(raise_exception=True)

        destination = get_object_or_404(Organisation, pk=payload.validated_data["to_organisation"])
        movement = pools.transfer(
            from_pool_id=pool.pk, to_organisation=destination,
            quantity=payload.validated_data["quantity"],
            price_per_pass_paise=payload.validated_data["price_per_pass_paise"],
        )
        return Response({"transfer_id": str(movement.id),
                         "from": s.AdminPoolSerializer(movement.from_pool).data,
                         "to": s.AdminPoolSerializer(movement.to_pool).data},
                        status=status.HTTP_201_CREATED)

    @action(detail=True, methods=["post"])
    def issue(self, request, pk=None):
        """Hand passes out of a pool.

        With a `visit_date` this mints real passes and consumes the pandal's
        capacity for that day — a sponsor's guest occupies a place at the gate
        exactly like a paying visitor (D2). Without one it moves the pool's
        counter and records the handover only, which is what a sponsor doing its
        own distribution off-platform wants.
        """
        pool = self.get_object()
        payload = s.IssueSerializer(data=request.data)
        payload.is_valid(raise_exception=True)
        data = payload.validated_data

        if data.get("visit_date"):
            sponsor_issue.issue_passes(
                pool_id=pool.pk, quantity=data["quantity"], visit_date=data["visit_date"],
                category_id=data.get("category"),
                distributed_to=data.get("distributed_to", ""), issued_by=request.user,
            )
        else:
            pools.issue_from_pool(
                pool_id=pool.pk, quantity=data["quantity"],
                distributed_to=data.get("distributed_to", ""), issued_by=request.user,
            )
        pool.refresh_from_db()
        return Response(s.AdminPoolSerializer(pool).data)


class BuyPassesView(APIView):
    """A sub-sponsor buys from its own sponsor, at the price its sponsor set.

    It cannot buy from a pandal, and it cannot choose the price — both rules
    live in `sponsorship.operations`, not here (FR-159, FR-160).
    """

    permission_classes = [IsSponsorAdmin]

    @extend_schema(request=s.BuyPassesSerializer, responses=s.AdminPoolSerializer)
    def post(self, request):
        payload = s.BuyPassesSerializer(data=request.data)
        payload.is_valid(raise_exception=True)

        admin = request.admin
        organisation = Organisation.objects.filter(
            id__in=admin.organisation_ids, parent__isnull=False
        ).first()
        if organisation is None:
            raise ValidationFailedError("Only a sub-sponsor buys passes.")

        pandal = get_object_or_404(Pandal, pk=payload.validated_data["pandal"])
        movement = pools.buy_from_parent(organisation=organisation, pandal=pandal,
                                         quantity=payload.validated_data["quantity"])
        return Response(s.AdminPoolSerializer(movement.to_pool).data,
                        status=status.HTTP_201_CREATED)


class IssuanceViewSet(mixins.ListModelMixin, viewsets.GenericViewSet):
    """Where a pool actually went."""

    permission_classes = [IsSponsorAdmin]
    serializer_class = s.AdminIssuanceSerializer
    queryset = PoolIssuance.objects.none()

    def get_queryset(self):
        if getattr(self, "swagger_fake_view", False):
            return PoolIssuance.objects.none()
        admin = self.request.admin
        queryset = PoolIssuance.objects.select_related("pool__organisation", "pool__pandal")
        return queryset if admin.is_super else queryset.filter(
            pool__organisation_id__in=admin.organisation_ids
        )


class OrganisationViewSet(viewsets.ModelViewSet):
    """A sponsor creates its own sub-sponsors; a Super Admin creates anyone."""

    permission_classes = [IsSponsorAdmin]
    serializer_class = s.AdminOrganisationSerializer

    queryset = Organisation.objects.none()  # for schema generation only

    def get_queryset(self):
        if getattr(self, "swagger_fake_view", False):
            return Organisation.objects.none()
        admin = self.request.admin
        if admin.is_super:
            return Organisation.objects.all()
        return Organisation.objects.filter(
            Q(id__in=admin.organisation_ids) | Q(parent_id__in=admin.organisation_ids)
        )

    def perform_create(self, serializer):
        parent = serializer.validated_data.get("parent")
        if not self.request.admin.is_super:
            if parent is None or not self.request.admin.owns_organisation(parent.id):
                raise ValidationFailedError("A sub-sponsor must belong to your organisation.")
        serializer.save()

    def perform_update(self, serializer):
        """A sponsor edits its sub-sponsors, never itself and never the tree.

        get_queryset() already limits the rows a sponsor can reach to its own
        organisations and their children — but "its own" is exactly the row it
        must not touch, because price_per_pass_paise there is what the *pandal*
        charges *them*. And letting anyone move `parent` would let a sponsor
        re-parent a sub-sponsor under someone else's pool.
        """
        admin = self.request.admin
        if not admin.is_super:
            if admin.owns_organisation(serializer.instance.pk):
                raise ValidationFailedError(
                    "You cannot edit your own organisation's terms — only your sub-sponsors'."
                )
            if "parent" in serializer.validated_data and (
                serializer.validated_data["parent"] != serializer.instance.parent
            ):
                raise ValidationFailedError("A sub-sponsor cannot be moved to another sponsor.")
        serializer.save()


# --------------------------------------------------------------------------
# Passes
# --------------------------------------------------------------------------

class PassCategoryViewSet(PandalScopedViewSet):
    """The pandal invents its own categories, so this is plain CRUD (D4)."""

    model = PassCategory
    serializer_class = s.AdminPassCategorySerializer


class PassConfigViewSet(PandalScopedViewSet):
    """The configuration grid: what is on sale, when, at what price.

    Every edit is journalled with the counts at that moment (FR-058), because
    the question asked after the Puja is always "what was it selling for on
    Ashtami" and the row itself only knows what it says today.
    """

    model = PassConfig
    serializer_class = s.AdminPassConfigSerializer
    select_related = ("category", "pandal")

    def _journal(self, config, action_name):
        day_total = PandalDayCapacity.objects.filter(pandal=config.pandal).aggregate(
            issued=Sum("issued_count"), capacity=Sum("capacity")
        )
        issued = day_total["issued"] or 0
        PassConfigChange.objects.create(
            config=config, pandal=config.pandal, actor=self.request.user, action=action_name,
            # Round-tripped through the JSON encoder: the serializer hands back
            # UUID and date objects, and a JSONField will not take those.
            snapshot=json.loads(json.dumps(s.AdminPassConfigSerializer(config).data,
                                           cls=DjangoJSONEncoder)),
            issued_count=issued, remaining_count=max(0, (day_total["capacity"] or 0) - issued),
        )

    def perform_create(self, serializer):
        super().perform_create(serializer)
        self._journal(serializer.instance, "created")

    def perform_update(self, serializer):
        serializer.save()
        self._journal(serializer.instance, "updated")

    @extend_schema(responses=None)
    @action(detail=True, methods=["get"])
    def changes(self, request, pk=None):
        config = self.get_object()
        return Response([
            {"action": c.action, "at": c.created_at, "issued": c.issued_count,
             "remaining": c.remaining_count, "by": getattr(c.actor, "full_name", "") or "",
             "snapshot": c.snapshot}
            for c in config.changes.select_related("actor")[:50]
        ])


class PandalDayCapacityView(APIView):
    """A pandal's own limit per day (D2) — the ceiling every pass sits under.

    Set as a range in one call, the same shape as service capacity, because an
    admin thinks "ten thousand a day from Shashthi to Dashami", not in rows.
    """

    permission_classes = [IsPandalAdmin]

    @extend_schema(responses=s.AdminPandalDaySerializer(many=True))
    def get(self, request, pandal_id):
        pandal = get_object_or_404(request.admin.pandals(Pandal.objects.all()), pk=pandal_id)
        days = PandalDayCapacity.objects.filter(pandal=pandal)
        return Response(s.AdminPandalDaySerializer(days, many=True).data)

    @extend_schema(request=None, responses=s.AdminPandalDaySerializer(many=True))
    def put(self, request, pandal_id):
        pandal = get_object_or_404(request.admin.pandals(Pandal.objects.all()), pk=pandal_id)
        for row in request.data.get("days", []):
            day, _ = PandalDayCapacity.objects.get_or_create(
                pandal=pandal, date=row["date"], defaults={"capacity": 0},
            )
            capacity = int(row["capacity"])
            if capacity < day.issued_count:
                # The database refuses this; the message says why it must.
                raise ValidationFailedError(
                    f"{day.issued_count} passes are already issued for {day.date}.",
                    fields={"capacity": f"Cannot go below {day.issued_count}."},
                )
            day.capacity = capacity
            day.is_open = row.get("is_open", day.is_open)
            day.save(update_fields=["capacity", "is_open", "updated_at"])

        days = PandalDayCapacity.objects.filter(pandal=pandal)
        return Response(s.AdminPandalDaySerializer(days, many=True).data)


class AdminPassViewSet(mixins.ListModelMixin, mixins.RetrieveModelMixin,
                       viewsets.GenericViewSet):
    """Passes issued at the caller's pandals.

    Scoped through the legs rather than the pass, because a City Pass belongs to
    no single pandal — each pandal on it sees it, and sees only its own leg's
    state.
    """

    permission_classes = [IsPandalAdmin]
    serializer_class = s.AdminPassSerializer

    queryset = Pass.objects.none()  # for schema generation only

    def get_queryset(self):
        if getattr(self, "swagger_fake_view", False):
            return Pass.objects.none()
        admin = self.request.admin
        queryset = (Pass.objects.select_related("category", "holder")
                    .prefetch_related("legs__pandal").order_by("-created_at"))
        if not admin.is_super:
            queryset = queryset.filter(legs__pandal_id__in=admin.pandal_ids).distinct()
        if pandal := self.request.query_params.get("pandal"):
            queryset = queryset.filter(legs__pandal_id=pandal).distinct()
        if status_filter := self.request.query_params.get("status"):
            queryset = queryset.filter(status=status_filter)
        if code := self.request.query_params.get("q"):
            queryset = queryset.filter(pass_code__icontains=code)
        return queryset


class ScanEventViewSet(mixins.ListModelMixin, viewsets.GenericViewSet):
    """The entry log. Read-only: a scan is a fact, and editing it would be
    editing whether somebody came in."""

    permission_classes = [IsPandalAdmin]
    serializer_class = s.AdminScanEventSerializer

    queryset = ScanEvent.objects.none()  # for schema generation only

    def get_queryset(self):
        if getattr(self, "swagger_fake_view", False):
            return ScanEvent.objects.none()
        admin = self.request.admin
        queryset = (ScanEvent.objects
                    .select_related("gate", "leg__issued_pass", "volunteer__user")
                    .order_by("-scanned_at"))
        queryset = admin.pandals(queryset, field="gate__pandal")
        if pandal := self.request.query_params.get("pandal"):
            queryset = queryset.filter(gate__pandal_id=pandal)
        if result := self.request.query_params.get("result"):
            queryset = queryset.filter(result=result)
        return queryset


class PassSummaryView(APIView):
    """The Passes & Payments screen's numbers, in one call."""

    permission_classes = [IsPandalAdmin]

    @extend_schema(responses=s.PassSummarySerializer)
    def get(self, request):
        admin = request.admin
        pandal_ids = (list(Pandal.objects.values_list("id", flat=True))
                      if admin.is_super else list(admin.pandal_ids))
        if pandal := request.query_params.get("pandal"):
            pandal_ids = [pandal]

        legs = PassLeg.objects.filter(pandal_id__in=pandal_ids)
        days = PandalDayCapacity.objects.filter(pandal_id__in=pandal_ids).aggregate(
            capacity=Sum("capacity"), issued=Sum("issued_count")
        )
        scans = ScanEvent.objects.filter(gate__pandal_id__in=pandal_ids)
        revenue = OrderLine.objects.filter(
            kind=OrderLine.Kind.PASS, order__pandal_id__in=pandal_ids,
            order__status=Order.Status.PAID,
        ).aggregate(total=Sum("amount_paise"))

        return Response({
            "capacity": days["capacity"] or 0,
            "issued": days["issued"] or 0,
            "available": max(0, (days["capacity"] or 0) - (days["issued"] or 0)),
            "legs_pending": legs.filter(state=PassLeg.State.PENDING).count(),
            "legs_visited": legs.filter(state=PassLeg.State.VISITED).count(),
            "revenue_paise": revenue["total"] or 0,
            "scans_admitted": scans.filter(result__in=[ScanEvent.Result.ADMITTED,
                                                       ScanEvent.Result.MANUAL_OVERRIDE]).count(),
            "scans_refused": scans.exclude(result__in=[ScanEvent.Result.ADMITTED,
                                                       ScanEvent.Result.MANUAL_OVERRIDE]).count(),
            "by_category": [
                {"category": row["issued_pass__category__name"], "count": row["n"]}
                for row in legs.values("issued_pass__category__name")
                              .annotate(n=Count("id")).order_by("-n")
            ],
        })


class StaffViewSet(mixins.ListModelMixin, mixins.CreateModelMixin,
                   mixins.DestroyModelMixin, viewsets.GenericViewSet):
    """Who can sign in to which console.

    A committee manages its own people — the alternative is a support ticket
    every time a volunteer joins, which is the sort of thing that means the
    account gets shared instead.
    """

    permission_classes = [IsAdmin]
    serializer_class = s.AdminStaffSerializer

    queryset = AdminMembership.objects.none()  # for schema generation only

    def get_queryset(self):
        if getattr(self, "swagger_fake_view", False):
            return AdminMembership.objects.none()
        admin = self.request.admin
        # Explicitly ordered: pagination over an unordered queryset can show the
        # same row on two pages and miss another entirely.
        queryset = (AdminMembership.objects
                    .select_related("user", "pandal", "organisation")
                    .order_by("pandal__name", "user__phone"))
        if admin.is_super:
            return queryset
        # Your own pandals' staff, and your own organisations' — never the
        # platform's whole administrator list.
        return queryset.filter(
            Q(pandal_id__in=admin.pandal_ids) | Q(organisation_id__in=admin.organisation_ids)
        )

    def perform_create(self, serializer):
        admin = self.request.admin
        role = serializer.validated_data["role"]
        pandal = serializer.validated_data.get("pandal")

        if admin.is_super:
            return serializer.save()

        # A pandal admin may add people to their own pandal, and only as pandal
        # admins. Anything else would be a way to grant yourself more than you
        # have, which is the whole point of checking here rather than hiding a
        # dropdown.
        if role != Role.PANDAL_ADMIN:
            raise ValidationFailedError("You can only add administrators for your pandal.")
        if pandal is None or not admin.owns_pandal(pandal.id):
            raise ValidationFailedError("That pandal is not yours.")
        serializer.save()

    def perform_destroy(self, instance):
        if instance.user_id == self.request.user.id:
            # Cheap to check, and the alternative is a committee locking itself
            # out of its own console on a Friday night.
            raise ValidationFailedError("You cannot remove your own access.")
        super().perform_destroy(instance)


class UserViewSet(mixins.ListModelMixin, mixins.RetrieveModelMixin, viewsets.GenericViewSet):
    """Everyone with an account, for the Super Admin only.

    List and retrieve, nothing else: an account is created by verifying a phone
    number and is closed by the person who owns it, so there is no edit here to
    write. Searching is by phone or name because that is what a support call
    gives you.
    """

    permission_classes = [IsSuperAdmin]
    serializer_class = s.AdminUserSerializer

    queryset = User.objects.none()  # for schema generation only

    def get_queryset(self):
        if getattr(self, "swagger_fake_view", False):
            return User.objects.none()
        queryset = (User.objects.prefetch_related("memberships__pandal",
                                                  "memberships__organisation")
                    .order_by("-date_joined"))
        if term := self.request.query_params.get("q"):
            queryset = queryset.filter(
                Q(phone__icontains=term) | Q(first_name__icontains=term)
                | Q(last_name__icontains=term) | Q(email__icontains=term)
            )
        if self.request.query_params.get("admins_only") == "true":
            queryset = queryset.filter(memberships__isnull=False).distinct()
        return queryset


class CreativeViewSet(viewsets.ModelViewSet):
    permission_classes = [IsSponsorAdmin]
    serializer_class = s.AdminCreativeSerializer

    queryset = BrandingCreative.objects.none()  # for schema generation only

    def get_queryset(self):
        if getattr(self, "swagger_fake_view", False):
            return BrandingCreative.objects.none()
        admin = self.request.admin
        queryset = BrandingCreative.objects.select_related("organisation", "pandal", "placement")
        return queryset if admin.is_super else queryset.filter(
            organisation_id__in=admin.organisation_ids
        )

    def perform_create(self, serializer):
        organisation = serializer.validated_data["organisation"]
        pandal = serializer.validated_data["pandal"]
        if not self.request.admin.owns_organisation(organisation.id):
            raise ValidationFailedError("That organisation is not yours.")

        # Entitlement is enforced at upload, not caught later (D8). Pending and
        # approved both occupy a placement, or a sponsor queues unlimited
        # uploads and exceeds its package the moment they are approved.
        entitled = pools.entitled_placements(organisation, pandal)
        in_use = BrandingCreative.objects.filter(
            organisation=organisation, pandal=pandal,
            status__in=[BrandingCreative.Status.PENDING, BrandingCreative.Status.APPROVED],
        ).count()
        if in_use >= entitled:
            raise ValidationFailedError(
                f"Your package allows {entitled} placement(s) at {pandal.name}, "
                f"and {in_use} are already in use.",
            )
        serializer.save()

    @action(detail=True, methods=["post"])
    def review(self, request, pk=None):
        """A Super Admin approves or rejects a creative (FR-174)."""
        if not request.admin.is_super:
            raise ValidationFailedError("Only a Super Admin reviews creatives.")
        creative = self.get_object()
        decision = request.data.get("decision")
        if decision not in {"approved", "rejected"}:
            raise ValidationFailedError("Decide either approved or rejected.")

        creative.status = decision
        creative.rejection_reason = request.data.get("reason", "")[:255]
        creative.reviewed_by = request.user
        creative.reviewed_at = timezone.now()
        creative.save(update_fields=["status", "rejection_reason", "reviewed_by",
                                     "reviewed_at", "updated_at"])
        return Response(s.AdminCreativeSerializer(creative).data)


# --------------------------------------------------------------------------
# Dashboards
# --------------------------------------------------------------------------

class RevenueView(APIView):
    """Grouped by `order_line.kind`, so passes appear here later with no new
    endpoint (Scope §4.5)."""

    permission_classes = [IsPandalAdmin]

    @extend_schema(responses=s.RevenueSerializer)
    def get(self, request):
        orders = Order.objects.filter(status=Order.Status.PAID)
        if not request.admin.is_super:
            orders = orders.filter(pandal_id__in=request.admin.pandal_ids)
        if pandal := request.query_params.get("pandal"):
            orders = orders.filter(pandal_id=pandal)
        if start := request.query_params.get("from"):
            orders = orders.filter(paid_at__date__gte=dt.date.fromisoformat(start))
        if end := request.query_params.get("to"):
            orders = orders.filter(paid_at__date__lte=dt.date.fromisoformat(end))

        by_kind = (OrderLine.objects.filter(order__in=orders)
                   .values("kind")
                   .annotate(count=Count("id"), total_paise=Sum("amount_paise"))
                   .order_by("kind"))

        return Response({
            "orders": orders.count(),
            "total_paise": orders.aggregate(n=Sum("total_paise"))["n"] or 0,
            "by_kind": list(by_kind),
        })


class PlatformDashboardView(APIView):
    """The Super Admin's opening screen."""

    permission_classes = [IsSuperAdmin]

    @extend_schema(responses=s.PlatformDashboardSerializer)
    def get(self, request):
        paid = Order.objects.filter(status=Order.Status.PAID)
        return Response({
            "pandals": {
                "total": Pandal.objects.count(),
                "published": Pandal.objects.filter(
                    publication_status=Pandal.PublicationStatus.PUBLISHED).count(),
                "selling_passes": Pandal.objects.filter(sells_passes=True).count(),
            },
            "users": User.objects.count(),
            "revenue_paise": paid.aggregate(n=Sum("total_paise"))["n"] or 0,
            "donations": {
                "count": Donation.objects.filter(received_at__isnull=False).count(),
                "total_paise": Donation.objects.filter(received_at__isnull=False)
                               .aggregate(n=Sum("amount_paise"))["n"] or 0,
            },
            "service_bookings": ServiceBooking.objects.filter(
                status=ServiceBooking.Status.CONFIRMED).count(),
            "support": {
                "new": SupportRequest.objects.filter(status=SupportRequest.Status.NEW).count(),
            },
            "lost_items": {
                "open": LostItem.objects.filter(status=LostItem.Status.LOST).count(),
            },
            "sponsors": {
                "organisations": Organisation.objects.filter(parent__isnull=True).count(),
                "sub_sponsors": Organisation.objects.filter(parent__isnull=False).count(),
                "pending_allocations": PoolAllocation.objects.filter(
                    status=PoolAllocation.Status.PENDING).count(),
            },
            "branding": {
                "pending_review": BrandingCreative.objects.filter(
                    status=BrandingCreative.Status.PENDING).count(),
            },
        })
