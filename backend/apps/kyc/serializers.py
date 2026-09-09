from rest_framework import serializers

from .models import KycCheck


class PanVerifySerializer(serializers.Serializer):
    # write_only throughout: a PAN should never come back out of an endpoint
    # that was given one.
    pan = serializers.CharField(max_length=20, write_only=True)
    name = serializers.CharField(max_length=140, write_only=True)
    date_of_birth = serializers.CharField(max_length=10, required=False, allow_blank=True,
                                          write_only=True)


class KycCheckSerializer(serializers.ModelSerializer):
    masked_number = serializers.SerializerMethodField()

    class Meta:
        model = KycCheck
        fields = ("id", "kind", "status", "masked_number", "name_on_record",
                  "reason", "verified_at", "created_at")

    def get_masked_number(self, check) -> str:
        """Enough for a donor to recognise which PAN, and no more."""
        if not check.number:
            return ""
        return f"{check.number[:2]}{'•' * 6}{check.number[-2:]}"


class KycStatusSerializer(serializers.Serializer):
    """What the donate form needs to decide whether to ask."""

    threshold_paise = serializers.IntegerField()
    verified = serializers.BooleanField()
    check = KycCheckSerializer(allow_null=True)
