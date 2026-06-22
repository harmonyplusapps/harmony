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
