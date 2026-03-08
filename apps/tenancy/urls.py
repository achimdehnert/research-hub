from django.urls import path

from . import views

app_name = "tenancy"

urlpatterns = [
    path("", views.org_list, name="org-list"),
    path("create/", views.org_create, name="org-create"),
]
