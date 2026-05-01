from django.contrib import admin
from django.urls import path, include
from apps.accounts import views as account_views

urlpatterns = [
    path("admin/", admin.site.urls),
    path("accounts/", include("apps.accounts.urls")),
    path("dashboard/", account_views.dashboard_placeholder, name="dashboard"),
]
