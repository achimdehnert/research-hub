"""research-hub URL configuration."""
from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.http import JsonResponse
from django.urls import include, path
from drf_spectacular.views import SpectacularAPIView, SpectacularSwaggerView

from apps.research.views_metrics import metrics_json, metrics_prometheus


def healthz(request):
    return JsonResponse({"status": "ok", "service": "research-hub"})


urlpatterns = [
    path("healthz/", healthz, name="healthz"),
    path("metrics/", metrics_json, name="metrics-json"),
    path("metrics/prometheus/", metrics_prometheus, name="metrics-prometheus"),
    path("admin/", admin.site.urls),
    path("accounts/", include("allauth.urls")),
    path("research/", include("apps.research.urls")),
    path("tenancy/", include("apps.tenancy.urls")),
    path("billing/modules/", include("django_module_shop.urls")),
    path("api/v1/", include("apps.research.api.urls")),
    path("api/schema/", SpectacularAPIView.as_view(), name="schema"),
    path("api/docs/", SpectacularSwaggerView.as_view(url_name="schema"), name="swagger-ui"),
    path("knowledge/", include("apps.knowledge.urls")),
    path("oidc/", include("mozilla_django_oidc.urls")),
    path("", include("apps.accounts.urls")),
] + static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
