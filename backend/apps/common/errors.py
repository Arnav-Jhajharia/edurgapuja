"""One error envelope, everywhere — as specified in the API contract §1.

    { "error": { "code": …, "message": …, "fields": { … } } }

Every 4xx is meant to be actionable by the client, so a code is a stable string
the client may branch on, not a sentence it has to parse.
"""

from rest_framework import status
from rest_framework.exceptions import APIException
from rest_framework.response import Response
from rest_framework.views import exception_handler as drf_exception_handler


class DomainError(APIException):
    """Base for anything that should surface as a typed 4xx, never a 500."""

    status_code = status.HTTP_400_BAD_REQUEST
    default_code = "bad_request"
    default_detail = "The request could not be completed."

    def __init__(self, message: str | None = None, *, fields: dict | None = None, **extra):
        super().__init__(message or self.default_detail)
        self.fields = fields or {}
        self.extra = extra


class ValidationFailedError(DomainError):
    status_code = status.HTTP_422_UNPROCESSABLE_ENTITY
    default_code = "validation_failed"


class CapacityUnavailableError(DomainError):
    status_code = status.HTTP_409_CONFLICT
    default_code = "capacity_unavailable"
    default_detail = "There are not enough places left."


class HoldExpiredError(DomainError):
    status_code = status.HTTP_409_CONFLICT
    default_code = "hold_expired"
    default_detail = "That reservation has expired."


def exception_handler(exc, context):
    response = drf_exception_handler(exc, context)
    if response is None:
        return None

    if isinstance(exc, DomainError):
        body = {"code": exc.default_code, "message": str(exc.detail)}
        if exc.fields:
            body["fields"] = exc.fields
        body.update(exc.extra)
        return Response({"error": body}, status=exc.status_code)

    detail = response.data
    if isinstance(detail, dict) and "detail" not in detail:
        # DRF field errors: {"phone": ["..."]}. Reported as 422 rather than DRF's
        # 400, because the contract reserves 400 for a malformed request and 422
        # for one that parsed but cannot be accepted.
        return Response(
            {"error": {"code": "validation_failed",
                       "message": "Some fields need attention.",
                       "fields": {k: v[0] if isinstance(v, list) else v
                                  for k, v in detail.items()}}},
            status=status.HTTP_422_UNPROCESSABLE_ENTITY,
        )

    code = getattr(exc, "default_code", "error")
    message = detail.get("detail") if isinstance(detail, dict) else str(detail)
    return Response({"error": {"code": code, "message": str(message)}},
                    status=response.status_code)
