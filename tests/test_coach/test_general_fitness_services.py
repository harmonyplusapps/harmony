import pytest
from datetime import date, timedelta
from django.contrib.auth.models import User
from apps.fitness.models import FitnessPlan, WorkoutDay, WorkoutLog
from services.coach.general_fitness import consistent_week_streak

TODAY = date.today()


def _user(username="g"):
    return User.objects.create_user(username=username, password="x", email=f"{username}@e.com")


def _week(user, week_number, weeks_ago, day_types, completed_count, is_active=False):
    """Create a one-week plan ending `weeks_ago` weeks before today, with the given
    non-rest day_types, marking the first `completed_count` of them completed."""
    end = TODAY - timedelta(weeks=weeks_ago)
    start = end - timedelta(days=6)
    plan = FitnessPlan.objects.create(
        user=user, week_number=week_number, start_date=start, end_date=end,
        is_active=is_active, total_workout_days=len(day_types),
        weekly_goal_summary="g", claude_reasoning="r",
    )
    days = []
    for i, dt in enumerate(day_types):
        d = start + timedelta(days=i)
        wd = WorkoutDay.objects.create(
            fitness_plan=plan, date=d, day_of_week=d.strftime("%A"),
            day_type=dt, focus_area="full_body", estimated_duration_minutes=40,
        )
        days.append(wd)
    for wd in days[:completed_count]:
        WorkoutLog.objects.create(user=user, workout_day=wd, date=wd.date, completed=True)
    return plan


@pytest.mark.django_db
def test_streak_counts_consecutive_consistent_weeks():
    user = _user()
    _week(user, 2, weeks_ago=1, day_types=["strength", "running", "yoga"], completed_count=3)
    _week(user, 1, weeks_ago=2, day_types=["strength", "running", "yoga"], completed_count=3)
    assert consistent_week_streak(user, TODAY) == 2


@pytest.mark.django_db
def test_streak_stops_at_inconsistent_week():
    user = _user()
    _week(user, 3, weeks_ago=1, day_types=["strength", "running", "yoga"], completed_count=3)
    _week(user, 2, weeks_ago=2, day_types=["strength", "running", "yoga"], completed_count=1)
    _week(user, 1, weeks_ago=3, day_types=["strength", "running", "yoga"], completed_count=3)
    assert consistent_week_streak(user, TODAY) == 1


@pytest.mark.django_db
def test_streak_excludes_in_progress_week_and_rest_days():
    user = _user()
    _week(user, 2, weeks_ago=-1, day_types=["strength", "running", "yoga"], completed_count=0, is_active=True)
    _week(user, 1, weeks_ago=1, day_types=["strength", "yoga", "rest"], completed_count=2)
    assert consistent_week_streak(user, TODAY) == 1


@pytest.mark.django_db
def test_streak_zero_for_new_user():
    assert consistent_week_streak(_user(), TODAY) == 0


from decimal import Decimal
from apps.fitness.models import RunningStrategy
from services.coach.general_fitness import get_suggestions


def _run_week(user, week_number, weeks_ago, run_types, is_active=False):
    end = TODAY - timedelta(weeks=weeks_ago)
    start = end - timedelta(days=6)
    plan = FitnessPlan.objects.create(
        user=user, week_number=week_number, start_date=start, end_date=end,
        is_active=is_active, total_workout_days=len(run_types),
        weekly_goal_summary="g", claude_reasoning="r",
    )
    for i, rt in enumerate(run_types):
        d = start + timedelta(days=i)
        wd = WorkoutDay.objects.create(
            fitness_plan=plan, date=d, day_of_week=d.strftime("%A"),
            day_type="running", focus_area="cardio", estimated_duration_minutes=30,
        )
        RunningStrategy.objects.create(
            workout_day=wd, run_type=rt, total_distance_km=Decimal("5"),
            total_duration_minutes=30, pace_target="6:00/km",
        )
        WorkoutLog.objects.create(user=user, workout_day=wd, date=d, completed=True)
    return plan


@pytest.mark.django_db
def test_get_suggestions_bundles_streak_bump_and_addday():
    user = _user()
    _week(user, 2, weeks_ago=1, day_types=["strength", "strength", "yoga"], completed_count=3)
    _week(user, 1, weeks_ago=2, day_types=["strength", "strength", "yoga"], completed_count=3)
    _week(user, 3, weeks_ago=-1, day_types=["strength", "strength", "yoga"], completed_count=0, is_active=True)
    s = get_suggestions(user, TODAY)
    assert s.consistent_week_streak == 2
    assert s.duration_bump_min == 5 and s.duration_capped is False
    assert s.current_training_days == 3
    assert s.add_training_day is False
    assert s.run_rotation is None


@pytest.mark.django_db
def test_get_suggestions_suppresses_bump_on_deload_week():
    user = _user()
    _week(user, 2, weeks_ago=1, day_types=["strength", "strength", "yoga"], completed_count=3)
    _week(user, 1, weeks_ago=2, day_types=["strength", "strength", "yoga"], completed_count=3)
    _week(user, 4, weeks_ago=-1, day_types=["strength", "strength", "yoga"], completed_count=0, is_active=True)
    s = get_suggestions(user, TODAY)
    assert s.consistent_week_streak == 2
    assert s.duration_bump_min == 0 and s.duration_capped is False


@pytest.mark.django_db
def test_get_suggestions_run_rotation_on_monotonous_history():
    user = _user("r")
    _run_week(user, 1, weeks_ago=1, run_types=["easy", "easy", "easy"])
    s = get_suggestions(user, TODAY)
    assert s.run_rotation is not None
    assert s.run_rotation.recent_type == "easy"
    assert s.run_rotation.suggested_type == "interval"


@pytest.mark.django_db
def test_get_suggestions_empty_for_new_user():
    s = get_suggestions(_user("n"), TODAY)
    assert s.consistent_week_streak == 0
    assert s.duration_bump_min == 0
    assert s.add_training_day is False
    assert s.current_training_days == 0
    assert s.run_rotation is None
