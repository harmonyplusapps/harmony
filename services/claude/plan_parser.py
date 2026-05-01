from django.db import transaction
from django.contrib.auth.models import User
from apps.fitness.models import FitnessPlan, WorkoutDay, WorkoutExercise, RunningStrategy
from apps.health.models import HealthPlan, MealPlan
from services.wger.client import fetch_and_cache_exercise


@transaction.atomic
def parse_and_save_plans(user: User, data: dict) -> tuple[FitnessPlan, HealthPlan]:
    fitness_plan = _parse_fitness_plan(user, data["fitness_plan"])
    health_plan = _parse_health_plan(user, data["health_plan"])
    return fitness_plan, health_plan


def _parse_fitness_plan(user: User, fp_data: dict) -> FitnessPlan:
    FitnessPlan.objects.filter(user=user, is_active=True).update(is_active=False)

    plan = FitnessPlan.objects.create(
        user=user,
        week_number=fp_data["week_number"],
        start_date=fp_data["start_date"],
        end_date=fp_data["end_date"],
        total_workout_days=fp_data["total_workout_days"],
        total_running_days=fp_data["total_running_days"],
        weekly_goal_summary=fp_data["weekly_goal_summary"],
        claude_reasoning=fp_data["claude_reasoning"],
    )

    for day_data in fp_data["workout_days"]:
        day = WorkoutDay.objects.create(
            fitness_plan=plan,
            date=day_data["date"],
            day_of_week=day_data["day_of_week"],
            day_type=day_data["day_type"],
            focus_area=day_data["focus_area"],
            estimated_duration_minutes=day_data["estimated_duration_minutes"],
            warmup_description=day_data.get("warmup_description", ""),
            cooldown_description=day_data.get("cooldown_description", ""),
            notes=day_data.get("notes", ""),
        )

        for i, ex_data in enumerate(day_data.get("exercises", [])):
            exercise_cache = fetch_and_cache_exercise(ex_data["exercise_name"])
            WorkoutExercise.objects.create(
                workout_day=day,
                exercise_cache=exercise_cache,
                custom_name=ex_data["exercise_name"] if not exercise_cache else "",
                section=ex_data["section"],
                sets=ex_data.get("sets"),
                reps=ex_data.get("reps"),
                duration_seconds=ex_data.get("duration_seconds"),
                distance_km=ex_data.get("distance_km"),
                rest_seconds=ex_data.get("rest_seconds", 60),
                intensity=ex_data["intensity"],
                notes=ex_data.get("notes", ""),
                order=i,
            )

        rs_data = day_data.get("running_strategy")
        if rs_data:
            RunningStrategy.objects.create(
                workout_day=day,
                run_type=rs_data["run_type"],
                total_distance_km=rs_data["total_distance_km"],
                total_duration_minutes=rs_data["total_duration_minutes"],
                pace_target=rs_data["pace_target"],
                structure=rs_data["structure"],
                heart_rate_zone=rs_data.get("heart_rate_zone", ""),
                notes=rs_data.get("notes", ""),
            )

    return plan


def _parse_health_plan(user: User, hp_data: dict) -> HealthPlan:
    HealthPlan.objects.filter(user=user, is_active=True).update(is_active=False)

    plan = HealthPlan.objects.create(
        user=user,
        week_number=hp_data["week_number"],
        start_date=hp_data["start_date"],
        end_date=hp_data["end_date"],
        daily_calorie_target=hp_data["daily_calorie_target"],
        daily_protein_g=hp_data["daily_protein_g"],
        daily_carbs_g=hp_data["daily_carbs_g"],
        daily_fat_g=hp_data["daily_fat_g"],
        daily_fiber_g=hp_data["daily_fiber_g"],
        daily_water_ml=hp_data["daily_water_ml"],
        claude_reasoning=hp_data["claude_reasoning"],
    )

    for day_data in hp_data["meal_plans"]:
        for i, meal_data in enumerate(day_data["meals"]):
            MealPlan.objects.create(
                health_plan=plan,
                day_of_week=day_data["day_of_week"],
                meal_type=meal_data["meal_type"],
                meal_name=meal_data["meal_name"],
                description=meal_data["description"],
                calories=meal_data["calories"],
                protein_g=meal_data["protein_g"],
                carbs_g=meal_data["carbs_g"],
                fat_g=meal_data["fat_g"],
                fiber_g=meal_data["fiber_g"],
                ingredients=meal_data["ingredients"],
                preparation_notes=meal_data.get("preparation_notes", ""),
                order=i,
            )

    return plan
