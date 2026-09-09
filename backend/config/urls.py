from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import include, path
from drf_spectacular.views import SpectacularAPIView, SpectacularSwaggerView

from apps.common.views import health

api_v1 = [
    path("", include("apps.accounts.urls")),
    path("", include("apps.pandals.urls")),
    path("", include("apps.services.urls")),
    path("", include("apps.donations.urls")),
    path("", include("apps.orders.urls")),
    path("", include("apps.ops.urls")),
    path("", include("apps.passes.urls")),
    path("", include("apps.kyc.urls")),
    path("", include("apps.payments.urls")),
]

admin_v1 = [
    path("", include("apps.adminapi.urls")),
]

urlpatterns = [
    path("admin/", admin.site.urls),
    path("healthz", health, name="health"),
    path("api/schema/", SpectacularAPIView.as_view(), name="schema"),
    path("api/docs/", SpectacularSwaggerView.as_view(url_name="schema"), name="docs"),
    path("api/v1/", include(api_v1)),
    path("api/v1/admin/", include(admin_v1)),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
