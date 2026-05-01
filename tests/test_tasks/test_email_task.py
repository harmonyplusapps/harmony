import pytest
from datetime import date
from unittest.mock import patch, MagicMock
from django.contrib.auth.models import User
from apps.accounts.models import UserProfile
from apps.notifications.models import EmailLog
from tasks.email import send_daily_emails


@pytest.fixture
def active_user(db):
    user = User.objects.create_user(username="emailuser", password="pass")
    UserProfile.objects.create(
        user=user, height_cm=170, weight_kg=70, gender="female",
        date_of_birth="1995-01-01", fitness_experience="beginner",
        primary_goal="Get fit", diet_type="omnivore",
        food_allergies=[], wake_time="07:00", sleep_time="23:00",
        work_schedule="9-5", workout_days_per_week=3,
        preferred_workout_days=["Monday", "Wednesday", "Friday"],
        running_days_per_week=0, workout_location="home",
        available_equipment=[], notification_email="user@example.com",
        onboarding_completed=True,
    )
    return user


@pytest.mark.django_db
def test_send_daily_emails_creates_email_log(active_user):
    with patch("tasks.email.generate_email_summary") as mock_summary, \
         patch("tasks.email.send_mail") as mock_mail:
        mock_summary.return_value = ("Great job today!", "on_track", "on_track")
        send_daily_emails()
    assert EmailLog.objects.filter(user=active_user, status="sent").exists()


@pytest.mark.django_db
def test_send_daily_emails_skips_duplicate(active_user):
    today = date.today()
    EmailLog.objects.create(
        user=active_user, date=today, status="sent",
        fitness_status="on_track", health_status="on_track",
        body_preview="Already sent"
    )
    with patch("tasks.email.generate_email_summary") as mock_summary:
        send_daily_emails()
        mock_summary.assert_not_called()


@pytest.mark.django_db
def test_send_daily_emails_logs_failure_on_error(active_user):
    with patch("tasks.email.generate_email_summary", side_effect=Exception("API down")), \
         patch("tasks.email.send_mail"):
        send_daily_emails()
    log = EmailLog.objects.get(user=active_user)
    assert log.status == "failed"
    assert "API down" in log.error_message
