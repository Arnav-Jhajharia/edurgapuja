from django.urls import path
from rest_framework_simplejwt.views import TokenRefreshView

from .views import (
    AuthMethodsView,
    LogoutView,
    MeView,
    OtpRequestView,
    OtpVerifyView,
    PasswordLoginView,
    ProfileTypeListView,
    SetPasswordView,
)

urlpatterns = [
    path("auth/methods", AuthMethodsView.as_view(), name="auth-methods"),
    path("auth/otp/request", OtpRequestView.as_view(), name="otp-request"),
    path("auth/otp/verify", OtpVerifyView.as_view(), name="otp-verify"),
    path("auth/password/login", PasswordLoginView.as_view(), name="password-login"),
    path("auth/password/set", SetPasswordView.as_view(), name="password-set"),
    path("auth/token/refresh", TokenRefreshView.as_view(), name="token-refresh"),
    path("auth/logout", LogoutView.as_view(), name="logout"),
    path("me", MeView.as_view(), name="me"),
    path("profile-types", ProfileTypeListView.as_view(), name="profile-types"),
]
