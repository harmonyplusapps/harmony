import pytest
from datetime import date
from django.db import IntegrityError
from django.contrib.auth.models import User
from apps.health.models import SorenessLog, PeriodLog, WellnessLog, MUSCLE_GROUP_TO_FOCUS
from apps.accounts.models import UserProfile


@pytest.fixture
def user(db):
    return User.objects.create_user(username="h", password="x", email="h@e.com")


@pytest.mark.django_db
def test_wellnesslog_has_optional_steps_and_resting_hr(user):
    log = WellnessLog.objects.create(
        user=user, date=date(2026, 6, 17),
        sleep_hours=7, sleep_quality=4, mood_score=6,
        stress_level=4, energy_level=7,
    )
    assert log.steps is None
    assert log.resting_hr_bpm is None
    log.steps = 8200
    log.resting_hr_bpm = 58
    log.save()
    log.refresh_from_db()
    assert log.steps == 8200
    assert log.resting_hr_bpm == 58


@pytest.mark.django_db
def test_sorenesslog_unique_per_user_date_group(user):
    SorenessLog.objects.create(
        user=user, date=date(2026, 6, 17), muscle_group="quads", severity="severe",
    )
    with pytest.raises(IntegrityError):
        SorenessLog.objects.create(
            user=user, date=date(2026, 6, 17), muscle_group="quads", severity="mild",
        )


@pytest.mark.django_db
def test_periodlog_unique_per_user_start_date(user):
    PeriodLog.objects.create(user=user, start_date=date(2026, 6, 1))
    with pytest.raises(IntegrityError):
        PeriodLog.objects.create(user=user, start_date=date(2026, 6, 1))


@pytest.mark.django_db
def test_muscle_group_to_focus_mapping_covers_all_choices():
    groups = {c[0] for c in SorenessLog.MUSCLE_GROUP_CHOICES}
    assert groups == set(MUSCLE_GROUP_TO_FOCUS.keys())
    assert MUSCLE_GROUP_TO_FOCUS["chest"] == "upper_body"
    assert MUSCLE_GROUP_TO_FOCUS["quads"] == "lower_body"
    assert MUSCLE_GROUP_TO_FOCUS["core"] == "core"


@pytest.mark.django_db
def test_userprofile_cycle_defaults(user):
    profile = UserProfile.objects.create(
        user=user, height_cm=170, weight_kg=65, gender="female",
        date_of_birth=date(1992, 3, 3), fitness_experience="beginner",
        primary_goal="Get active", diet_type="omnivore", food_allergies=[],
        daily_routine="", wake_time="07:00", sleep_time="23:00",
        work_schedule="9-5", workout_days_per_week=3, preferred_workout_days=[],
        workout_location="home", available_equipment=[],
        notification_email="h@e.com",
    )
    assert profile.tracks_cycle is False
    assert profile.average_cycle_length == 28
