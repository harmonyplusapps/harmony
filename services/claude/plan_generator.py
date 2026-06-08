import json
from django.contrib.auth.models import User
from apps.accounts.models import UserProfile
from services.claude.client import get_async_client
from services.claude.prompts import PLAN_GENERATION_SYSTEM_PROMPT
from services.claude.plan_parser import parse_and_save_plans

MAX_CONTINUATIONS = 5


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


def _strip_fences(text: str) -> str:
    text = text.strip()
    if text.startswith("```"):
        text = text[text.index("\n") + 1:]
    if text.endswith("```"):
        text = text[:text.rfind("```")]
    return text.strip()


async def _generate_with_continuation(client, system, messages) -> str:
    accumulated = ""

    for attempt in range(MAX_CONTINUATIONS + 1):
        async with client.messages.stream(
            model="claude-sonnet-4-6",
            max_tokens=32000,
            system=system,
            messages=messages,
        ) as stream:
            final_message = await stream.get_final_message()

        chunk = final_message.content[0].text if final_message.content else ""
        accumulated += chunk

        if final_message.stop_reason != "max_tokens":
            break

        if attempt == MAX_CONTINUATIONS:
            raise ValueError("Plan generation exceeded maximum continuations without completing.")

        messages = messages + [
            {"role": "assistant", "content": chunk},
            {"role": "user", "content": "Continue exactly where you left off. No repetition, no preamble."},
        ]

    return accumulated


async def generate_initial_plans(user: User) -> tuple:
    profile = await UserProfile.objects.aget(user=user)
    client = get_async_client()

    system = [
        {
            "type": "text",
            "text": PLAN_GENERATION_SYSTEM_PROMPT,
            "cache_control": {"type": "ephemeral"},
        }
    ]
    messages = [{"role": "user", "content": _build_user_context(profile)}]

    raw = await _generate_with_continuation(client, system, messages)

    try:
        data = json.loads(_strip_fences(raw))
    except json.JSONDecodeError as e:
        raise ValueError(f"Claude returned invalid JSON after continuation: {e}") from e

    return await _async_parse(user, data)


async def _async_parse(user, data):
    from asgiref.sync import sync_to_async
    return await sync_to_async(parse_and_save_plans)(user, data)
