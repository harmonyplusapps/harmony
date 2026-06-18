import pytest
from datetime import date, timedelta
from django.contrib.auth.models import User
from apps.accounts.models import UserProfile
from apps.health.models import WellnessLog, SorenessLog, PeriodLog
from apps.fitness.models import FitnessPlan, WorkoutDay, WorkoutLog
from services.health.snapshot import get_health_snapshot, HealthSnapshot, SorenessItem


@pytest.fixture
def user(db):
    u = User.objects.create_user(username="s", password="x", email="s@e.com")
    UserProfile.objects.create(
        user=u, height_cm=170, weight_kg=65, gender="female",
        date_of_birth=date(1992, 3, 3), fitness_experience="beginner",
        primary_goal="Get active", diet_type="omnivore", food_allergies=[],
        daily_routine="", wake_time="07:00", sleep_time="23:00",
        work_schedule="9-5", workout_days_per_week=3, preferred_workout_days=[],
        workout_location="home", available_equipment=[],
        notification_email="s@e.com", tracks_cycle=True,
    )
    return u


def _completed_workout(user, on_date):
    plan = FitnessPlan.objects.create(
        user=user, week_number=1, start_date=on_date, end_date=on_date,
        total_workout_days=1, weekly_goal_summary="g", claude_reasoning="r",
    )
    day = WorkoutDay.objects.create(
        fitness_plan=plan, date=on_date, day_of_week="Monday",
        day_type="strength", focus_area="lower_body", estimated_duration_minutes=45,
    )
    return WorkoutLog.objects.create(
        user=user, workout_day=day, date=on_date, completed=True, completion_percentage=100,
    )


@pytest.mark.django_db
def test_snapshot_empty_day_degrades_gracefully(user):
    snap = get_health_snapshot(user, date(2026, 6, 17))
    assert isinstance(snap, HealthSnapshot)
    assert snap.sleep_hours is None
    assert snap.energy is None
    assert snap.soreness == []
    assert snap.cycle_phase is None
    assert snap.steps is None
    assert snap.resting_hr is None
    assert snap.momentum.bucket == "no_history"
    assert list(snap.recent_workouts) == []


@pytest.mark.django_db
def test_snapshot_assembles_logged_data(user):
    on = date(2026, 6, 17)
    WellnessLog.objects.create(
        user=user, date=on, sleep_hours=7, sleep_quality=4, mood_score=6,
        stress_level=3, energy_level=8, steps=9000, resting_hr_bpm=55,
    )
    SorenessLog.objects.create(user=user, date=on, muscle_group="quads", severity="severe")
    SorenessLog.objects.create(user=user, date=on, muscle_group="core", severity="mild")
    PeriodLog.objects.create(user=user, start_date=on - timedelta(2))  # day 3 -> period
    _completed_workout(user, on)

    snap = get_health_snapshot(user, on)
    assert snap.sleep_hours == 7
    assert snap.energy == 8
    assert snap.stress == 3
    assert snap.steps == 9000
    assert snap.resting_hr == 55
    assert SorenessItem("quads", "severe") in snap.soreness
    assert SorenessItem("core", "mild") in snap.soreness
    assert snap.cycle_phase == "period"
    assert snap.momentum.bucket == "current"
    assert len(snap.recent_workouts) == 1


@pytest.mark.django_db
def test_snapshot_cycle_phase_none_when_not_tracked(user):
    user.profile.tracks_cycle = False
    user.profile.save()
    PeriodLog.objects.create(user=user, start_date=date(2026, 6, 15))
    snap = get_health_snapshot(user, date(2026, 6, 17))
    assert snap.cycle_phase is None


@pytest.mark.django_db
def test_snapshot_uses_most_recent_period_on_or_before_date(user):
    PeriodLog.objects.create(user=user, start_date=date(2026, 5, 1))
    PeriodLog.objects.create(user=user, start_date=date(2026, 6, 16))  # day 2 on the 17th
    snap = get_health_snapshot(user, date(2026, 6, 17))
    assert snap.cycle_phase == "period"
