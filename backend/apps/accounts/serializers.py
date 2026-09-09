from rest_framework import serializers

from .models import ProfileType, User
from .phone import normalise


class PhoneField(serializers.CharField):
    """Accepts any format a person might type; stores E.164 (FR-016)."""

    def to_internal_value(self, data):
        return normalise(super().to_internal_value(data))


class ProfileTypeSerializer(serializers.ModelSerializer):
    class Meta:
        model = ProfileType
        fields = ("id", "name", "slug", "description")


class OtpRequestSerializer(serializers.Serializer):
    phone = PhoneField()
    purpose = serializers.ChoiceField(
        choices=["login", "web_checkout"], default="login", required=False
    )


class OtpRequestResponseSerializer(serializers.Serializer):
    resend_after_seconds = serializers.IntegerField()


class OtpVerifySerializer(serializers.Serializer):
    phone = PhoneField()
    code = serializers.CharField(min_length=4, max_length=8)
    purpose = serializers.ChoiceField(
        choices=["login", "web_checkout"], default="login", required=False
    )
    preferred_language = serializers.ChoiceField(
        choices=["en", "bn", "hi"], required=False, default="en"
    )


class PasswordLoginSerializer(serializers.Serializer):
    phone = PhoneField()
    password = serializers.CharField(write_only=True, trim_whitespace=False)


class SetPasswordSerializer(serializers.Serializer):
    """Setting one needs an existing session, so a stolen phone number alone
    cannot claim an account by giving it a password."""

    password = serializers.CharField(write_only=True, trim_whitespace=False, min_length=8)


class UserSerializer(serializers.ModelSerializer):
    profile_types = serializers.PrimaryKeyRelatedField(
        many=True, queryset=ProfileType.objects.filter(is_active=True), required=False
    )
    profile_completeness = serializers.IntegerField(read_only=True)
    full_name = serializers.CharField(read_only=True)

    class Meta:
        model = User
        fields = ("id", "phone", "first_name", "last_name", "full_name", "email",
                  "date_of_birth", "gender", "state", "city", "pin_code",
                  "profile_types", "preferred_language", "profile_completeness",
                  "phone_verified_at", "date_joined")
        read_only_fields = ("id", "phone", "phone_verified_at", "date_joined")


class TokenPairSerializer(serializers.Serializer):
    access = serializers.CharField()
    refresh = serializers.CharField()
    user = UserSerializer()
    is_new_user = serializers.BooleanField()
