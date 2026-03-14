"""Knowledge app URL configuration."""

from django.urls import path

from apps.knowledge.views import outline_webhook

app_name = "knowledge"

urlpatterns = [
    path("webhook/outline/", outline_webhook, name="outline-webhook"),
]
