from django.contrib import admin
from django.urls import path, include

urlpatterns = [
    path("admin/", admin.site.urls),
    path("accounts/", include("apps.accounts.urls")),
    # Uncomment in Task 12 when these URL modules are created:
    # path("dashboard/", include("apps.dashboard.urls")),
    # path("fitness/", include("apps.fitness.urls")),
    # path("health/", include("apps.health.urls")),
]
