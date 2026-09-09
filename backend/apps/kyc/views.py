"""The donor's side of verification."""

from drf_spectacular.utils import extend_schema
from rest_framework import permissions, status
from rest_framework.response import Response
from rest_framework.throttling import ScopedRateThrottle
from rest_framework.views import APIView

from . import services
from .models import verified_pan
from .serializers import KycCheckSerializer, KycStatusSerializer, PanVerifySerializer


class KycStatusView(APIView):
    """Whether this donor is ready to give a large amount, and from what point
    it starts mattering.

    Public, because the donate form has to know the threshold before anybody has
    signed in — otherwise the first a donor hears of it is a refusal.
    """

    permission_classes = [permissions.AllowAny]

    @extend_schema(responses=KycStatusSerializer)
    def get(self, request):
        check = verified_pan(request.user) if request.user.is_authenticated else None
        return Response({
            "threshold_paise": services.threshold_paise(),
            "verified": check is not None,
            "check": KycCheckSerializer(check).data if check else None,
        })


class PanVerifyView(APIView):
    """Verify a PAN against the register.

    Throttled hard: this endpoint takes a number and says whether it is real,
    which is a lookup somebody could abuse if it were free.
    """

    throttle_classes = [ScopedRateThrottle]
    throttle_scope = "kyc"

    @extend_schema(request=PanVerifySerializer, responses=KycCheckSerializer)
    def post(self, request):
        payload = PanVerifySerializer(data=request.data)
        payload.is_valid(raise_exception=True)
        data = payload.validated_data

        check = services.verify_pan(
            user=request.user, pan=data["pan"], name=data["name"],
            date_of_birth=data.get("date_of_birth", ""),
        )
        return Response(KycCheckSerializer(check).data, status=status.HTTP_201_CREATED)
