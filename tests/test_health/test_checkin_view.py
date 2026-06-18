import pytest
from datetime import date
from django.urls import reverse
from django.contrib.auth.models import User
from apps.accounts.models import UserProfile
from apps.health.models import SorenessLog, WellnessLog, PeriodLog


def _make_user(tracks_cycle=False):
    u = User.objects.create_user(username="c", password="testpass123", email="c@e.com")
    UserProfile.objects.create(
        user=u, height_cm=170, weight_kg=65, gender="female",
        date_of_birth=date(1992, 3, 3), fitness_experience="beginner",
        primary_goal="Get active", diet_type="omnivore", food_allergies=[],
        daily_routine="", wake_time="07:00", sleep_time="23:00",
        work_schedule="9-5", workout_days_per_week=3, preferred_workout_days=[],
        workout_location="home", available_equipment=[],
        notification_email="c@e.com", tracks_cycle=tracks_cycle,
    )
    return u


@pytest.mark.django_db
def test_checkin_redirects_unauthenticated(client):
    resp = client.get(reverse("health_checkin"))
    assert resp.status_code == 302
    assert "/accounts/login" in resp["Location"]


@pytest.mark.django_db
def test_checkin_get_returns_200(client, db):
    _make_user()
    client.login(username="c", password="testpass123")
    resp = client.get(reverse("health_checkin"))
    assert resp.status_code == 200


@pytest.mark.django_db
def test_checkin_hides_cycle_controls_when_not_tracked(client, db):
    _make_user(tracks_cycle=False)
    client.login(username="c", password="testpass123")
    resp = client.get(reverse("health_checkin"))
    assert "Period started today" not in resp.content.decode()


@pytest.mark.django_db
def test_checkin_shows_cycle_controls_when_tracked(client, db):
    _make_user(tracks_cycle=True)
    client.login(username="c", password="testpass123")
    resp = client.get(reverse("health_checkin"))
    assert "Period started today" in resp.content.decode()


@pytest.mark.django_db
def test_checkin_post_saves_soreness_steps_and_resting_hr(client, db):
    _make_user()
    client.login(username="c", password="testpass123")
    resp = client.post(reverse("health_checkin"), {
        "soreness_quads": "severe",
        "soreness_core": "mild",
        "steps": "7400",
        "resting_hr_bpm": "60",
    })
    assert resp.status_code == 200
    today = date.today()
    sore = {s.muscle_group: s.severity for s in SorenessLog.objects.filter(user__username="c", date=today)}
    assert sore == {"quads": "severe", "core": "mild"}
    log = WellnessLog.objects.get(user__username="c", date=today)
    assert log.steps == 7400
    assert log.resting_hr_bpm == 60


@pytest.mark.django_db
def test_checkin_post_replaces_existing_soreness(client, db):
    user = _make_user()
    SorenessLog.objects.create(user=user, date=date.today(), muscle_group="back", severity="moderate")
    client.login(username="c", password="testpass123")
    client.post(reverse("health_checkin"), {"soreness_quads": "mild"})
    groups = {s.muscle_group for s in SorenessLog.objects.filter(user=user, date=date.today())}
    assert groups == {"quads"}


@pytest.mark.django_db
def test_checkin_post_period_button_creates_periodlog(client, db):
    user = _make_user(tracks_cycle=True)
    client.login(username="c", password="testpass123")
    client.post(reverse("health_checkin"), {"period_started": "true"})
    assert PeriodLog.objects.filter(user=user, start_date=date.today()).exists()
