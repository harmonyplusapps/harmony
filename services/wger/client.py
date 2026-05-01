import re
import httpx
from django.conf import settings
from apps.exercises.models import ExerciseCache


def _strip_html(text: str) -> str:
    return re.sub(r"<[^>]+>", "", text).strip()


def fetch_and_cache_exercise(name: str) -> ExerciseCache | None:
    cached = ExerciseCache.objects.filter(name__iexact=name).first()
    if cached:
        return cached

    base_url = settings.WGER_API_BASE_URL
    resp = httpx.get(
        f"{base_url}/exercise/search/",
        params={"term": name, "language": "english", "format": "json"},
    )
    resp.raise_for_status()
    data = resp.json()

    if not data.get("results"):
        return None

    hit = data["results"][0]
    muscles = hit.get("muscles", [])
    muscles_secondary = hit.get("muscles_secondary", [])
    equipment = hit.get("equipment", [])
    images = hit.get("images", [])
    gif_url = images[0]["image"] if images else ""

    exercise, _ = ExerciseCache.objects.update_or_create(
        wger_id=hit["id"],
        defaults={
            "name": hit["name"],
            "category": hit.get("category", {}).get("name", ""),
            "primary_muscles": [m["name_en"] for m in muscles],
            "secondary_muscles": [m["name_en"] for m in muscles_secondary],
            "equipment": ", ".join(e["name"] for e in equipment),
            "description": _strip_html(hit.get("description", "")),
            "gif_url": gif_url,
        },
    )
    return exercise


def search_exercise_by_name(name: str) -> ExerciseCache | None:
    return fetch_and_cache_exercise(name)
