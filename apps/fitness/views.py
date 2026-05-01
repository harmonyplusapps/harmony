from django.contrib.auth.decorators import login_required
from django.http import HttpResponse
from django.shortcuts import get_object_or_404
from django.views.decorators.http import require_POST
from .models import WorkoutLog, ExerciseLog, WorkoutExercise, WorkoutDay
import json


def _parse_json_list(raw, default=None):
    try:
        result = json.loads(raw or "[]")
        return result if isinstance(result, list) else (default or [])
    except (json.JSONDecodeError, TypeError):
        return default or []


@login_required
@require_POST
def log_workout_day(request, workout_day_id):
    day = get_object_or_404(WorkoutDay, id=workout_day_id, fitness_plan__user=request.user)
    log, _ = WorkoutLog.objects.get_or_create(
        user=request.user, workout_day=day,
        defaults={"date": day.date},
    )
    log.completed = request.POST.get("completed") == "true"
    log.completion_percentage = int(request.POST.get("completion_percentage", 0))
    log.perceived_exertion = request.POST.get("perceived_exertion") or None
    log.actual_duration_minutes = request.POST.get("actual_duration_minutes") or None
    log.additional_comments = request.POST.get("additional_comments", "")
    log.save()
    return HttpResponse('<span class="saved">Saved ✓</span>')


@login_required
@require_POST
def log_exercise(request, exercise_id):
    exercise = get_object_or_404(WorkoutExercise, id=exercise_id, workout_day__fitness_plan__user=request.user)
    workout_log = get_object_or_404(WorkoutLog, user=request.user, workout_day=exercise.workout_day)
    log, _ = ExerciseLog.objects.get_or_create(
        workout_log=workout_log, workout_exercise=exercise
    )
    log.sets_completed = int(request.POST.get("sets_completed", 0))
    log.reps_completed = _parse_json_list(request.POST.get("reps_completed"))
    log.weight_kg = _parse_json_list(request.POST.get("weight_kg"))
    log.skipped = request.POST.get("skipped") == "true"
    log.skip_reason = request.POST.get("skip_reason", "")
    log.additional_comments = request.POST.get("additional_comments", "")
    log.save()
    return HttpResponse('<span class="saved">Saved ✓</span>')
