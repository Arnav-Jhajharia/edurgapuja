"""The visitor's and the gate's view of passes.

Three audiences, three permission stances:

* **Public** — what a pandal sells, and how many places are left. No account.
* **Signed in** — buying, and the passes you hold. A pass has to reach a phone,
  so unlike a donation it cannot be anonymous.
* **Gate staff** — the manifest and the scan endpoint, restricted to volunteers
  posted at that pandal.
"""

import datetime as dt

from django.shortcuts import get_object_or_404
from django.utils import timezone
from drf_spectacular.types import OpenApiTypes
from drf_spectacular.utils import OpenApiParameter, extend_schema
from rest_framework import mixins, permissions, status, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.common.errors import ValidationFailedError
from apps.pandals.models import Gate, Pandal, Volunteer
from apps.payments import services as payments
from apps.payments.serializers import CheckoutSerializer

from . import inventory, scanning
from .codes import DIGITS, PAYLOAD_PREFIX, STEP_SECONDS
from .models import PandalDayCapacity, Pass, PassConfig
from .purchase import covered_pandals, start_purchase
from .serializers import (
    LegSecretSerializer,
    ManifestEntrySerializer,
    PandalDayAvailabilitySerializer,
    PassConfigSerializer,
    PassPurchaseSerializer,
    PassSerializer,
    ScanEventSerializer,
    ScanSerializer,
)


def _selling_pandal(slug: str) -> Pandal:
    """A pandal only appears to sell passes once it has switched them on.

    This is the whole of what "each pandal owner can introduce a pass when they
    need one" costs at the API: a flag that already existed.
    """
    return get_object_or_404(
        Pandal.objects.filter(publication_status=Pandal.PublicationStatus.PUBLISHED,
                              is_active=True, sells_passes=True),
        slug=slug,
    )


class PandalPassesView(APIView):
    permission_classes = [permissions.AllowAny]

    @extend_schema(responses=PassConfigSerializer(many=True))
    def get(self, request, slug: str):
        pandal = _selling_pandal(slug)
        configs = (PassConfig.objects
                   .select_related("category")
                   .filter(pandal=pandal, is_active=True, category__is_active=True))
        return Response(PassConfigSerializer(configs, many=True).data)


class PandalPassAvailabilityView(APIView):
    """Places left per day at this pandal, so a client greys out what is gone
    rather than letting somebody reach checkout and be refused."""

    permission_classes = [permissions.AllowAny]

    @extend_schema(
        parameters=[OpenApiParameter("from", str), OpenApiParameter("to", str)],
        responses=PandalDayAvailabilitySerializer(many=True),
    )
    def get(self, request, slug: str):
        pandal = _selling_pandal(slug)
        days = PandalDayCapacity.objects.filter(pandal=pandal, is_open=True)

        if start := request.query_params.get("from"):
            days = days.filter(date__gte=dt.date.fromisoformat(start))
        if end := request.query_params.get("to"):
            days = days.filter(date__lte=dt.date.fromisoformat(end))

        return Response(PandalDayAvailabilitySerializer([
            {"date": day.date, "capacity": day.capacity, "available": inventory.available(day)}
            for day in days
        ], many=True).data)


class PassViewSet(mixins.ListModelMixin, mixins.RetrieveModelMixin, viewsets.GenericViewSet):
    serializer_class = PassSerializer
    queryset = Pass.objects.none()  # for schema generation only

    def get_queryset(self):
        if getattr(self, "swagger_fake_view", False) or not self.request.user.is_authenticated:
            return Pass.objects.none()
        return (Pass.objects
                .filter(holder=self.request.user)
                .select_related("category")
                .prefetch_related("legs__pandal"))

    @extend_schema(request=PassPurchaseSerializer, responses=CheckoutSerializer)
    def create(self, request):
        payload = PassPurchaseSerializer(data=request.data)
        payload.is_valid(raise_exception=True)
        data = payload.validated_data

        issued, order, holds = start_purchase(
            config_id=data["config_id"], visit_date=data["visit_date"],
            party_size=data["party_size"], pandal_ids=data.get("pandal_ids"),
            user=request.user, contact_phone=data.get("contact_phone", ""),
        )
        payment = payments.create_payment(
            order=order,
            idempotency_key=request.headers.get("Idempotency-Key") or str(order.id),
            provider_name=data.get("payment_provider", ""),
        )

        return Response({
            "pass_id": str(issued.id),
            "pass_code": issued.pass_code,
            "status": issued.status,
            "pandals_covered": len(holds),
            "hold_expires_at": min(h.expires_at for h in holds),
            "order_id": str(order.id),
            "amount_paise": order.total_paise,
            "payment": payments.payment_intent(payment),
        }, status=status.HTTP_201_CREATED)

    @extend_schema(
        parameters=[OpenApiParameter("leg_id", OpenApiTypes.UUID,
                                     OpenApiParameter.PATH)],
        responses=LegSecretSerializer,
    )
    @action(detail=True, methods=["get"], url_path=r"legs/(?P<leg_id>[^/.]+)/secret")
    def leg_secret(self, request, pk=None, leg_id=None):
        """Provision this device to generate entry codes without a network (D5).

        Only the holder, and only for a pass that has actually been paid for —
        the secret is the whole of what a phone needs to produce a code, so it
        must not exist before the money does.
        """
        issued = self.get_object()
        leg = get_object_or_404(issued.legs, pk=leg_id)
        secret = getattr(leg, "secret", None)
        if secret is None:
            raise ValidationFailedError(
                "This pass is not paid for yet, so it has no entry code."
            )
        return Response({
            "leg_id": str(leg.id),
            "secret": secret.secret,
            "step_seconds": STEP_SECONDS,
            "digits": DIGITS,
            "payload_format": f"{PAYLOAD_PREFIX}:<leg_id>:<counter>:<code>",
        })


class CityPassCoverageView(APIView):
    """Which pandals a City Pass configuration would cover, before buying it."""

    permission_classes = [permissions.AllowAny]

    @extend_schema(responses=None)
    def get(self, request, config_id):
        config = get_object_or_404(
            PassConfig.objects.select_related("pandal").filter(is_active=True), pk=config_id
        )
        return Response([
            {"id": str(p.id), "name": p.name, "slug": p.slug}
            for p in covered_pandals(config)
        ])


# --------------------------------------------------------------------------
# The gate
# --------------------------------------------------------------------------

class IsGateStaff(permissions.BasePermission):
    """Posted at that pandal, and still active.

    Deactivating a volunteer ends their ability to scan on the next request —
    which is the point of the flag, and why this is checked per call rather than
    baked into a token at sign-in.
    """

    message = "You are not posted at that gate."

    def has_permission(self, request, view):
        if not request.user.is_authenticated:
            return False
        gate_id = request.data.get("gate_id") or request.query_params.get("gate_id")
        pandal_id = request.query_params.get("pandal")
        postings = Volunteer.objects.filter(user=request.user, is_active=True)
        if gate_id:
            return postings.filter(pandal__gates__id=gate_id).exists()
        if pandal_id:
            return postings.filter(pandal_id=pandal_id).exists()
        return postings.exists()


class GateManifestView(APIView):
    """Everything a device needs to admit people for one pandal on one day,
    downloaded while it still has signal (D5)."""

    permission_classes = [IsGateStaff]

    @extend_schema(
        parameters=[OpenApiParameter("pandal", str), OpenApiParameter("date", str)],
        responses=ManifestEntrySerializer(many=True),
    )
    def get(self, request):
        pandal_id = request.query_params.get("pandal")
        if not pandal_id:
            raise ValidationFailedError("Say which pandal.", fields={"pandal": "Required."})
        pandal = get_object_or_404(Pandal, pk=pandal_id)

        raw = request.query_params.get("date")
        date = dt.date.fromisoformat(raw) if raw else timezone.localdate()

        return Response(ManifestEntrySerializer(
            scanning.manifest(pandal=pandal, date=date), many=True
        ).data)


class GateScanView(APIView):
    """Report a scan. Accepts a batch, because a device that was offline for an
    hour has an hour of them to send at once."""

    permission_classes = [IsGateStaff]

    @extend_schema(request=ScanSerializer, responses=ScanEventSerializer)
    def post(self, request):
        payload = ScanSerializer(data=request.data)
        payload.is_valid(raise_exception=True)
        data = payload.validated_data

        gate = get_object_or_404(Gate.objects.filter(is_active=True), pk=data["gate_id"])
        volunteer = Volunteer.objects.filter(
            user=request.user, pandal=gate.pandal, is_active=True
        ).first()

        if data.get("override") and not data.get("override_reason"):
            raise ValidationFailedError(
                "An override has to say why.",
                fields={"override_reason": "Give a reason."},
            )

        event = scanning.admit(
            gate=gate, payload=data["payload"], scanned_at=data.get("scanned_at"),
            volunteer=volunteer, device_id=data.get("device_id", ""),
            override=data.get("override", False),
            override_reason=data.get("override_reason", ""),
        )
        return Response(ScanEventSerializer(event).data, status=status.HTTP_201_CREATED)
