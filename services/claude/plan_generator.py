import json
from django.contrib.auth.models import User
from apps.accounts.models import UserProfile
from services.claude.client import get_client
from services.claude.prompts import PLAN_GENERATION_SYSTEM_PROMPT
from services.claude.plan_parser import parse_and_save_plans


def _build_user_context(profile: UserProfile) -> str:
    from datetime import date
    age = (date.today() - profile.date_of_birth).days // 365
    return f"""User Profile:
- Age: {age}, Gender: {profile.gender}
- Height: {profile.height_cm}cm, Weight: {profile.weight_kg}kg
- Fitness experience: {profile.fitness_experience}
- Primary goal: {profile.primary_goal}
- Diet type: {profile.diet_type}
- Food allergies: {', '.join(profile.food_allergies) or 'none'}
- Food preferences: {profile.food_preferences or 'none'}
- Daily routine: {profile.daily_routine}
- Wake time: {profile.wake_time}, Sleep time: {profile.sleep_time}
- Work schedule: {profile.work_schedule}
- Workout days per week: {profile.workout_days_per_week}
- Preferred workout days: {', '.join(profile.preferred_workout_days)}
- Running days per week: {profile.running_days_per_week}
- Workout location: {profile.workout_location}
- Available equipment: {', '.join(profile.available_equipment) or 'bodyweight only'}
- Injury history: {profile.injury_history or 'none'}
- Medical conditions: {profile.medical_conditions or 'none'}
- Additional comments: {profile.additional_comments or 'none'}

Generate week 1 starting from today."""


async def generate_initial_plans(user: User) -> tuple:
    profile = await UserProfile.objects.aget(user=user)
    client = get_client()

    message = await client.messages.acreate(
        model="claude-sonnet-4-6",
        max_tokens=8096,
        system=[
            {
                "type": "text",
                "text": PLAN_GENERATION_SYSTEM_PROMPT,
                "cache_control": {"type": "ephemeral"},
            }
        ],
        messages=[{"role": "user", "content": _build_user_context(profile)}],
    )

    raw = message.content[0].text
    try:
        data = json.loads(raw)
    except (json.JSONDecodeError, IndexError) as e:
        raise ValueError(f"Claude returned invalid JSON: {e}") from e
    return await _async_parse(user, data)


async def _async_parse(user, data):
    from asgiref.sync import sync_to_async
    return await sync_to_async(parse_and_save_plans)(user, data)
