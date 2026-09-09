from django.urls import path
from rest_framework.routers import SimpleRouter

from .views import (
    PandalLiveStatusView,
    PandalLostItemsView,
    PandalPageView,
    PandalViewSet,
    SiteResolveView,
)

router = SimpleRouter(trailing_slash=False)
router.register("pandals", PandalViewSet, basename="pandal")

urlpatterns = [
    path("site/resolve", SiteResolveView.as_view(), name="site-resolve"),
    path("pandals/<slug:slug>/page", PandalPageView.as_view(), name="pandal-page"),
    path("pandals/<slug:slug>/live-status", PandalLiveStatusView.as_view(),
         name="pandal-live-status"),
    path("pandals/<slug:slug>/lost-items", PandalLostItemsView.as_view(),
         name="pandal-lost-items"),
    *router.urls,
]
