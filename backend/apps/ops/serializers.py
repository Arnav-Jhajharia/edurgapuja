from rest_framework import serializers

from .models import LostItem, SupportRequest


class LostItemSerializer(serializers.ModelSerializer):
    class Meta:
        model = LostItem
        fields = ("id", "pandal", "item", "location", "contact_phone", "status", "created_at")
        read_only_fields = ("id", "status", "created_at")


class SupportRequestSerializer(serializers.ModelSerializer):
    class Meta:
        model = SupportRequest
        fields = ("id", "pandal", "name", "contact_phone", "subject", "message",
                  "status", "created_at")
        read_only_fields = ("id", "status", "created_at")
