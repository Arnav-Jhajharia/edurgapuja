from rest_framework import serializers

from .models import Donation, DonationLink


class DonationLinkSerializer(serializers.ModelSerializer):
    path = serializers.CharField(read_only=True)
    pandal_slug = serializers.CharField(source="pandal.slug", read_only=True)

    class Meta:
        model = DonationLink
        fields = ("id", "pandal", "pandal_slug", "suggested_amount_paise", "purpose",
                  "token", "path", "is_active")


class DonationCreateSerializer(serializers.Serializer):
    # Which gateway to use. Ignored if it is not one this deployment
    # has turned on, so a stale client cannot break checkout.
    payment_provider = serializers.CharField(required=False, allow_blank=True,
                                             max_length=20)
    pandal_id = serializers.UUIDField()
    offering_id = serializers.UUIDField(required=False, allow_null=True)
    amount_paise = serializers.IntegerField(required=False, min_value=100)
    # Blank is how a donor stays anonymous, and the receipt then carries no name.
    donor_name = serializers.CharField(max_length=120, required=False, allow_blank=True,
                                       default="")
    message = serializers.CharField(max_length=280, required=False, allow_blank=True, default="")
    link_token = serializers.CharField(max_length=12, required=False, allow_blank=True)
    phone = serializers.CharField(max_length=20, required=False, allow_blank=True, default="")

    def validate(self, attrs):
        if not attrs.get("offering_id") and not attrs.get("amount_paise"):
            raise serializers.ValidationError(
                {"amount_paise": "Choose an offering or enter an amount."}
            )
        return attrs


class DonationSerializer(serializers.ModelSerializer):
    is_anonymous = serializers.BooleanField(read_only=True)

    class Meta:
        model = Donation
        fields = ("id", "pandal", "donor_name", "message", "amount_paise",
                  "is_anonymous", "received_at", "created_at")
