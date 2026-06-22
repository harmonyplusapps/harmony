import pytest
from datetime import date, timedelta
from decimal import Decimal
from django.urls import reverse
from django.contrib.auth.models import User
from apps.accounts.models import UserProfile
from apps.health.models import WeightLog, WellnessLog


def _user():
    u = User.objects.create_user(username="cd", password="testpass123", email="cd@e.com")
    UserProfile.objects.create(
        user=u, height_cm=170, weight_kg=65, gender="female",
        date_of_birth=date(1992, 3, 3), fitness_experience="beginner",
        primary_goal="Get active", diet_type="omnivore", food_allergies=[],
        daily_routine="", wake_time="07:00", sleep_time="23:00",
        work_schedule="9-5", workout_days_per_week=3, preferred_workout_days=[],
        workout_location="home", available_equipment=[],
        notification_email="cd@e.com", onboarding_completed=True,
    )
    return u


@pytest.mark.django_db
def test_dashboard_shows_step_goal(client):
    user = _user()
    WellnessLog.objects.create(
        user=user, date=date.today() - timedelta(days=1), sleep_hours=8, sleep_quality=4,
        mood_score=5, stress_level=4, energy_level=6, steps=8000,
    )
    client.login(username="cd", password="testpass123")
    resp = client.get(reverse("dashboard"))
    assert resp.context["step_target"] == 8500
    assert "8500" in resp.content.decode()


@pytest.mark.django_db
def test_dashboard_shows_weight_trend(client):
    user = _user()
    today = date.today()
    for d, kg in [(1, "64.0"), (3, "64.4"), (9, "65.0"), (11, "65.2")]:
        WeightLog.objects.create(user=user, date=today - timedelta(days=d), weight_kg=Decimal(kg))
    client.login(username="cd", password="testpass123")
    resp = client.get(reverse("dashboard"))
    assert resp.context["weight_trend"] is not None
    assert resp.context["weight_trend"].direction == "down"
    assert "kg" in resp.content.decode()


@pytest.mark.django_db
def test_dashboard_no_cardio_data_renders_clean(client):
    _user()
    client.login(username="cd", password="testpass123")
    resp = client.get(reverse("dashboard"))
    assert resp.context["weight_trend"] is None
    assert resp.context["step_target"] is None
