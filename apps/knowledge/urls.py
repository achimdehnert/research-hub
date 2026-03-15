"""Knowledge app URL configuration."""

from django.urls import path

from apps.knowledge.views import outline_webhook
from apps.knowledge.views_dashboard import knowledge_dashboard

app_name = "knowledge"

urlpatterns = [
    path("webhook/outline/", outline_webhook, name="outline-webhook"),
    path("dashboard/", knowledge_dashboard, name="dashboard"),
]
