import pytest
import json
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch
from django.contrib.auth.models import User
from apps.accounts.models import UserProfile
from apps.fitness.models import FitnessPlan
from apps.health.models import HealthPlan
from services.claude.plan_generator import generate_initial_plans
from datetime import date

FIXTURE = json.loads((Path(__file__).parent.parent / "fixtures/claude_plan_response.json").read_text())


@pytest.fixture
def user_with_profile(db):
    user = User.objects.create_user(username="testuser2", password="pass")
    UserProfile.objects.create(
        user=user, height_cm=175, weight_kg=80, gender="male",
        date_of_birth=date(1990, 1, 1), fitness_experience="beginner",
        primary_goal="Lose 5kg", diet_type="omnivore",
        food_allergies=[], wake_time="07:00", sleep_time="23:00",
        work_schedule="9-5", workout_days_per_week=3,
        preferred_workout_days=["Monday", "Wednesday", "Friday"],
        running_days_per_week=2, workout_location="gym",
        available_equipment=["barbell", "dumbbells"],
        notification_email="test@example.com",
    )
    return user


@pytest.mark.asyncio
async def test_generate_initial_plans_calls_claude_and_parses(user_with_profile):
    mock_message = MagicMock()
    mock_message.content = [MagicMock(text=json.dumps(FIXTURE))]

    with patch("services.claude.plan_generator.get_client") as mock_get_client:
        mock_client = MagicMock()
        mock_client.messages.acreate = AsyncMock(return_value=mock_message)
        mock_get_client.return_value = mock_client

        with patch("services.wger.client.httpx.get") as mock_wger:
            mock_resp = MagicMock()
            mock_resp.json.return_value = {"count": 0, "results": []}
            mock_resp.raise_for_status.return_value = None
            mock_wger.return_value = mock_resp

            fitness_plan, health_plan = await generate_initial_plans(user_with_profile)

    assert fitness_plan.week_number == 1
    assert health_plan.week_number == 1
