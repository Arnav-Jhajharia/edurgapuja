from rest_framework import mixins, permissions, viewsets

from .models import LostItem
from .serializers import LostItemSerializer, SupportRequestSerializer


class SupportRequestViewSet(mixins.CreateModelMixin, viewsets.GenericViewSet):
    """Open to anyone — this is also the landing page's 'Talk to our team'."""

    serializer_class = SupportRequestSerializer
    permission_classes = [permissions.AllowAny]

    def perform_create(self, serializer):
        user = self.request.user if self.request.user.is_authenticated else None
        serializer.save(user=user)


class LostItemViewSet(mixins.CreateModelMixin, viewsets.GenericViewSet):
    """Reporting needs an account; reading a pandal's list does not, and lives on
    the pandal route instead."""

    serializer_class = LostItemSerializer
    queryset = LostItem.objects.all()

    def perform_create(self, serializer):
        serializer.save(reported_by=self.request.user)
