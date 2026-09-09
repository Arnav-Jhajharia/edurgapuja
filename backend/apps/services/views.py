import datetime as dt

from django.shortcuts import get_object_or_404
from drf_spectacular.utils import OpenApiParameter, extend_schema
from rest_framework import mixins, permissions, status, viewsets
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.pandals.models import Pandal
from apps.payments import services as payments
from apps.payments.serializers import CheckoutSerializer

from . import inventory
from .booking import start_booking
from .models import Service, ServiceBooking, ServiceDayCapacity
from .serializers import (
    DayAvailabilitySerializer,
    ServiceBookingCreateSerializer,
    ServiceBookingSerializer,
    ServiceSerializer,
)


class PandalServicesView(APIView):
    permission_classes = [permissions.AllowAny]

    @extend_schema(responses=ServiceSerializer(many=True))
    def get(self, request, slug: str):
        pandal = get_object_or_404(
            Pandal.objects.filter(publication_status=Pandal.PublicationStatus.PUBLISHED,
                                  is_active=True, offers_services=True),
            slug=slug,
        )
        services = Service.objects.filter(pandal=pandal, is_active=True)
        return Response(ServiceSerializer(services, many=True).data)


class ServiceAvailabilityView(APIView):
    """Places left per day, so the client can grey out what is gone rather than
    letting somebody reach checkout and be refused."""

    permission_classes = [permissions.AllowAny]

    @extend_schema(
        parameters=[OpenApiParameter("from", str), OpenApiParameter("to", str)],
        responses=DayAvailabilitySerializer(many=True),
    )
    def get(self, request, service_id):
        service = get_object_or_404(Service.objects.filter(is_active=True), pk=service_id)
        days = ServiceDayCapacity.objects.filter(service=service, is_open=True)

        if start := request.query_params.get("from"):
            days = days.filter(date__gte=dt.date.fromisoformat(start))
        if end := request.query_params.get("to"):
            days = days.filter(date__lte=dt.date.fromisoformat(end))

        return Response(DayAvailabilitySerializer([
            {"date": day.date, "capacity": day.capacity, "available": inventory.available(day)}
            for day in days
        ], many=True).data)


class ServiceBookingViewSet(mixins.ListModelMixin, mixins.RetrieveModelMixin,
                            viewsets.GenericViewSet):
    """A booking has a person attached and has to reach them, so it needs an
    account — unlike a donation, which may be entirely anonymous."""

    serializer_class = ServiceBookingSerializer
    # Schema generation introspects this without a request, so it must be a real
    # queryset; the per-caller scoping happens in get_queryset below.
    queryset = ServiceBooking.objects.none()

    def get_queryset(self):
        if getattr(self, "swagger_fake_view", False) or not self.request.user.is_authenticated:
            return ServiceBooking.objects.none()
        return (ServiceBooking.objects
                .filter(user=self.request.user)
                .select_related("service", "service__pandal", "day"))

    @extend_schema(request=ServiceBookingCreateSerializer, responses=CheckoutSerializer)
    def create(self, request):
        payload = ServiceBookingCreateSerializer(data=request.data)
        payload.is_valid(raise_exception=True)
        data = payload.validated_data

        booking, order, hold = start_booking(
            service_id=data["service_id"], date=data["date"], quantity=data["quantity"],
            details=data.get("details", {}), user=request.user,
        )
        payment = payments.create_payment(
            order=order,
            idempotency_key=request.headers.get("Idempotency-Key") or str(order.id),
            provider_name=data.get("payment_provider", ""),
        )

        return Response({
            "booking_id": str(booking.id),
            "status": booking.status,
            "hold_expires_at": hold.expires_at,
            "order_id": str(order.id),
            "amount_paise": order.total_paise,
            "payment": payments.payment_intent(payment),
        }, status=status.HTTP_201_CREATED)
