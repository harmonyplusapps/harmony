import pytest
import json
from pathlib import Path
from datetime import date
from django.contrib.auth.models import User
from apps.fitness.models import FitnessPlan, WorkoutDay, WorkoutExercise, RunningStrategy
from apps.health.models import HealthPlan, MealPlan
from services.claude.plan_parser import parse_and_save_plans

FIXTURE = json.loads((Path(__file__).parent.parent / "fixtures/claude_plan_response.json").read_text())


@pytest.fixture
def user(db):
    return User.objects.create_user(username="testuser", password="pass")


def test_parse_creates_fitness_plan(user):
    parse_and_save_plans(user, FIXTURE)
    assert FitnessPlan.objects.filter(user=user, week_number=1).exists()


def test_parse_creates_workout_days(user):
    parse_and_save_plans(user, FIXTURE)
    plan = FitnessPlan.objects.get(user=user, week_number=1)
    assert plan.workout_days.count() == 2


def test_parse_creates_exercises(user):
    parse_and_save_plans(user, FIXTURE)
    day = WorkoutDay.objects.get(day_of_week="Monday")
    assert day.exercises.count() == 2


def test_parse_creates_running_strategy(user):
    parse_and_save_plans(user, FIXTURE)
    day = WorkoutDay.objects.get(day_of_week="Thursday")
    assert hasattr(day, "running_strategy")
    assert day.running_strategy.run_type == "easy"


def test_parse_creates_health_plan(user):
    parse_and_save_plans(user, FIXTURE)
    assert HealthPlan.objects.filter(user=user, week_number=1).exists()


def test_parse_creates_meal_plans(user):
    parse_and_save_plans(user, FIXTURE)
    plan = HealthPlan.objects.get(user=user, week_number=1)
    assert plan.meal_plans.count() == 1


def test_parse_is_atomic(user):
    bad_data = dict(FIXTURE)
    bad_data["health_plan"] = {"invalid": True}
    with pytest.raises(Exception):
        parse_and_save_plans(user, bad_data)
    assert FitnessPlan.objects.filter(user=user).count() == 0
