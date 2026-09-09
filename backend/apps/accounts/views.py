import logging

from django.db import transaction
from django.utils import timezone
from drf_spectacular.utils import extend_schema
from rest_framework import permissions, status
from rest_framework.generics import RetrieveUpdateAPIView
from rest_framework.response import Response
from rest_framework.throttling import ScopedRateThrottle
from rest_framework.views import APIView
from rest_framework_simplejwt.tokens import RefreshToken

from . import passwords
from .models import ProfileType, User
from .otp import service as otp_service
from .serializers import (
    OtpRequestResponseSerializer,
    OtpRequestSerializer,
    OtpVerifySerializer,
    PasswordLoginSerializer,
    ProfileTypeSerializer,
    SetPasswordSerializer,
    TokenPairSerializer,
    UserSerializer,
)

logger = logging.getLogger(__name__)


def client_ip(request) -> str | None:
    forwarded = request.META.get("HTTP_X_FORWARDED_FOR", "")
    return forwarded.split(",")[0].strip() or request.META.get("REMOTE_ADDR")


class OtpRequestView(APIView):
    """Step one of both sign-up and sign-in.

    One endpoint for both, and the response is identical either way — it must not
    reveal whether a number is already registered (FR-004).
    """

    permission_classes = [permissions.AllowAny]
    throttle_classes = [ScopedRateThrottle]
    throttle_scope = "otp"

    @extend_schema(request=OtpRequestSerializer, responses=OtpRequestResponseSerializer)
    def post(self, request):
        payload = OtpRequestSerializer(data=request.data)
        payload.is_valid(raise_exception=True)

        issued = otp_service.issue(
            payload.validated_data["phone"],
            purpose=payload.validated_data.get("purpose", "login"),
            ip=client_ip(request),
        )
        return Response({"resend_after_seconds": issued.resend_after_seconds})


class OtpVerifyView(APIView):
    """Step two. Verifying creates the account if it does not exist yet, which is
    what makes a web purchase reach the app with no linking step (FR-019)."""

    permission_classes = [permissions.AllowAny]

    @extend_schema(request=OtpVerifySerializer, responses=TokenPairSerializer)
    def post(self, request):
        payload = OtpVerifySerializer(data=request.data)
        payload.is_valid(raise_exception=True)
        data = payload.validated_data

        otp_service.verify(data["phone"], data["code"], purpose=data.get("purpose", "login"))

        with transaction.atomic():
            user, created = User.objects.get_or_create(
                phone=data["phone"],
                defaults={"preferred_language": data.get("preferred_language", "en")},
            )
            if user.phone_verified_at is None:
                user.phone_verified_at = timezone.now()
                user.save(update_fields=["phone_verified_at", "updated_at"])

        refresh = RefreshToken.for_user(user)
        return Response({
            "access": str(refresh.access_token),
            "refresh": str(refresh),
            "user": UserSerializer(user).data,
            "is_new_user": created,
        })


class PasswordLoginView(APIView):
    """The second door: phone and password instead of phone and code (D11).

    Throttled on the same scope as OTP because it is the same thing — an
    unauthenticated attempt to sign in as somebody, and the one endpoint here
    where guessing is possible at all.
    """

    permission_classes = [permissions.AllowAny]
    throttle_classes = [ScopedRateThrottle]
    throttle_scope = "login"

    @extend_schema(request=PasswordLoginSerializer, responses=TokenPairSerializer)
    def post(self, request):
        payload = PasswordLoginSerializer(data=request.data)
        payload.is_valid(raise_exception=True)

        user = passwords.authenticate(phone=payload.validated_data["phone"],
                                      password=payload.validated_data["password"])
        refresh = RefreshToken.for_user(user)
        return Response({
            "access": str(refresh.access_token),
            "refresh": str(refresh),
            "user": UserSerializer(user).data,
            "is_new_user": False,
        })


class SetPasswordView(APIView):
    """Give this account a password, or change the one it has.

    Requires a live session, which in practice means the caller has just proved
    the phone number by OTP. A password is a convenience layered on top of that
    proof, never a substitute for it.
    """

    @extend_schema(request=SetPasswordSerializer, responses=None)
    def post(self, request):
        payload = SetPasswordSerializer(data=request.data)
        payload.is_valid(raise_exception=True)

        request.user.set_password(payload.validated_data["password"])
        request.user.save(update_fields=["password", "updated_at"])
        return Response(status=status.HTTP_204_NO_CONTENT)


class AuthMethodsView(APIView):
    """What sign-in options to offer, so the client does not hard-code them."""

    permission_classes = [permissions.AllowAny]

    @extend_schema(responses=None)
    def get(self, request):
        return Response({
            "otp": True,
            "password": True,
            # Told to the client on purpose: a demo build should be able to say
            # out loud that it is a demo, rather than looking like the real one.
            "shared_dev_password": passwords.dev_password_is_open(),
        })


class LogoutView(APIView):
    """Ends this device's session by blacklisting its refresh token (FR-013)."""

    @extend_schema(request=None, responses=None)
    def post(self, request):
        token = request.data.get("refresh")
        if token:
            try:
                RefreshToken(token).blacklist()
            except Exception:
                # An expired or already-blacklisted token is not an error to the
                # caller: they asked to be signed out, and they are.
                logger.info("logout presented a token that was already invalid")
        return Response(status=status.HTTP_204_NO_CONTENT)


class MeView(RetrieveUpdateAPIView):
    serializer_class = UserSerializer

    def get_object(self):
        return self.request.user


class ProfileTypeListView(APIView):
    permission_classes = [permissions.AllowAny]

    @extend_schema(responses=ProfileTypeSerializer(many=True))
    def get(self, request):
        return Response(
            ProfileTypeSerializer(ProfileType.objects.filter(is_active=True), many=True).data
        )
