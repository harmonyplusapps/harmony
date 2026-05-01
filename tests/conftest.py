import pytest
from django.contrib.auth.models import User
from datetime import date
from apps.accounts.models import UserProfile


@pytest.fixture
def base_user(db):
    return User.objects.create_user(username="base", password="testpass123", email="base@example.com")


@pytest.fixture
def complete_profile(base_user):
    return UserProfile.objects.create(
        user=base_user,
        height_cm=175, weight_kg=75, gender="male",
        date_of_birth=date(1990, 6, 15),
        fitness_experience="intermediate",
        primary_goal="Build muscle and improve endurance",
        diet_type="omnivore",
        food_allergies=["peanuts"],
        food_preferences="High protein meals",
        daily_routine="Office job 9-5, commute 30 min each way",
        wake_time="06:30", sleep_time="22:30",
        work_schedule="9-5",
        workout_days_per_week=3,
        preferred_workout_days=["Monday", "Wednesday", "Friday"],
        running_days_per_week=2,
        workout_location="gym",
        available_equipment=["barbell", "dumbbells", "cable machine"],
        notification_email="base@example.com",
        onboarding_completed=True,
    )
