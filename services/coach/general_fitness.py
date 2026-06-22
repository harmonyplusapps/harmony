from dataclasses import dataclass

# --- Tunable constants -------------------------------------------------------
CONSISTENCY_THRESHOLD = 0.8
DURATION_INCREMENT_MIN = 5
BUMP_EVERY_CONSISTENT_WEEKS = 2
DURATION_CAP_MIN = 30
FOURTH_DAY_STREAK = 3
MAX_TRAINING_DAYS = 4
RUN_MONOTONY_WINDOW = 3
DURATION_BUMP_DAY_TYPES = ("strength", "yoga")
ROTATION_PREFERENCE = ["easy", "interval", "tempo", "long_run", "fartlek"]


@dataclass(frozen=True)
class RunRotation:
    recent_type: str
    suggested_type: str
    note: str


def consistent_week(planned: int, completed: int,
                    threshold: float = CONSISTENCY_THRESHOLD) -> bool:
    """A week counts as consistent when >= threshold of its planned (non-rest)
    workouts were completed. A week with nothing planned is not consistent."""
    return planned > 0 and completed / planned >= threshold


def duration_bump(streak_weeks: int) -> tuple[int, bool]:
    """Minutes to add per session given a consistent-week streak, and whether the
    +30 min cap has been reached. +5 min per 2 consistent weeks."""
    bumps = streak_weeks // BUMP_EVERY_CONSISTENT_WEEKS
    raw = bumps * DURATION_INCREMENT_MIN
    return min(raw, DURATION_CAP_MIN), raw >= DURATION_CAP_MIN


def should_add_training_day(streak_weeks: int, current_days: int) -> bool:
    """Nudge to add a training day after a 3-consistent-week streak, but only for
    users training fewer than 4 days/week."""
    return streak_weeks >= FOURTH_DAY_STREAK and current_days < MAX_TRAINING_DAYS


def suggest_run_rotation(recent_run_types: list[str]) -> tuple[str | None, str]:
    """Anti-monotony nudge: when the recent run window is full and all one type,
    suggest the first preferred type not used recently. Otherwise (None, "")."""
    if len(recent_run_types) < RUN_MONOTONY_WINDOW:
        return None, ""
    recent_set = set(recent_run_types)
    if len(recent_set) != 1:
        return None, ""
    recent_type = recent_run_types[0]
    suggested = next((t for t in ROTATION_PREFERENCE if t not in recent_set), None)
    if suggested is None:
        return None, ""
    note = (f"Your last {len(recent_run_types)} runs were all "
            f"{recent_type.replace('_', ' ')} — try a "
            f"{suggested.replace('_', ' ')} run.")
    return suggested, note


def consistent_week_streak(user, on_date) -> int:
    """Count consecutive consistent weeks among the user's fully-elapsed week-plans,
    newest first. A week is consistent when >= CONSISTENCY_THRESHOLD of its non-rest
    workout days have a completed WorkoutLog. The in-progress week is excluded."""
    from apps.fitness.models import FitnessPlan, WorkoutLog

    plans = FitnessPlan.objects.filter(
        user=user, end_date__lt=on_date,
    ).order_by("-week_number")

    streak = 0
    for plan in plans:
        planned = plan.workout_days.exclude(day_type="rest").count()
        completed = (
            WorkoutLog.objects.filter(
                user=user, workout_day__fitness_plan=plan, completed=True,
            ).exclude(workout_day__day_type="rest").count()
        )
        if consistent_week(planned, completed):
            streak += 1
        else:
            break
    return streak
