from rest_framework import serializers

from .models import Service, ServiceBooking, ServiceField


class ServiceFieldSerializer(serializers.ModelSerializer):
    """One question, as the client needs to render it.

    `is_sensitive` is included on purpose: a form that is about to ask for a
    gotra or a disability should be able to say why it wants it.
    """

    class Meta:
        model = ServiceField
        fields = ("key", "label", "kind", "required", "help_text", "options",
                  "is_sensitive", "sort_order")


class ServiceSerializer(serializers.ModelSerializer):
    """The form is data now, not a platform-defined shape the client hard-codes.

    A pandal inventing a service nobody has thought of gets a working booking
    form on the landing page with no client change (FR-133).
    """

    fields_ = ServiceFieldSerializer(source="fields", many=True, read_only=True)

    class Meta:
        model = Service
        fields = ("id", "name", "slug", "type", "description", "price_paise",
                  "max_per_booking", "requires_capacity", "fields_")

    def to_representation(self, instance):
        # `fields` is taken by DRF's own Serializer API, so the attribute is
        # declared as `fields_` and renamed on the way out.
        data = super().to_representation(instance)
        data["fields"] = data.pop("fields_")
        return data


class DayAvailabilitySerializer(serializers.Serializer):
    date = serializers.DateField()
    capacity = serializers.IntegerField()
    available = serializers.IntegerField()


class ServiceBookingCreateSerializer(serializers.Serializer):
    # Which gateway to use. Ignored if it is not one this deployment
    # has turned on, so a stale client cannot break checkout.
    payment_provider = serializers.CharField(required=False, allow_blank=True,
                                             max_length=20)
    service_id = serializers.UUIDField()
    date = serializers.DateField()
    quantity = serializers.IntegerField(min_value=1, default=1)
    details = serializers.DictField(required=False, default=dict)


class ServiceBookingSerializer(serializers.ModelSerializer):
    service_name = serializers.CharField(source="service.name", read_only=True)
    pandal_name = serializers.CharField(source="service.pandal.name", read_only=True)
    date = serializers.DateField(source="day.date", read_only=True)

    class Meta:
        model = ServiceBooking
        fields = ("id", "service", "service_name", "pandal_name", "date", "quantity",
                  "status", "details", "confirmed_at", "created_at")
