from django.urls import path

from .views import KycStatusView, PanVerifyView

urlpatterns = [
    path("kyc/status", KycStatusView.as_view(), name="kyc-status"),
    path("kyc/pan", PanVerifyView.as_view(), name="kyc-pan"),
]
