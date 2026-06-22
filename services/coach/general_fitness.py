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
