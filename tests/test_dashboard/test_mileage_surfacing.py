import pytest
from datetime import date, timedelta
from decimal import Decimal
from django.urls import reverse
from django.contrib.auth.models import User
from apps.accounts.models import UserProfile
from apps.fitness.models import FitnessPlan, WorkoutDay, WorkoutLog, RunningStrategy


def _user():
    u = User.objects.create_user(username="mp", password="testpass123", email="mp@e.com")
    UserProfile.objects.create(
        user=u, height_cm=170, weight_kg=65, gender="female",
        date_of_birth=date(1992, 3, 3), fitness_experience="beginner",
        primary_goal="Run a 5K", diet_type="omnivore", food_allergies=[],
        daily_routine="", wake_time="07:00", sleep_time="23:00",
        work_schedule="9-5", workout_days_per_week=3, preferred_workout_days=[],
        workout_location="outdoor", available_equipment=[],
        notification_email="mp@e.com", onboarding_completed=True,
    )
    return u


def _completed_run(user, days_ago, km):
    d = date.today() - timedelta(days=days_ago)
    plan = FitnessPlan.objects.create(
        user=user, week_number=1, start_date=d, end_date=d, is_active=False,
        total_workout_days=1, weekly_goal_summary="g", claude_reasoning="r",
    )
    wd = WorkoutDay.objects.create(
        fitness_plan=plan, date=d, day_of_week=d.strftime("%A"),
        day_type="running", focus_area="cardio", estimated_duration_minutes=30,
    )
    RunningStrategy.objects.create(
        workout_day=wd, run_type="easy", total_distance_km=Decimal(str(km)),
        total_duration_minutes=30, pace_target="6:00/km",
    )
    WorkoutLog.objects.create(user=user, workout_day=wd, date=d, completed=True)


@pytest.mark.django_db
def test_weekly_plan_shows_mileage_target(client):
    user = _user()
    FitnessPlan.objects.create(
        user=user, week_number=2, start_date=date.today(), end_date=date.today(),
        is_active=True, total_workout_days=1, weekly_goal_summary="g", claude_reasoning="r",
    )
    _completed_run(user, 2, 5.0)
    _completed_run(user, 4, 8.0)  # total 13.0 -> 14.3
    client.login(username="mp", password="testpass123")
    resp = client.get(reverse("weekly_plan"))
    assert resp.context["weekly_mileage_km"] == 14.3
    assert "14.3 km" in resp.content.decode()


@pytest.mark.django_db
def test_weekly_plan_no_mileage_without_runs(client):
    user = _user()
    FitnessPlan.objects.create(
        user=user, week_number=2, start_date=date.today(), end_date=date.today(),
        is_active=True, total_workout_days=1, weekly_goal_summary="g", claude_reasoning="r",
    )
    client.login(username="mp", password="testpass123")
    resp = client.get(reverse("weekly_plan"))
    assert resp.context["weekly_mileage_km"] is None
