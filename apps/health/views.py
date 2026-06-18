from datetime import date
from django.contrib.auth.decorators import login_required
from django.http import HttpResponse
from django.shortcuts import render, redirect
from django.db import transaction
from django.views.decorators.http import require_POST
from .models import NutritionLog, WellnessLog, SorenessLog, PeriodLog
from services.health.snapshot import get_health_snapshot


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


def _parse_optional_int(value):
    """Return an int, or None for empty/blank/non-numeric input (fields are optional)."""
    try:
        return int(value) if value not in (None, "") else None
    except (TypeError, ValueError):
        return None


@login_required
def checkin(request):
    today = date.today()
    if request.method == "POST":
        steps = _parse_optional_int(request.POST.get("steps"))
        resting_hr = _parse_optional_int(request.POST.get("resting_hr_bpm"))
        with transaction.atomic():
            # Replace today's soreness with whatever groups were submitted.
            SorenessLog.objects.filter(user=request.user, date=today).delete()
            for group, _label in SorenessLog.MUSCLE_GROUP_CHOICES:
                severity = request.POST.get(f"soreness_{group}")
                if severity in {"mild", "moderate", "severe"}:
                    SorenessLog.objects.create(
                        user=request.user, date=today, muscle_group=group, severity=severity,
                    )

            if steps is not None or resting_hr is not None:
                log, _ = WellnessLog.objects.get_or_create(
                    user=request.user, date=today,
                    defaults={"sleep_hours": 0, "sleep_quality": 3, "mood_score": 5,
                              "stress_level": 5, "energy_level": 5},
                )
                log.steps = steps
                log.resting_hr_bpm = resting_hr
                log.save()

            if request.POST.get("period_started") == "true" and request.user.profile.tracks_cycle:
                PeriodLog.objects.get_or_create(user=request.user, start_date=today)

        # Post/Redirect/Get: avoid re-submitting saves on refresh.
        return redirect("health_checkin")

    return render(request, "health/checkin.html", _checkin_context(request, today))


def _checkin_context(request, today):
    """Build the check-in template context. Call only from an authenticated view."""
    soreness = {
        s.muscle_group: s.severity
        for s in SorenessLog.objects.filter(user=request.user, date=today)
    }
    wellness = WellnessLog.objects.filter(user=request.user, date=today).first()
    tracks_cycle = request.user.profile.tracks_cycle
    cycle_phase = get_health_snapshot(request.user, today).cycle_phase if tracks_cycle else None
    period_logged_today = (
        tracks_cycle
        and PeriodLog.objects.filter(user=request.user, start_date=today).exists()
    )
    return {
        "muscle_groups": SorenessLog.MUSCLE_GROUP_CHOICES,
        "severities": SorenessLog.SEVERITY_CHOICES,
        "soreness": soreness,
        "steps": wellness.steps if wellness else "",
        "resting_hr_bpm": wellness.resting_hr_bpm if wellness else "",
        "tracks_cycle": tracks_cycle,
        "cycle_phase": cycle_phase,
        "period_logged_today": period_logged_today,
    }
