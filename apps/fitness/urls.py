from django.urls import path
from . import views

urlpatterns = [
    path("log/day/<int:workout_day_id>/", views.log_workout_day, name="log_workout_day"),
    path("log/exercise/<int:exercise_id>/", views.log_exercise, name="log_exercise"),
]
