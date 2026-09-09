from django.shortcuts import get_object_or_404
from drf_spectacular.utils import extend_schema
from rest_framework import permissions, status
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.payments import services as payments
from apps.payments.serializers import PaymentIntentSerializer

from .models import DonationLink
from .serializers import DonationCreateSerializer, DonationLinkSerializer
from .services import start_donation


class DonationLinkResolveView(APIView):
    """Opening a shared link tells the app which pandal and amount to pre-fill."""

    permission_classes = [permissions.AllowAny]

    @extend_schema(responses=DonationLinkSerializer)
    def get(self, request, pandal_slug: str, token: str):
        link = get_object_or_404(
            DonationLink.objects.select_related("pandal"),
            token=token, pandal__slug=pandal_slug, is_active=True,
        )
        return Response(DonationLinkSerializer(link).data)


class DonationCreateView(APIView):
    """Start a donation and return a payment intent.

    No account required. Anonymous giving skips verification entirely — only a
    purchase that has to reach a phone needs to know the phone (FR-046).
    """

    permission_classes = [permissions.AllowAny]

    @extend_schema(request=DonationCreateSerializer, responses=PaymentIntentSerializer)
    def post(self, request):
        payload = DonationCreateSerializer(data=request.data)
        payload.is_valid(raise_exception=True)
        data = payload.validated_data

        donation, order = start_donation(data=data, user=request.user)
        payment = payments.create_payment(
            order=order,
            idempotency_key=request.headers.get("Idempotency-Key") or str(order.id),
            provider_name=data.get("payment_provider", ""),
        )

        return Response({
            "order_id": str(order.id),
            "status": order.status,
            "amount_paise": order.total_paise,
            "donation_id": str(donation.id),
            "payment": payments.payment_intent(payment),
        }, status=status.HTTP_201_CREATED)
