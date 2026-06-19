import math
from dataclasses import dataclass

INCREMENT_KG = 2.5  # default progression step (metric); tunable


@dataclass(frozen=True)
class WeightSuggestion:
    exercise_id: int
    suggested_weight_kg: float | None
    reason: str   # new | progress | hold | backoff | deload
    note: str


def round_to_increment(weight: float, increment: float) -> float:
    # Round half up (gym convention), not Python's banker's rounding.
    return round(math.floor(weight / increment + 0.5) * increment, 2)


def working_weight(weight_kg: list) -> float | None:
    """Top working set for a session, or None when nothing was logged."""
    return float(max(float(v) for v in weight_kg)) if weight_kg else None


def met_target(sets_completed: int, reps_completed: list, skipped: bool,
               prescribed_sets: int, prescribed_reps: int) -> bool:
    if skipped:
        return False
    if sets_completed < prescribed_sets:
        return False
    if not reps_completed:
        return False
    return all(r >= prescribed_reps for r in reps_completed)


def suggest_next_weight(sessions: list[tuple[float, bool]], increment_kg, is_deload):
    """Decide next weight from one exercise's history (oldest -> newest), each
    session a (working_weight, met_target) tuple. Returns (weight|None, reason, note)."""
    if not sessions:
        return (None, "new", "Log a few sessions and I'll start suggesting loads.")
    current = sessions[-1][0]
    if is_deload:
        return (round_to_increment(current * 0.8, increment_kg), "deload",
                "Deload week — back off to ~80%.")
    last_two = sessions[-2:]
    if len(last_two) == 2 and all(met for _, met in last_two):
        return (round_to_increment(current + increment_kg, increment_kg), "progress",
                f"Hit it twice — go up {increment_kg:g} kg.")
    if len(last_two) == 2 and not any(met for _, met in last_two):
        return (round_to_increment(current * 0.9, increment_kg), "backoff",
                "Two tough sessions — drop 10% and rebuild.")
    return (current, "hold", "Stay here and nail all your sets.")


def suggest_strength_progression(user, workout_day, is_deload):
    """Map each main-section weighted exercise on `workout_day` to a WeightSuggestion,
    using this user's prior ExerciseLog history for the same exercise identity."""
    from apps.fitness.models import ExerciseLog

    suggestions = {}
    main_exercises = workout_day.exercises.filter(
        section="main", sets__isnull=False, reps__isnull=False,
    )
    for ex in main_exercises:
        if ex.exercise_cache_id is not None:
            logs = ExerciseLog.objects.filter(
                workout_log__user=user,
                workout_exercise__exercise_cache_id=ex.exercise_cache_id,
            )
        elif ex.custom_name:
            logs = ExerciseLog.objects.filter(
                workout_log__user=user,
                workout_exercise__custom_name=ex.custom_name,
            )
        else:
            # No identity (no cache link, no name) -> cannot match history.
            suggestions[ex.id] = WeightSuggestion(
                exercise_id=ex.id, suggested_weight_kg=None, reason="new",
                note="Log a few sessions and I'll start suggesting loads.",
            )
            continue
        logs = logs.select_related("workout_exercise").order_by("workout_log__date")

        sessions = []
        for log in logs:
            w = working_weight(log.weight_kg)
            if w is None:
                continue
            we = log.workout_exercise
            sessions.append((
                w,
                met_target(log.sets_completed, log.reps_completed, log.skipped,
                           we.sets or 0, we.reps or 0),
            ))

        weight, reason, note = suggest_next_weight(sessions, INCREMENT_KG, is_deload)
        suggestions[ex.id] = WeightSuggestion(
            exercise_id=ex.id, suggested_weight_kg=weight, reason=reason, note=note,
        )
    return suggestions
