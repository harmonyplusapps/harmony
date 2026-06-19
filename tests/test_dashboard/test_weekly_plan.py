import pytest
from datetime import date
from django.urls import reverse
from django.contrib.auth.models import User
from apps.accounts.models import UserProfile
from apps.fitness.models import FitnessPlan, WorkoutDay
from apps.health.models import HealthPlan, MealPlan


@pytest.fixture
def user_with_plan(db):
    user = User.objects.create_user(username="planuser", password="testpass123")
    UserProfile.objects.create(
        user=user,
        height_cm=170, weight_kg=70, gender="female",
        date_of_birth=date(1995, 1, 1),
        fitness_experience="beginner",
        primary_goal="Lose weight",
        diet_type="omnivore",
        food_allergies=[],
        food_preferences="",
        daily_routine="Work from home",
        wake_time="07:00", sleep_time="23:00",
        work_schedule="9-5",
        workout_days_per_week=3,
        preferred_workout_days=["Monday", "Wednesday", "Friday"],
        running_days_per_week=1,
        workout_location="home",
        available_equipment=[],
        notification_email="plan@example.com",
        onboarding_completed=True,
    )
    fitness_plan = FitnessPlan.objects.create(
        user=user,
        week_number=1,
        start_date=date(2026, 6, 8),
        end_date=date(2026, 6, 14),
        total_workout_days=3,
        total_running_days=1,
        weekly_goal_summary="Build base fitness",
        claude_reasoning="Started with beginner-friendly plan",
        is_active=True,
    )
    WorkoutDay.objects.create(
        fitness_plan=fitness_plan,
        date=date(2026, 6, 9),
        day_of_week="Monday",
        day_type="strength",
        focus_area="full_body",
        estimated_duration_minutes=45,
    )
    health_plan = HealthPlan.objects.create(
        user=user,
        week_number=1,
        start_date=date(2026, 6, 8),
        end_date=date(2026, 6, 14),
        daily_calorie_target=1800,
        daily_protein_g=130,
        daily_carbs_g=180,
        daily_fat_g=60,
        daily_fiber_g=25,
        daily_water_ml=2500,
        claude_reasoning="Moderate deficit for fat loss",
        is_active=True,
    )
    MealPlan.objects.create(
        health_plan=health_plan,
        day_of_week="Monday",
        meal_type="breakfast",
        meal_name="Oats with berries",
        description="Steel-cut oats",
        calories=350,
        protein_g=12,
        carbs_g=55,
        fat_g=8,
        fiber_g=6,
        ingredients=["oats", "berries"],
        order=0,
    )
    return user


@pytest.mark.django_db
def test_weekly_plan_redirects_unauthenticated(client):
    resp = client.get(reverse("weekly_plan"))
    assert resp.status_code == 302
    assert "/accounts/login" in resp["Location"]


@pytest.mark.django_db
def test_weekly_plan_redirects_if_not_onboarded(client, base_user):
    client.login(username="base", password="testpass123")
    resp = client.get(reverse("weekly_plan"))
    assert resp.status_code == 302
    assert "onboarding" in resp["Location"]


@pytest.mark.django_db
def test_weekly_plan_shows_no_plan_message(client, complete_profile):
    client.login(username="base", password="testpass123")
    resp = client.get(reverse("weekly_plan"))
    assert resp.status_code == 200
    assert "No active plan" in resp.content.decode()
    assert resp.context["is_deload"] is False
    assert resp.context["weight_suggestions"] == {}


@pytest.mark.django_db
def test_weekly_plan_renders_all_days(client, user_with_plan):
    client.login(username="planuser", password="testpass123")
    resp = client.get(reverse("weekly_plan"))
    assert resp.status_code == 200
    content = resp.content.decode()
    for day in ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]:
        assert day in content


@pytest.mark.django_db
def test_weekly_plan_renders_workout_data(client, user_with_plan):
    client.login(username="planuser", password="testpass123")
    resp = client.get(reverse("weekly_plan"))
    assert resp.status_code == 200
    content = resp.content.decode()
    assert "Strength" in content
    assert "Build base fitness" in content


@pytest.mark.django_db
def test_weekly_plan_renders_meal_data(client, user_with_plan):
    client.login(username="planuser", password="testpass123")
    resp = client.get(reverse("weekly_plan"))
    assert resp.status_code == 200
    assert "Oats with berries" in resp.content.decode()
