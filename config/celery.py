"""Celery configuration for research-hub."""
import os
from celery import Celery

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings.base")

app = Celery("research_hub")
app.config_from_object("django.conf:settings", namespace="CELERY")
app.autodiscover_tasks()
