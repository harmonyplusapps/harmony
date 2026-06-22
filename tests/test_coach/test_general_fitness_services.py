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
