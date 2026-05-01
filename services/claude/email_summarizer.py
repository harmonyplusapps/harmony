from datetime import date
from django.contrib.auth.models import User
from apps.fitness.models import FitnessPlan, WorkoutDay, WorkoutLog
from apps.health.models import HealthPlan, NutritionLog, WellnessLog
from services.claude.client import get_client
from services.claude.prompts import EMAIL_SUMMARY_SYSTEM_PROMPT


def build_daily_context(user: User, today: date) -> dict:
    fitness_plan = FitnessPlan.objects.filter(user=user, is_active=True).first()
    health_plan = HealthPlan.objects.filter(user=user, is_active=True).first()

    planned_workout = None
    actual_workout = None
    fitness_status = "no_data"

    if fitness_plan:
        day_of_week = today.strftime("%A")
        planned_workout = WorkoutDay.objects.filter(
            fitness_plan=fitness_plan, day_of_week=day_of_week
        ).first()
        if planned_workout:
            log = WorkoutLog.objects.filter(user=user, workout_day=planned_workout).first()
            if log:
                actual_workout = log
                if log.completion_percentage > 110:
                    fitness_status = "overshooting"
                elif log.completion_percentage >= 90:
                    fitness_status = "on_track"
                else:
                    fitness_status = "underachieving"

    nutrition_logs = list(
        NutritionLog.objects.filter(user=user, date=today).values(
            "meal_type", "description", "estimated_calories"
        )
    )
    total_logged_calories = sum(
        n["estimated_calories"] or 0 for n in nutrition_logs
    )
    health_status = "no_data"
    if health_plan and nutrition_logs:
        if total_logged_calories > health_plan.daily_calorie_target * 1.1:
            health_status = "overshooting"
        elif total_logged_calories >= health_plan.daily_calorie_target * 0.9:
            health_status = "on_track"
        else:
            health_status = "underachieving"

    wellness = WellnessLog.objects.filter(user=user, date=today).first()

    return {
        "planned_workout": str(planned_workout) if planned_workout else "Rest day",
        "actual_workout": f"{actual_workout.completion_percentage}% complete" if actual_workout else "Not logged",
        "fitness_status": fitness_status,
        "nutrition_logs": nutrition_logs,
        "calorie_target": health_plan.daily_calorie_target if health_plan else None,
        "total_logged_calories": total_logged_calories,
        "health_status": health_status,
        "wellness": {
            "sleep_hours": str(wellness.sleep_hours) if wellness else "Not logged",
            "mood_score": wellness.mood_score if wellness else None,
            "mindfulness_done": wellness.mindfulness_done if wellness else False,
        },
    }


def generate_email_summary(user: User, today: date) -> tuple[str, str, str]:
    context = build_daily_context(user, today)
    client = get_client()

    message = client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=512,
        system=[
            {
                "type": "text",
                "text": EMAIL_SUMMARY_SYSTEM_PROMPT,
                "cache_control": {"type": "ephemeral"},
            }
        ],
        messages=[
            {
                "role": "user",
                "content": f"Today's data for {user.get_full_name() or user.username}:\n{context}",
            }
        ],
    )

    summary_text = message.content[0].text
    return summary_text, context["fitness_status"], context["health_status"]
