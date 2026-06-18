import pytest
from datetime import date
from django.urls import reverse
from django.contrib.auth.models import User
from apps.accounts.models import UserProfile


@pytest.fixture
def nav_user(db):
    u = User.objects.create_user(username="n", password="testpass123", email="n@e.com")
    UserProfile.objects.create(
        user=u, height_cm=170, weight_kg=65, gender="female",
        date_of_birth=date(1992, 3, 3), fitness_experience="beginner",
        primary_goal="Get active", diet_type="omnivore", food_allergies=[],
        daily_routine="", wake_time="07:00", sleep_time="23:00",
        work_schedule="9-5", workout_days_per_week=3, preferred_workout_days=[],
        workout_location="home", available_equipment=[],
        notification_email="n@e.com", onboarding_completed=True,
    )
    return u


@pytest.mark.django_db
def test_dashboard_sidebar_links_to_checkin(client, nav_user):
    client.login(username="n", password="testpass123")
    resp = client.get(reverse("dashboard"))
    assert reverse("health_checkin") in resp.content.decode()
