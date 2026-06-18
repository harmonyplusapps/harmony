import pytest
from datetime import date
from django.urls import reverse
from django.contrib.auth.models import User
from apps.accounts.models import UserProfile
from apps.fitness.models import FitnessPlan, WorkoutDay
from apps.health.models import SorenessLog


def _user():
    u = User.objects.create_user(username="dv", password="testpass123", email="dv@e.com")
    UserProfile.objects.create(
        user=u, height_cm=170, weight_kg=65, gender="female",
        date_of_birth=date(1992, 3, 3), fitness_experience="beginner",
        primary_goal="Get active", diet_type="omnivore", food_allergies=[],
        daily_routine="", wake_time="07:00", sleep_time="23:00",
        work_schedule="9-5", workout_days_per_week=3, preferred_workout_days=[],
        workout_location="home", available_equipment=[],
        notification_email="dv@e.com", onboarding_completed=True,
    )
    return u


def _plan_today(user, focus_area="upper_body"):
    today = date.today()
    plan = FitnessPlan.objects.create(
        user=user, week_number=1, start_date=today, end_date=today,
        total_workout_days=1, weekly_goal_summary="g", claude_reasoning="r",
    )
    WorkoutDay.objects.create(
        fitness_plan=plan, date=today, day_of_week=today.strftime("%A"),
        day_type="strength", focus_area=focus_area, estimated_duration_minutes=45,
    )
    return plan


@pytest.mark.django_db
def test_dashboard_has_decision_in_context(client):
    user = _user()
    _plan_today(user)
    client.login(username="dv", password="testpass123")
    resp = client.get(reverse("dashboard"))
    assert "decision" in resp.context
    assert resp.context["decision"].recommended_day_type == "strength"


@pytest.mark.django_db
def test_dashboard_shows_active_recovery_card_on_soreness_override(client):
    user = _user()
    _plan_today(user, focus_area="lower_body")
    SorenessLog.objects.create(user=user, date=date.today(), muscle_group="quads", severity="severe")
    client.login(username="dv", password="testpass123")
    resp = client.get(reverse("dashboard"))
    body = resp.content.decode()
    assert "Active Recovery" in body
    assert "still sore" in body


@pytest.mark.django_db
def test_dashboard_clean_day_no_banner(client):
    user = _user()
    _plan_today(user, focus_area="upper_body")
    client.login(username="dv", password="testpass123")
    resp = client.get(reverse("dashboard"))
    assert "coach-banner" not in resp.content.decode()
