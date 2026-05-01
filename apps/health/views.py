from datetime import date
from django.contrib.auth.decorators import login_required
from django.http import HttpResponse
from django.views.decorators.http import require_POST
from .models import NutritionLog, WellnessLog


@login_required
@require_POST
def log_nutrition(request):
    today = date.today()
    meal_type = request.POST.get("meal_type")
    log, _ = NutritionLog.objects.get_or_create(
        user=request.user, date=today, meal_type=meal_type,
        defaults={"description": ""},
    )
    log.description = request.POST.get("description", "")
    log.estimated_calories = request.POST.get("estimated_calories") or None
    log.estimated_protein_g = request.POST.get("estimated_protein_g") or None
    log.estimated_carbs_g = request.POST.get("estimated_carbs_g") or None
    log.estimated_fat_g = request.POST.get("estimated_fat_g") or None
    log.water_ml = request.POST.get("water_ml") or None
    log.additional_comments = request.POST.get("additional_comments", "")
    log.save()
    return HttpResponse('<span class="saved">Saved ✓</span>')


@login_required
@require_POST
def log_wellness(request):
    today = date.today()
    log, _ = WellnessLog.objects.get_or_create(
        user=request.user, date=today,
        defaults={"sleep_hours": 0, "sleep_quality": 3, "mood_score": 5,
                  "stress_level": 5, "energy_level": 5},
    )
    log.sleep_hours = request.POST.get("sleep_hours", 0)
    log.sleep_quality = request.POST.get("sleep_quality", 3)
    log.mood_score = request.POST.get("mood_score", 5)
    log.stress_level = request.POST.get("stress_level", 5)
    log.energy_level = request.POST.get("energy_level", 5)
    log.mindfulness_done = request.POST.get("mindfulness_done") == "true"
    log.mindfulness_duration_minutes = request.POST.get("mindfulness_duration_minutes") or None
    log.mindfulness_type = request.POST.get("mindfulness_type", "")
    log.additional_comments = request.POST.get("additional_comments", "")
    log.save()
    return HttpResponse('<span class="saved">Saved ✓</span>')
