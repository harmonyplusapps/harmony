import json
from django.contrib.auth.models import User
from apps.fitness.models import FitnessPlan, WorkoutLog
from apps.health.models import HealthPlan, NutritionLog, WellnessLog
from apps.plans.models import PlanAdaptationLog
from services.claude.client import get_client
from services.claude.prompts import ADAPTATION_SYSTEM_PROMPT
from services.claude.plan_parser import parse_and_save_plans


def _build_adaptation_context(user: User, fitness_plan: FitnessPlan, health_plan: HealthPlan) -> str:
    logs = WorkoutLog.objects.filter(
        user=user, workout_day__fitness_plan=fitness_plan
    ).select_related("workout_day").prefetch_related("exercise_logs")

    workout_summary = []
    for log in logs:
        workout_summary.append({
            "day": log.workout_day.day_of_week,
            "completed": log.completed,
            "completion_pct": log.completion_percentage,
            "perceived_exertion": log.perceived_exertion,
            "actual_duration": log.actual_duration_minutes,
            "comments": log.additional_comments,
        })

    nutrition_logs = NutritionLog.objects.filter(
        user=user, date__range=[fitness_plan.start_date, fitness_plan.end_date]
    ).values("date", "meal_type", "estimated_calories", "description")

    wellness_logs = WellnessLog.objects.filter(
        user=user, date__range=[fitness_plan.start_date, fitness_plan.end_date]
    ).values("date", "sleep_hours", "sleep_quality", "mood_score", "stress_level", "energy_level")

    return f"""Current week summary:
Fitness logs: {json.dumps(workout_summary, default=str)}
Nutrition logs: {json.dumps(list(nutrition_logs), default=str)}
Wellness logs: {json.dumps(list(wellness_logs), default=str)}
Current fitness plan reasoning: {fitness_plan.claude_reasoning}
Current health plan reasoning: {health_plan.claude_reasoning}

Generate an adapted plan for week {fitness_plan.week_number + 1}."""


async def adapt_plans_for_user(user: User) -> None:
    fitness_plan = await FitnessPlan.objects.filter(user=user, is_active=True).afirst()
    health_plan = await HealthPlan.objects.filter(user=user, is_active=True).afirst()

    if not fitness_plan or not health_plan:
        return

    client = get_client()
    context = await _async_build_context(user, fitness_plan, health_plan)

    message = await client.messages.acreate(
        model="claude-sonnet-4-6",
        max_tokens=8096,
        system=[
            {
                "type": "text",
                "text": ADAPTATION_SYSTEM_PROMPT,
                "cache_control": {"type": "ephemeral"},
            }
        ],
        messages=[{"role": "user", "content": context}],
    )

    data = json.loads(message.content[0].text)
    from asgiref.sync import sync_to_async
    new_fitness, new_health = await sync_to_async(parse_and_save_plans)(user, data)

    await PlanAdaptationLog.objects.acreate(
        user=user,
        adaptation_type="fitness",
        previous_plan_id=fitness_plan.id,
        new_plan_id=new_fitness.id,
        trigger_reason=data["fitness_plan"].get("claude_reasoning", "")[:200],
        claude_analysis=data["fitness_plan"].get("claude_reasoning", ""),
    )
    await PlanAdaptationLog.objects.acreate(
        user=user,
        adaptation_type="health",
        previous_plan_id=health_plan.id,
        new_plan_id=new_health.id,
        trigger_reason=data["health_plan"].get("claude_reasoning", "")[:200],
        claude_analysis=data["health_plan"].get("claude_reasoning", ""),
    )


async def _async_build_context(user, fitness_plan, health_plan):
    from asgiref.sync import sync_to_async
    return await sync_to_async(_build_adaptation_context)(user, fitness_plan, health_plan)
