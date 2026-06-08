import pytest
from datetime import date
from apps.accounts.forms import ProfileEditForm
from apps.accounts.models import UserProfile
from django.contrib.auth.models import User


@pytest.fixture
def profile_with_json(db):
    user = User.objects.create_user(username="edituser", password="pass")
    return UserProfile.objects.create(
        user=user,
        height_cm=170, weight_kg=70, gender="female",
        date_of_birth=date(1995, 3, 10),
        fitness_experience="beginner",
        primary_goal="Lose weight",
        diet_type="vegan",
        food_allergies=["gluten", "dairy"],
        food_preferences="Low oil",
        daily_routine="Work from home",
        wake_time="07:00", sleep_time="23:00",
        work_schedule="flexible",
        workout_days_per_week=4,
        preferred_workout_days=["Monday", "Wednesday", "Friday", "Sunday"],
        running_days_per_week=1,
        workout_location="home",
        available_equipment=["resistance bands", "dumbbells"],
        injury_history="Left knee strain",
        medical_conditions="",
        notification_email="edit@example.com",
        onboarding_completed=True,
    )


@pytest.mark.django_db
def test_form_pre_fills_preferred_workout_days(profile_with_json):
    form = ProfileEditForm(instance=profile_with_json)
    assert form.initial["preferred_workout_days"] == ["Monday", "Wednesday", "Friday", "Sunday"]


@pytest.mark.django_db
def test_form_pre_fills_available_equipment(profile_with_json):
    form = ProfileEditForm(instance=profile_with_json)
    assert form.initial["available_equipment"] == "resistance bands, dumbbells"


@pytest.mark.django_db
def test_form_pre_fills_food_allergies(profile_with_json):
    form = ProfileEditForm(instance=profile_with_json)
    assert form.initial["food_allergies"] == "gluten, dairy"


@pytest.mark.django_db
def test_form_clean_available_equipment_returns_list(profile_with_json):
    data = {
        "height_cm": "170", "weight_kg": "70", "gender": "female",
        "date_of_birth": "1995-03-10", "fitness_experience": "beginner",
        "primary_goal": "Lose weight", "diet_type": "vegan",
        "food_allergies": "nuts",
        "food_preferences": "", "daily_routine": "",
        "wake_time": "07:00", "sleep_time": "23:00",
        "work_schedule": "flexible",
        "workout_days_per_week": "4",
        "preferred_workout_days": ["Monday", "Wednesday"],
        "running_days_per_week": "1",
        "workout_location": "home",
        "available_equipment": "dumbbells, kettlebell",
        "injury_history": "", "medical_conditions": "",
        "notification_email": "edit@example.com",
    }
    form = ProfileEditForm(data, instance=profile_with_json)
    assert form.is_valid(), form.errors
    assert form.cleaned_data["available_equipment"] == ["dumbbells", "kettlebell"]


@pytest.mark.django_db
def test_form_clean_food_allergies_returns_list(profile_with_json):
    data = {
        "height_cm": "170", "weight_kg": "70", "gender": "female",
        "date_of_birth": "1995-03-10", "fitness_experience": "beginner",
        "primary_goal": "Lose weight", "diet_type": "vegan",
        "food_allergies": "gluten, soy",
        "food_preferences": "", "daily_routine": "",
        "wake_time": "07:00", "sleep_time": "23:00",
        "work_schedule": "flexible",
        "workout_days_per_week": "4",
        "preferred_workout_days": ["Monday"],
        "running_days_per_week": "1",
        "workout_location": "home",
        "available_equipment": "",
        "injury_history": "", "medical_conditions": "",
        "notification_email": "edit@example.com",
    }
    form = ProfileEditForm(data, instance=profile_with_json)
    assert form.is_valid(), form.errors
    assert form.cleaned_data["food_allergies"] == ["gluten", "soy"]


@pytest.mark.django_db
def test_form_empty_equipment_returns_empty_list(profile_with_json):
    data = {
        "height_cm": "170", "weight_kg": "70", "gender": "female",
        "date_of_birth": "1995-03-10", "fitness_experience": "beginner",
        "primary_goal": "Lose weight", "diet_type": "vegan",
        "food_allergies": "",
        "food_preferences": "", "daily_routine": "",
        "wake_time": "07:00", "sleep_time": "23:00",
        "work_schedule": "flexible",
        "workout_days_per_week": "4",
        "preferred_workout_days": ["Monday"],
        "running_days_per_week": "1",
        "workout_location": "home",
        "available_equipment": "",
        "injury_history": "", "medical_conditions": "",
        "notification_email": "edit@example.com",
    }
    form = ProfileEditForm(data, instance=profile_with_json)
    assert form.is_valid(), form.errors
    assert form.cleaned_data["available_equipment"] == []
