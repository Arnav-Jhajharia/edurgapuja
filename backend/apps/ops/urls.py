from rest_framework.routers import SimpleRouter

from .views import LostItemViewSet, SupportRequestViewSet

router = SimpleRouter(trailing_slash=False)
router.register("support-requests", SupportRequestViewSet, basename="support-request")
router.register("lost-items", LostItemViewSet, basename="lost-item")

urlpatterns = router.urls
