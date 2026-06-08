from django.urls import path
from . import views

urlpatterns = [
    path("", views.dashboard, name="dashboard"),
    path("plan/", views.weekly_plan, name="weekly_plan"),
]
