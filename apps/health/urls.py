from django.urls import path
from . import views

urlpatterns = [
    path("log/nutrition/", views.log_nutrition, name="log_nutrition"),
    path("log/wellness/", views.log_wellness, name="log_wellness"),
]
