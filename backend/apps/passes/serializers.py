from rest_framework import serializers

from .models import Pass, PassCategory, PassConfig, PassLeg, ScanEvent


class PassCategorySerializer(serializers.ModelSerializer):
    class Meta:
        model = PassCategory
        fields = ("id", "name", "slug", "description")


class PassConfigSerializer(serializers.ModelSerializer):
    """One row of what is on sale. The category carries the price (D4)."""

    category = PassCategorySerializer(read_only=True)
    product_display = serializers.CharField(source="get_product_display", read_only=True)

    class Meta:
        model = PassConfig
        fields = ("id", "product", "product_display", "category", "from_date", "to_date",
                  "from_time", "to_time", "price_paise", "max_party_size")


class PandalDayAvailabilitySerializer(serializers.Serializer):
    """Named apart from the service one: same shape, different resource, and a
    shared component name would give generated clients the wrong type."""

    date = serializers.DateField()
    capacity = serializers.IntegerField()
    available = serializers.IntegerField()


class PassPurchaseSerializer(serializers.Serializer):
    # Which gateway to use. Ignored if it is not one this deployment
    # has turned on, so a stale client cannot break checkout.
    payment_provider = serializers.CharField(required=False, allow_blank=True,
                                             max_length=20)
    config_id = serializers.UUIDField()
    visit_date = serializers.DateField()
    party_size = serializers.IntegerField(min_value=1, default=1)
    # City Pass only: which of the covered pandals the buyer actually wants.
    # Omitted means every pandal selling passes in that city.
    pandal_ids = serializers.ListField(child=serializers.UUIDField(), required=False)
    contact_phone = serializers.CharField(required=False, allow_blank=True, max_length=20)


class PassLegSerializer(serializers.ModelSerializer):
    pandal_name = serializers.CharField(source="pandal.name", read_only=True)
    pandal_slug = serializers.CharField(source="pandal.slug", read_only=True)

    class Meta:
        model = PassLeg
        fields = ("id", "pandal", "pandal_name", "pandal_slug", "visit_date",
                  "slot_from", "slot_to", "state", "admitted_at")


class PassSerializer(serializers.ModelSerializer):
    category_name = serializers.CharField(source="category.name", read_only=True)
    product_display = serializers.CharField(source="get_product_display", read_only=True)
    legs = PassLegSerializer(many=True, read_only=True)
    pandals_covered = serializers.IntegerField(read_only=True)
    pandals_visited = serializers.IntegerField(read_only=True)

    class Meta:
        model = Pass
        fields = ("id", "pass_code", "product", "product_display", "category", "category_name",
                  "party_size", "status", "source", "issued_at", "legs",
                  "pandals_covered", "pandals_visited")


class LegSecretSerializer(serializers.Serializer):
    """Handed to the visitor's own device, once, so it can derive codes offline."""

    leg_id = serializers.UUIDField()
    secret = serializers.CharField()
    step_seconds = serializers.IntegerField()
    digits = serializers.IntegerField()
    payload_format = serializers.CharField()


class ManifestEntrySerializer(serializers.Serializer):
    leg_id = serializers.UUIDField()
    secret = serializers.CharField()
    pass_code = serializers.CharField()
    category = serializers.CharField()
    product = serializers.CharField()
    party_size = serializers.IntegerField()
    slot_from = serializers.TimeField(allow_null=True)
    slot_to = serializers.TimeField(allow_null=True)


class ScanSerializer(serializers.Serializer):
    """One scan, as the gate device reports it.

    `scanned_at` is the device's own clock, because a device that was offline
    reports an hour later and the time that matters is when the person was at
    the gate.
    """

    gate_id = serializers.UUIDField()
    payload = serializers.CharField(max_length=200)
    scanned_at = serializers.DateTimeField(required=False)
    device_id = serializers.CharField(required=False, allow_blank=True, max_length=80)
    override = serializers.BooleanField(default=False)
    override_reason = serializers.CharField(required=False, allow_blank=True, max_length=255)


class ScanEventSerializer(serializers.ModelSerializer):
    gate_name = serializers.CharField(source="gate.name", read_only=True)
    pass_code = serializers.CharField(source="leg.issued_pass.pass_code", read_only=True,
                                      default="")
    pandal_name = serializers.CharField(source="gate.pandal.name", read_only=True)

    class Meta:
        model = ScanEvent
        fields = ("id", "gate", "gate_name", "pandal_name", "leg", "pass_code", "result",
                  "scanned_at", "received_at", "device_id", "override_reason")
