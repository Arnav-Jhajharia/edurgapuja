from django.urls import path

from .views import DonationCreateView, DonationLinkResolveView

urlpatterns = [
    path("donations", DonationCreateView.as_view(), name="donation-create"),
    path("d/<slug:pandal_slug>/<str:token>", DonationLinkResolveView.as_view(),
         name="donation-link-resolve"),
]
