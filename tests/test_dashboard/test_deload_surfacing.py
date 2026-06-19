import pytest
from datetime import date, timedelta
from django.urls import reverse
from django.contrib.auth.models import User
from apps.accounts.models import UserProfile
from apps.fitness.models import (
    FitnessPlan, WorkoutDay, WorkoutExercise, WorkoutLog, ExerciseLog,
)


def _user():
    u = User.objects.create_user(username="wp", password="testpass123", email="wp@e.com")
    UserProfile.objects.create(
        user=u, height_cm=170, weight_kg=65, gender="female",
        date_of_birth=date(1992, 3, 3), fitness_experience="beginner",
        primary_goal="Get active", diet_type="omnivore", food_allergies=[],
        daily_routine="", wake_time="07:00", sleep_time="23:00",
        work_schedule="9-5", workout_days_per_week=3, preferred_workout_days=[],
        workout_location="home", available_equipment=[],
        notification_email="wp@e.com", onboarding_completed=True,
    )
    return u


def _plan(user, week_number):
    today = date.today()
    return FitnessPlan.objects.create(
        user=user, week_number=week_number, start_date=today, end_date=today,
        is_active=True, total_workout_days=1, weekly_goal_summary="g", claude_reasoning="r",
    )


@pytest.mark.django_db
def test_weekly_plan_shows_deload_badge_on_week_4(client):
    _plan(_user(), 4)
    client.login(username="wp", password="testpass123")
    resp = client.get(reverse("weekly_plan"))
    assert resp.context["is_deload"] is True
    assert "deload-badge" in resp.content.decode()


@pytest.mark.django_db
def test_weekly_plan_no_badge_on_week_3(client):
    _plan(_user(), 3)
    client.login(username="wp", password="testpass123")
    resp = client.get(reverse("weekly_plan"))
    assert resp.context["is_deload"] is False
    assert "deload-badge" not in resp.content.decode()


@pytest.mark.django_db
def test_weekly_plan_shows_weight_suggestion(client):
    user = _user()
    plan = _plan(user, 3)
    today = date.today()
    wd = WorkoutDay.objects.create(
        fitness_plan=plan, date=today, day_of_week=today.strftime("%A"),
        day_type="strength", focus_area="lower_body", estimated_duration_minutes=45,
    )
    ex = WorkoutExercise.objects.create(
        workout_day=wd, section="main", sets=3, reps=10,
        custom_name="Goblet Squat", intensity="moderate",
    )
    # Prior logged session of the same lift in an earlier (inactive) plan -> hold @ 40 kg.
    past = today - timedelta(days=7)
    old_plan = FitnessPlan.objects.create(
        user=user, week_number=2, start_date=past, end_date=past, is_active=False,
        total_workout_days=1, weekly_goal_summary="g", claude_reasoning="r",
    )
    pwd = WorkoutDay.objects.create(
        fitness_plan=old_plan, date=past, day_of_week=past.strftime("%A"),
        day_type="strength", focus_area="lower_body", estimated_duration_minutes=45,
    )
    pex = WorkoutExercise.objects.create(
        workout_day=pwd, section="main", sets=3, reps=10,
        custom_name="Goblet Squat", intensity="moderate",
    )
    wl = WorkoutLog.objects.create(user=user, workout_day=pwd, date=past, completed=True)
    ExerciseLog.objects.create(
        workout_log=wl, workout_exercise=pex,
        sets_completed=3, reps_completed=[10, 10, 10], weight_kg=[40, 40, 40],
    )

    client.login(username="wp", password="testpass123")
    resp = client.get(reverse("weekly_plan"))
    assert "weight_suggestions" in resp.context
    assert resp.context["weight_suggestions"][ex.id].suggested_weight_kg == 40.0
    assert "40.0 kg" in resp.content.decode()
