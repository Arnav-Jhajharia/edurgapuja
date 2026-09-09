from django.urls import path
from rest_framework.routers import SimpleRouter

from .views import (
    CityPassCoverageView,
    GateManifestView,
    GateScanView,
    PandalPassAvailabilityView,
    PandalPassesView,
    PassViewSet,
)

router = SimpleRouter(trailing_slash=False)
router.register("passes", PassViewSet, basename="pass")

urlpatterns = [
    path("pandals/<slug:slug>/passes", PandalPassesView.as_view(), name="pandal-passes"),
    path("pandals/<slug:slug>/pass-availability", PandalPassAvailabilityView.as_view(),
         name="pandal-pass-availability"),
    path("pass-configs/<uuid:config_id>/coverage", CityPassCoverageView.as_view(),
         name="city-pass-coverage"),
    path("gate/manifest", GateManifestView.as_view(), name="gate-manifest"),
    path("gate/scan", GateScanView.as_view(), name="gate-scan"),
    *router.urls,
]
