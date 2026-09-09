import json
import logging

from django.db import IntegrityError
from django.http import HttpResponse
from django.utils.decorators import method_decorator
from django.views import View
from django.views.decorators.csrf import csrf_exempt
from drf_spectacular.utils import extend_schema
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView

from . import providers, services
from .providers import SignatureError, get_provider

logger = logging.getLogger(__name__)


@method_decorator(csrf_exempt, name="dispatch")
class WebhookView(View):
    """Verify, store, acknowledge — then interpret.

    A plain Django view rather than a DRF one: this endpoint must not depend on
    content negotiation, authentication or throttling, and it needs the raw body
    to check the signature before anything parses it.

    Subclasses say where each provider puts its signature, its timestamp and its
    event id. Everything after that is identical, which is the point — the
    deduplication and the fulfilment must not be written twice.
    """

    provider_name = "razorpay"
    signature_header = "X-Razorpay-Signature"
    timestamp_header = ""
    event_id_header = "X-Razorpay-Event-Id"

    def event_id(self, request, payload: dict) -> str:
        return request.headers.get(self.event_id_header) or payload.get("id") or ""

    def post(self, request):
        provider = get_provider(self.provider_name)
        signature = request.headers.get(self.signature_header, "")
        timestamp = request.headers.get(self.timestamp_header, "") if self.timestamp_header else ""

        try:
            provider.verify_webhook(request.body, signature, timestamp)
        except SignatureError:
            logger.warning("%s webhook failed signature verification", self.provider_name)
            return HttpResponse(status=400)

        try:
            payload = json.loads(request.body)
        except json.JSONDecodeError:
            return HttpResponse(status=400)

        event_id = self.event_id(request, payload)
        if not event_id:
            return HttpResponse(status=400)

        try:
            event = services.record_event(
                provider=provider.name, event_id=event_id,
                event_type=self.event_type(payload), payload=payload,
            )
        except IntegrityError:
            # Seen before. A redelivery is a no-op, not an error — the provider
            # retries until it gets a 2xx.
            return HttpResponse(status=200)

        try:
            services.process_event(event)
        except Exception:
            # The event is stored, so a worker can retry. Never make the provider
            # redeliver just because our interpretation failed.
            logger.exception("failed to process payment event %s", event_id)

        return HttpResponse(status=200)

    def event_type(self, payload: dict) -> str:
        return payload.get("event", "")


class RazorpayWebhookView(WebhookView):
    """The default. Razorpay signs the raw body and names the event in `event`."""


class CashfreeWebhookView(WebhookView):
    """Cashfree signs `timestamp + body`, so the timestamp header is part of the
    proof. Its event name lives in `type`, and its id in `data.order.order_id`
    combined with the type — Cashfree does not send a single event id, so one is
    composed that is stable across redeliveries of the same event."""

    provider_name = "cashfree"
    signature_header = "x-webhook-signature"
    timestamp_header = "x-webhook-timestamp"

    def event_type(self, payload: dict) -> str:
        return payload.get("type", "")

    def event_id(self, request, payload: dict) -> str:
        data = payload.get("data", {}) or {}
        order = (data.get("order") or {}).get("order_id", "")
        payment = (data.get("payment") or {}).get("cf_payment_id", "")
        kind = payload.get("type", "")
        composed = ":".join(str(p) for p in (kind, order, payment) if p)
        return composed


class PaymentMethodsView(APIView):
    """Which gateways this deployment will take money through.

    Served rather than hard-coded so that turning one off during an outage is a
    setting and a restart, not a release — and so the client never offers a
    button that cannot work.
    """

    permission_classes = [AllowAny]

    @extend_schema(responses=None)
    def get(self, request):
        return Response({"providers": providers.available()})

