from datetime import date
from django.contrib.auth.decorators import login_required
from django.shortcuts import render, redirect
from apps.fitness.models import FitnessPlan, WorkoutDay, WorkoutLog
from apps.health.models import HealthPlan, MealPlan, WellnessLog


@login_required
def dashboard(request):
    profile = getattr(request.user, "profile", None)
    if not profile or not profile.onboarding_completed:
        return redirect("onboarding_step1")

    today = date.today()
    day_of_week = today.strftime("%A")

    fitness_plan = FitnessPlan.objects.filter(user=request.user, is_active=True).first()
    health_plan = HealthPlan.objects.filter(user=request.user, is_active=True).first()

    today_workout = None
    workout_log = None
    if fitness_plan:
        today_workout = WorkoutDay.objects.filter(
            fitness_plan=fitness_plan, day_of_week=day_of_week
        ).prefetch_related("exercises__exercise_cache", "running_strategy").first()
        if today_workout:
            workout_log, _ = WorkoutLog.objects.get_or_create(
                user=request.user,
                workout_day=today_workout,
                defaults={"date": today},
            )

    today_meals = []
    if health_plan:
        today_meals = MealPlan.objects.filter(
            health_plan=health_plan, day_of_week=day_of_week
        ).order_by("order")

    wellness_log, _ = WellnessLog.objects.get_or_create(
        user=request.user,
        date=today,
        defaults={"sleep_hours": 0, "sleep_quality": 3, "mood_score": 5,
                  "stress_level": 5, "energy_level": 5},
    )

    completed_days = 0
    planned_days = 0
    if fitness_plan:
        planned_days = fitness_plan.total_workout_days
        completed_days = WorkoutLog.objects.filter(
            user=request.user,
            workout_day__fitness_plan=fitness_plan,
            workout_day__date__gte=fitness_plan.start_date,
            workout_day__date__lte=fitness_plan.end_date,
            completed=True,
        ).count()

    return render(request, "dashboard/index.html", {
        "today": today,
        "today_workout": today_workout,
        "workout_log": workout_log,
        "today_meals": today_meals,
        "wellness_log": wellness_log,
        "fitness_plan": fitness_plan,
        "health_plan": health_plan,
        "completed_days": completed_days,
        "planned_days": planned_days,
        "meal_types": MealPlan.MEAL_TYPE_CHOICES,
    })
