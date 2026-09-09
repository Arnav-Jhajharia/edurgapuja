from rest_framework import serializers


class PaymentIntentSerializer(serializers.Serializer):
    """What a client needs to open the gateway's checkout."""

    provider = serializers.CharField()
    provider_order_id = serializers.CharField()
    key_id = serializers.CharField()
    amount_paise = serializers.IntegerField()
    currency = serializers.CharField()


class CheckoutSerializer(serializers.Serializer):
    order_id = serializers.UUIDField()
    status = serializers.CharField()
    amount_paise = serializers.IntegerField()
    payment = PaymentIntentSerializer()
