from datetime import date
from decimal import Decimal
from types import SimpleNamespace

import pytest
from django.contrib.auth.models import User
from apps.accounts.models import UserProfile
from apps.fitness.models import FitnessPlan, WorkoutDay

from services.health.snapshot import HealthSnapshot, SorenessItem
from services.health.calculations import Momentum
from services.coach.engine import decide, decide_today, is_deload_week


ON = date(2026, 6, 18)


def _snap(**over):
    base = dict(
        date=ON, sleep_hours=Decimal("8"), sleep_quality=4, energy=7, stress=4,
        soreness=[], cycle_phase=None,
        momentum=Momentum(current_streak=0, days_since_last=None, bucket="no_history"),
        steps=None, resting_hr=None, recent_workouts=[],
    )
    base.update(over)
    return HealthSnapshot(**base)


def _workout(day_type="strength", focus_area="upper_body"):
    return SimpleNamespace(day_type=day_type, focus_area=focus_area)


def test_is_deload_week():
    assert is_deload_week(1) is False
    assert is_deload_week(2) is False
    assert is_deload_week(3) is False
    assert is_deload_week(4) is True
    assert is_deload_week(8) is True
    assert is_deload_week(12) is True
    assert is_deload_week(0) is False
    assert is_deload_week(None) is False


def test_deload_applies_intensity_flag_and_rationale():
    d = decide(_snap(), _workout(), is_deload=True)
    assert d.intensity_modifier == 0.8
    assert "deload" in d.flags
    assert "deload" in d.rationale.lower()
    assert d.is_override is True


def test_deload_compounds_with_low_energy():
    d = decide(_snap(energy=2), _workout(), is_deload=True)  # 0.7 * 0.8
    assert d.intensity_modifier == 0.56
    assert "deload" in d.flags


def test_deload_does_not_fire_on_hard_stop():
    sore = [SorenessItem("quads", "severe", "lower_body")]
    d = decide(_snap(soreness=sore), _workout(focus_area="lower_body"), is_deload=True)
    assert d.recommended_day_type == "active_recovery"
    assert "deload" not in d.flags


def test_decide_without_deload_is_unchanged():
    d = decide(_snap(), _workout())
    assert "deload" not in d.flags
    assert d.intensity_modifier == 1.0


def _user(username):
    u = User.objects.create_user(username=username, password="x", email=f"{username}@e.com")
    UserProfile.objects.create(
        user=u, height_cm=170, weight_kg=65, gender="female",
        date_of_birth=date(1992, 3, 3), fitness_experience="beginner",
        primary_goal="Get active", diet_type="omnivore", food_allergies=[],
        daily_routine="", wake_time="07:00", sleep_time="23:00",
        work_schedule="9-5", workout_days_per_week=3, preferred_workout_days=[],
        workout_location="home", available_equipment=[],
        notification_email=f"{username}@e.com",
    )
    return u


def _plan(user, week_number):
    today = date.today()
    plan = FitnessPlan.objects.create(
        user=user, week_number=week_number, start_date=today, end_date=today,
        total_workout_days=1, weekly_goal_summary="g", claude_reasoning="r",
        is_active=True,
    )
    WorkoutDay.objects.create(
        fitness_plan=plan, date=today, day_of_week=today.strftime("%A"),
        day_type="strength", focus_area="upper_body", estimated_duration_minutes=45,
    )
    return plan


@pytest.mark.django_db
def test_decide_today_deload_on_week_4():
    user = _user("dl4")
    _plan(user, week_number=4)
    d = decide_today(user, date.today())
    assert "deload" in d.flags


@pytest.mark.django_db
def test_decide_today_no_deload_on_week_3():
    user = _user("dl3")
    _plan(user, week_number=3)
    d = decide_today(user, date.today())
    assert "deload" not in d.flags
