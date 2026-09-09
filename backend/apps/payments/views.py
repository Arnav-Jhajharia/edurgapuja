import json
import logging

from django.db import IntegrityError
from django.http import HttpResponse
from django.utils.decorators import method_decorator
from django.views import View
from django.views.decorators.csrf import csrf_exempt

from . import services
from .providers import SignatureError, get_provider

logger = logging.getLogger(__name__)


@method_decorator(csrf_exempt, name="dispatch")
class RazorpayWebhookView(View):
    """Verify, store, acknowledge — then interpret.

    A plain Django view rather than a DRF one: this endpoint must not depend on
    content negotiation, authentication or throttling, and it needs the raw body
    to check the signature before anything parses it.
    """

    def post(self, request):
        provider = get_provider()
        signature = request.headers.get("X-Razorpay-Signature", "")

        try:
            provider.verify_webhook(request.body, signature)
        except SignatureError:
            logger.warning("razorpay webhook failed signature verification")
            return HttpResponse(status=400)

        try:
            payload = json.loads(request.body)
        except json.JSONDecodeError:
            return HttpResponse(status=400)

        event_id = request.headers.get("X-Razorpay-Event-Id") or payload.get("id") or ""
        if not event_id:
            return HttpResponse(status=400)

        try:
            event = services.record_event(
                provider=provider.name, event_id=event_id,
                event_type=payload.get("event", ""), payload=payload,
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
