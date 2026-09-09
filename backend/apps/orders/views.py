from django.shortcuts import get_object_or_404
from drf_spectacular.utils import extend_schema
from rest_framework import permissions
from rest_framework.response import Response
from rest_framework.views import APIView

from .models import Order
from .serializers import OrderSerializer, ReceiptSerializer


class OrderDetailView(APIView):
    """Polled by the client while a payment settles.

    Open to anyone holding the id, because a donation may have been made with no
    account at all — the id is unguessable (UUIDv7) and carries nothing sensitive.
    """

    permission_classes = [permissions.AllowAny]

    @extend_schema(responses=OrderSerializer)
    def get(self, request, order_id):
        order = get_object_or_404(Order.objects.prefetch_related("lines"), pk=order_id)
        return Response(OrderSerializer(order).data)


class OrderReceiptView(APIView):
    permission_classes = [permissions.AllowAny]

    @extend_schema(responses=ReceiptSerializer)
    def get(self, request, order_id):
        order = get_object_or_404(
            Order.objects.select_related("pandal").prefetch_related("lines"),
            pk=order_id, status=Order.Status.PAID,
        )
        return Response(ReceiptSerializer({
            "receipt_number": order.receipt_number,
            "pandal": order.pandal.name,
            "issued_at": order.paid_at,
            "total_paise": order.total_paise,
            "lines": order.lines.all(),
        }).data)
