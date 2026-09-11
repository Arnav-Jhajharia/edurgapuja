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


class HandoffSerializer(serializers.Serializer):
    """What Razorpay Standard Checkout hands back on success.

    The field names are Razorpay's, kept verbatim so the client can pass the
    handler payload straight through without renaming anything.
    """

    razorpay_order_id = serializers.CharField(max_length=80)
    razorpay_payment_id = serializers.CharField(max_length=80)
    razorpay_signature = serializers.CharField(max_length=200)


class HandoffResultSerializer(serializers.Serializer):
    status = serializers.CharField()
    order_id = serializers.CharField()
    receipt_number = serializers.CharField(allow_blank=True)

