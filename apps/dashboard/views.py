from datetime import date
from django.contrib.auth.decorators import login_required
from django.shortcuts import render, redirect
from apps.fitness.models import FitnessPlan, WorkoutDay, WorkoutLog
from apps.health.models import HealthPlan, MealPlan, WellnessLog
from services.coach.engine import decide_today, ACTIVE_RECOVERY_SUGGESTION


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

    decision = decide_today(request.user, today)
    intensity_pct = round(decision.intensity_modifier * 100)

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

    progress_dots = [i < completed_days for i in range(max(planned_days, 1))]

    return render(request, "dashboard/index.html", {
        "profile": profile,
        "today": today,
        "today_workout": today_workout,
        "workout_log": workout_log,
        "decision": decision,
        "intensity_pct": intensity_pct,
        "active_recovery_suggestion": ACTIVE_RECOVERY_SUGGESTION,
        "today_meals": today_meals,
        "wellness_log": wellness_log,
        "fitness_plan": fitness_plan,
        "health_plan": health_plan,
        "completed_days": completed_days,
        "planned_days": planned_days,
        "progress_dots": progress_dots,
        "meal_types": MealPlan.MEAL_TYPE_CHOICES,
    })


@login_required
def weekly_plan(request):
    profile = getattr(request.user, "profile", None)
    if not profile or not profile.onboarding_completed:
        return redirect("onboarding_step1")

    DAYS = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
    today_name = date.today().strftime("%A")

    fitness_plan = FitnessPlan.objects.filter(user=request.user, is_active=True).first()
    health_plan = HealthPlan.objects.filter(user=request.user, is_active=True).first()

    days = []
    if fitness_plan:
        workout_days = {
            wd.day_of_week: wd
            for wd in fitness_plan.workout_days
                .prefetch_related("exercises__exercise_cache", "running_strategy")
                .all()
        }
        meals_by_day = {}
        if health_plan:
            for meal in health_plan.meal_plans.order_by("order").all():
                meals_by_day.setdefault(meal.day_of_week, []).append(meal)

        days = [
            {
                "name": day,
                "short": day[:3],
                "workout": workout_days.get(day),
                "meals": meals_by_day.get(day, []),
                "is_today": day == today_name,
            }
            for day in DAYS
        ]

    return render(request, "dashboard/weekly_plan.html", {
        "profile": profile,
        "fitness_plan": fitness_plan,
        "health_plan": health_plan,
        "days": days,
        "today_name": today_name,
    })
