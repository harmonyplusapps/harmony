import pytest
import json
from unittest.mock import patch, MagicMock
from pathlib import Path
from apps.exercises.models import ExerciseCache
from services.wger.client import fetch_and_cache_exercise, search_exercise_by_name

FIXTURE = json.loads((Path(__file__).parent.parent / "fixtures/wger_exercise_response.json").read_text())

@pytest.mark.django_db
def test_fetch_and_cache_exercise_creates_record():
    exercise_data = FIXTURE["results"][0]
    with patch("services.wger.client.httpx.get") as mock_get:
        mock_resp = MagicMock()
        mock_resp.json.return_value = FIXTURE
        mock_resp.raise_for_status.return_value = None
        mock_get.return_value = mock_resp
        result = fetch_and_cache_exercise("Bench Press")
    assert result is not None
    assert ExerciseCache.objects.filter(name="Bench Press").exists()

@pytest.mark.django_db
def test_fetch_and_cache_exercise_returns_cached():
    ExerciseCache.objects.create(
        wger_id=1, name="Bench Press", category="Chest",
        primary_muscles=[], secondary_muscles=[], gif_url=""
    )
    with patch("services.wger.client.httpx.get") as mock_get:
        result = fetch_and_cache_exercise("Bench Press")
        mock_get.assert_not_called()
    assert result.name == "Bench Press"

@pytest.mark.django_db
def test_fetch_returns_none_when_not_found():
    with patch("services.wger.client.httpx.get") as mock_get:
        mock_resp = MagicMock()
        mock_resp.json.return_value = {"count": 0, "results": []}
        mock_resp.raise_for_status.return_value = None
        mock_get.return_value = mock_resp
        result = fetch_and_cache_exercise("Nonexistent Exercise")
    assert result is None
