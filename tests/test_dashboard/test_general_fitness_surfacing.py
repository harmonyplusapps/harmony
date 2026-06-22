import pytest
from datetime import date, timedelta
from django.urls import reverse
from django.contrib.auth.models import User
from apps.accounts.models import UserProfile
from apps.fitness.models import FitnessPlan, WorkoutDay, WorkoutLog

TODAY = date.today()


def _user(username="gf"):
    u = User.objects.create_user(username=username, password="testpass123", email=f"{username}@e.com")
    UserProfile.objects.create(
        user=u, height_cm=170, weight_kg=65, gender="female",
        date_of_birth=date(1992, 3, 3), fitness_experience="beginner",
        primary_goal="Get active", diet_type="omnivore", food_allergies=[],
        daily_routine="", wake_time="07:00", sleep_time="23:00",
        work_schedule="9-5", workout_days_per_week=3, preferred_workout_days=[],
        workout_location="home", available_equipment=[],
        notification_email=f"{username}@e.com", onboarding_completed=True,
    )
    return u


def _consistent_week(user, week_number, weeks_ago, is_active=False):
    end = TODAY - timedelta(weeks=weeks_ago)
    start = end - timedelta(days=6)
    plan = FitnessPlan.objects.create(
        user=user, week_number=week_number, start_date=start, end_date=end,
        is_active=is_active, total_workout_days=3,
        weekly_goal_summary="g", claude_reasoning="r",
    )
    for i, dt in enumerate(["strength", "strength", "yoga"]):
        d = start + timedelta(days=i)
        wd = WorkoutDay.objects.create(
            fitness_plan=plan, date=d, day_of_week=d.strftime("%A"),
            day_type=dt, focus_area="full_body", estimated_duration_minutes=40,
        )
        if not is_active:
            WorkoutLog.objects.create(user=user, workout_day=wd, date=d, completed=True)
    return plan


@pytest.mark.django_db
def test_dashboard_shows_add_day_nudge(client):
    user = _user()
    for wk, ago in [(1, 3), (2, 2), (3, 1)]:
        _consistent_week(user, wk, ago)
    _consistent_week(user, 5, weeks_ago=-1, is_active=True)
    client.login(username="gf", password="testpass123")
    resp = client.get(reverse("dashboard"))
    gf = resp.context["general_fitness"]
    assert gf.consistent_week_streak == 3
    assert gf.add_training_day is True
    assert "4th training day" in resp.content.decode()


@pytest.mark.django_db
def test_dashboard_clean_for_new_user(client):
    _user("clean")
    client.login(username="clean", password="testpass123")
    resp = client.get(reverse("dashboard"))
    gf = resp.context["general_fitness"]
    assert gf.add_training_day is False
    assert gf.duration_bump_min == 0
    assert gf.run_rotation is None
    assert "4th training day" not in resp.content.decode()


@pytest.mark.django_db
def test_weekly_plan_shows_duration_hint(client):
    user = _user("wp")
    for wk, ago in [(1, 4), (2, 3), (3, 2), (5, 1)]:
        _consistent_week(user, wk, ago)
    _consistent_week(user, 6, weeks_ago=-1, is_active=True)
    client.login(username="wp", password="testpass123")
    resp = client.get(reverse("weekly_plan"))
    gf = resp.context["general_fitness"]
    assert gf.duration_bump_min == 10
    assert "+10 min suggested" in resp.content.decode()
