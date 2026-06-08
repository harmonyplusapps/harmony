import pytest
from datetime import date
from django.urls import reverse
from django.contrib.auth.models import User
from apps.accounts.models import UserProfile


@pytest.fixture
def onboarded_user(db):
    user = User.objects.create_user(
        username="dashuser", password="testpass123",
        first_name="Alex", last_name="Smith",
    )
    UserProfile.objects.create(
        user=user,
        height_cm=175, weight_kg=70, gender="male",
        date_of_birth=date(1995, 1, 1),
        fitness_experience="intermediate",
        primary_goal="Build muscle",
        diet_type="omnivore",
        food_allergies=[],
        food_preferences="",
        daily_routine="Office job",
        wake_time="07:00", sleep_time="23:00",
        work_schedule="9-5",
        workout_days_per_week=4,
        preferred_workout_days=["Monday", "Tuesday", "Thursday", "Friday"],
        running_days_per_week=0,
        workout_location="gym",
        available_equipment=["barbell", "dumbbells"],
        notification_email="alex@example.com",
        onboarding_completed=True,
    )
    return user


@pytest.mark.django_db
def test_dashboard_redirects_unauthenticated(client):
    resp = client.get(reverse("dashboard"))
    assert resp.status_code == 302
    assert "/accounts/login" in resp["Location"]


@pytest.mark.django_db
def test_dashboard_returns_200(client, onboarded_user):
    client.login(username="dashuser", password="testpass123")
    resp = client.get(reverse("dashboard"))
    assert resp.status_code == 200


@pytest.mark.django_db
def test_dashboard_context_has_profile(client, onboarded_user):
    client.login(username="dashuser", password="testpass123")
    resp = client.get(reverse("dashboard"))
    assert resp.context["profile"] is not None
    assert resp.context["profile"].primary_goal == "Build muscle"


@pytest.mark.django_db
def test_dashboard_context_has_progress_dots(client, onboarded_user):
    client.login(username="dashuser", password="testpass123")
    resp = client.get(reverse("dashboard"))
    assert "progress_dots" in resp.context
    assert isinstance(resp.context["progress_dots"], list)


@pytest.mark.django_db
def test_dashboard_renders_user_full_name(client, onboarded_user):
    client.login(username="dashuser", password="testpass123")
    resp = client.get(reverse("dashboard"))
    assert "Alex Smith" in resp.content.decode()


@pytest.mark.django_db
def test_dashboard_renders_primary_goal(client, onboarded_user):
    client.login(username="dashuser", password="testpass123")
    resp = client.get(reverse("dashboard"))
    assert "Build muscle" in resp.content.decode()


@pytest.mark.django_db
def test_dashboard_renders_logo_wordmark(client, onboarded_user):
    client.login(username="dashuser", password="testpass123")
    resp = client.get(reverse("dashboard"))
    content = resp.content.decode()
    assert "wordmark-name" in content
    assert "Your fitness companion" in content


@pytest.mark.django_db
def test_dashboard_renders_sidebar(client, onboarded_user):
    client.login(username="dashuser", password="testpass123")
    resp = client.get(reverse("dashboard"))
    content = resp.content.decode()
    assert "app-sidebar" in content
    assert reverse("weekly_plan") in content
    assert reverse("profile_edit") in content


@pytest.mark.django_db
def test_dashboard_renders_no_plan_message_when_no_plan(client, onboarded_user):
    client.login(username="dashuser", password="testpass123")
    resp = client.get(reverse("dashboard"))
    assert "No plan yet" in resp.content.decode()
