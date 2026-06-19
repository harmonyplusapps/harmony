import pytest
from datetime import date, timedelta
from decimal import Decimal
from django.contrib.auth.models import User
from apps.health.models import WellnessLog, WeightLog
from apps.fitness.models import (
    FitnessPlan, WorkoutDay, WorkoutLog, RunningStrategy,
)
from services.coach.cardio import (
    suggest_step_target_for, suggest_weekly_mileage_for, body_weight_trend,
)

TODAY = date.today()


def _user(username="c"):
    return User.objects.create_user(username=username, password="x", email=f"{username}@e.com")


def _steps(user, days_ago, steps):
    WellnessLog.objects.create(
        user=user, date=TODAY - timedelta(days=days_ago),
        sleep_hours=8, sleep_quality=4, mood_score=5, stress_level=4,
        energy_level=6, steps=steps,
    )


def _run(user, days_ago, km, completed=True):
    d = TODAY - timedelta(days=days_ago)
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
    if completed:
        WorkoutLog.objects.create(user=user, workout_day=wd, date=d, completed=True)


def _weight(user, days_ago, kg):
    WeightLog.objects.create(user=user, date=TODAY - timedelta(days=days_ago), weight_kg=Decimal(str(kg)))


@pytest.mark.django_db
def test_step_target_none_when_no_steps():
    assert suggest_step_target_for(_user(), TODAY) is None


@pytest.mark.django_db
def test_step_target_averages_recent_steps():
    user = _user()
    _steps(user, 1, 8000)
    _steps(user, 2, 8400)   # avg 8200 -> round 8000 -> +500 = 8500
    assert suggest_step_target_for(user, TODAY) == 8500


@pytest.mark.django_db
def test_step_target_ignores_old_days():
    user = _user()
    _steps(user, 1, 8000)
    _steps(user, 20, 2000)  # outside 7-day window, ignored -> avg 8000 -> 8500
    assert suggest_step_target_for(user, TODAY) == 8500


@pytest.mark.django_db
def test_weekly_mileage_sums_completed_runs():
    user = _user()
    _run(user, 2, 5.0)
    _run(user, 4, 8.0)      # total 13.0 -> *1.10 = 14.3
    assert suggest_weekly_mileage_for(user, TODAY, is_deload=False) == 14.3


@pytest.mark.django_db
def test_weekly_mileage_excludes_uncompleted_and_old():
    user = _user()
    _run(user, 2, 5.0)
    _run(user, 3, 9.0, completed=False)   # excluded
    _run(user, 20, 100.0)                 # outside window
    assert suggest_weekly_mileage_for(user, TODAY, is_deload=False) == 5.5  # 5.0*1.10


@pytest.mark.django_db
def test_weekly_mileage_deload():
    user = _user()
    _run(user, 2, 10.0)
    assert suggest_weekly_mileage_for(user, TODAY, is_deload=True) == 7.0  # 10*0.7


@pytest.mark.django_db
def test_weekly_mileage_none_without_runs():
    assert suggest_weekly_mileage_for(_user(), TODAY, is_deload=False) is None


@pytest.mark.django_db
def test_body_weight_trend_down():
    user = _user()
    _weight(user, 1, 64.0)
    _weight(user, 3, 64.4)   # current window avg 64.2
    _weight(user, 9, 65.0)
    _weight(user, 11, 65.2)  # prior window avg 65.1
    t = body_weight_trend(user, TODAY)
    assert t is not None
    assert t.current_avg == 64.2
    assert t.prior_avg == 65.1
    assert t.direction == "down"


@pytest.mark.django_db
def test_body_weight_trend_none_with_fewer_than_two_current():
    user = _user()
    _weight(user, 1, 64.0)
    assert body_weight_trend(user, TODAY) is None


@pytest.mark.django_db
def test_body_weight_trend_excludes_other_users():
    user = _user("a")
    other = _user("b")
    _weight(other, 1, 90.0)
    _weight(other, 2, 91.0)
    assert body_weight_trend(user, TODAY) is None
