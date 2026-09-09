from rest_framework import serializers

from .models import Order, OrderLine


class OrderLineSerializer(serializers.ModelSerializer):
    class Meta:
        model = OrderLine
        fields = ("kind", "description", "quantity", "unit_amount_paise", "amount_paise")


class OrderSerializer(serializers.ModelSerializer):
    lines = OrderLineSerializer(many=True, read_only=True)

    class Meta:
        model = Order
        fields = ("id", "pandal", "status", "subtotal_paise", "platform_fee_paise",
                  "discount_paise", "total_paise", "currency", "receipt_number",
                  "paid_at", "created_at", "lines")


class ReceiptSerializer(serializers.Serializer):
    receipt_number = serializers.CharField()
    pandal = serializers.CharField()
    issued_at = serializers.DateTimeField()
    total_paise = serializers.IntegerField()
    lines = OrderLineSerializer(many=True)
