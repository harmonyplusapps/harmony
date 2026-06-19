import pytest
from datetime import date, timedelta
from django.contrib.auth.models import User
from apps.accounts.models import UserProfile
from apps.exercises.models import ExerciseCache
from apps.fitness.models import (
    FitnessPlan, WorkoutDay, WorkoutExercise, WorkoutLog, ExerciseLog,
)
from services.coach.progression import suggest_strength_progression


def _user(username="pr"):
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


def _session(user, weights, days_ago, custom_name="Goblet Squat", cache=None,
             met=True, sets=3, reps=10, week=1):
    d = date.today() - timedelta(days=days_ago)
    plan = FitnessPlan.objects.create(
        user=user, week_number=week, start_date=d, end_date=d, is_active=False,
        total_workout_days=1, weekly_goal_summary="g", claude_reasoning="r",
    )
    wd = WorkoutDay.objects.create(
        fitness_plan=plan, date=d, day_of_week=d.strftime("%A"),
        day_type="strength", focus_area="lower_body", estimated_duration_minutes=45,
    )
    ex = WorkoutExercise.objects.create(
        workout_day=wd, section="main", sets=sets, reps=reps,
        custom_name="" if cache else custom_name, exercise_cache=cache,
        intensity="moderate",
    )
    wl = WorkoutLog.objects.create(user=user, workout_day=wd, date=d, completed=True)
    reps_completed = [reps] * sets if met else [reps - 5] * sets
    ExerciseLog.objects.create(
        workout_log=wl, workout_exercise=ex,
        sets_completed=sets if met else sets - 1,
        reps_completed=reps_completed, weight_kg=weights,
    )


def _current(user, custom_name="Goblet Squat", cache=None):
    today = date.today()
    plan = FitnessPlan.objects.create(
        user=user, week_number=3, start_date=today, end_date=today, is_active=True,
        total_workout_days=1, weekly_goal_summary="g", claude_reasoning="r",
    )
    wd = WorkoutDay.objects.create(
        fitness_plan=plan, date=today, day_of_week=today.strftime("%A"),
        day_type="strength", focus_area="lower_body", estimated_duration_minutes=45,
    )
    ex = WorkoutExercise.objects.create(
        workout_day=wd, section="main", sets=3, reps=10,
        custom_name="" if cache else custom_name, exercise_cache=cache,
        intensity="moderate",
    )
    return wd, ex


@pytest.mark.django_db
def test_progress_after_two_met_weeks_custom_name():
    user = _user()
    _session(user, [40, 40, 40], days_ago=14)
    _session(user, [40, 40, 40], days_ago=7)
    cwd, cex = _current(user)
    s = suggest_strength_progression(user, cwd, is_deload=False)[cex.id]
    assert s.reason == "progress"
    assert s.suggested_weight_kg == 42.5


@pytest.mark.django_db
def test_new_when_no_history():
    user = _user()
    cwd, cex = _current(user, custom_name="Bench Press")
    s = suggest_strength_progression(user, cwd, is_deload=False)[cex.id]
    assert s.reason == "new"
    assert s.suggested_weight_kg is None


@pytest.mark.django_db
def test_backoff_after_two_misses():
    user = _user()
    _session(user, [60, 60, 60], days_ago=14, custom_name="Deadlift", met=False)
    _session(user, [60, 60, 60], days_ago=7, custom_name="Deadlift", met=False)
    cwd, cex = _current(user, custom_name="Deadlift")
    s = suggest_strength_progression(user, cwd, is_deload=False)[cex.id]
    assert s.reason == "backoff"
    assert s.suggested_weight_kg == 55.0  # 60*0.9=54 -> nearest 2.5


@pytest.mark.django_db
def test_identity_matches_via_exercise_cache():
    user = _user()
    cache = ExerciseCache.objects.create(wger_id=1, name="Back Squat", category="legs")
    _session(user, [80, 80, 80], days_ago=14, cache=cache)
    _session(user, [80, 80, 80], days_ago=7, cache=cache)
    cwd, cex = _current(user, cache=cache)
    s = suggest_strength_progression(user, cwd, is_deload=False)[cex.id]
    assert s.reason == "progress"
    assert s.suggested_weight_kg == 82.5


@pytest.mark.django_db
def test_deload_trims_suggestion():
    user = _user()
    _session(user, [30, 30, 30], days_ago=14, custom_name="Overhead Press")
    _session(user, [30, 30, 30], days_ago=7, custom_name="Overhead Press")
    cwd, cex = _current(user, custom_name="Overhead Press")
    s = suggest_strength_progression(user, cwd, is_deload=True)[cex.id]
    assert s.reason == "deload"
    assert s.suggested_weight_kg == 25.0  # 30*0.8=24 -> nearest 2.5
