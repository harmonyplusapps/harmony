import pytest
from datetime import date
from django.contrib.auth.models import User
from apps.accounts.models import UserProfile
from apps.fitness.models import FitnessPlan, WorkoutDay
from apps.health.models import SorenessLog
from services.coach.engine import decide_today


def _user():
    u = User.objects.create_user(username="dt", password="x", email="dt@e.com")
    UserProfile.objects.create(
        user=u, height_cm=170, weight_kg=65, gender="female",
        date_of_birth=date(1992, 3, 3), fitness_experience="beginner",
        primary_goal="Get active", diet_type="omnivore", food_allergies=[],
        daily_routine="", wake_time="07:00", sleep_time="23:00",
        work_schedule="9-5", workout_days_per_week=3, preferred_workout_days=[],
        workout_location="home", available_equipment=[],
        notification_email="dt@e.com",
    )
    return u


def _plan_with_today(user, focus_area):
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
def test_decide_today_no_plan_is_rest():
    user = _user()
    d = decide_today(user, date.today())
    assert d.recommended_day_type == "rest"
    assert d.is_override is False


@pytest.mark.django_db
def test_decide_today_soreness_conflict_overrides_to_active_recovery():
    user = _user()
    _plan_with_today(user, focus_area="lower_body")
    SorenessLog.objects.create(user=user, date=date.today(), muscle_group="quads", severity="severe")
    d = decide_today(user, date.today())
    assert d.recommended_day_type == "active_recovery"
    assert d.is_override is True
    assert "lower_body" in d.avoid_focus_areas


@pytest.mark.django_db
def test_decide_today_clean_day_is_on_plan():
    user = _user()
    _plan_with_today(user, focus_area="upper_body")
    d = decide_today(user, date.today())
    assert d.recommended_day_type == "strength"
    assert d.is_override is False


@pytest.mark.django_db
def test_decide_today_uses_passed_workout_day():
    user = _user()
    plan = _plan_with_today(user, focus_area="upper_body")
    wd = WorkoutDay.objects.get(fitness_plan=plan)
    d = decide_today(user, date.today(), workout_day=wd)
    assert d.recommended_day_type == "strength"
    assert d.is_override is False
