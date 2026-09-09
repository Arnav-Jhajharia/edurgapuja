from django.urls import path
from rest_framework.routers import SimpleRouter

from .views import PandalServicesView, ServiceAvailabilityView, ServiceBookingViewSet

router = SimpleRouter(trailing_slash=False)
router.register("service-bookings", ServiceBookingViewSet, basename="service-booking")

urlpatterns = [
    path("pandals/<slug:slug>/services", PandalServicesView.as_view(), name="pandal-services"),
    path("services/<uuid:service_id>/availability", ServiceAvailabilityView.as_view(),
         name="service-availability"),
    *router.urls,
]
