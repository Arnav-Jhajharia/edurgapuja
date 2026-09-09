import logging

from django.conf import settings
from django.db import connection
from django.http import JsonResponse
from django.views.decorators.http import require_GET
from redis import Redis
from redis.exceptions import RedisError

logger = logging.getLogger(__name__)


@require_GET
def health(request):
    """Liveness plus its two hard dependencies."""
    checks = {"database": False, "redis": False}

    try:
        with connection.cursor() as cur:
            cur.execute("SELECT 1")
            checks["database"] = cur.fetchone() == (1,)
    except Exception:  # a health check must never raise
        logger.exception("health: database check failed")

    try:
        checks["redis"] = bool(Redis.from_url(settings.REDIS_URL).ping())
    except (RedisError, OSError):
        logger.exception("health: redis check failed")

    ok = all(checks.values())
    return JsonResponse({"status": "ok" if ok else "degraded", **checks},
                        status=200 if ok else 503)
