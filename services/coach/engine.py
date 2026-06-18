from dataclasses import dataclass
from datetime import timedelta

# --- Tunable constants -------------------------------------------------------
RECOVERY_INTENSITY = 0.4
MIN_INTENSITY = 0.4
MAX_INTENSITY = 1.1
HARD_RPE = 8              # perceived_exertion (1-10) considered a hard session
POOR_SLEEP_QUALITY = 2   # sleep_quality is 1-5
POOR_SLEEP_HOURS = 6     # sleep_hours
LOW_ENERGY = 3           # energy is 1-10
PUSH_STREAK = 3          # consecutive days to start nudging harder
OVERTRAIN_STREAK = 5     # consecutive days to flag overtraining watch

ACTIVE_RECOVERY_SUGGESTION = "20–30 min easy walk plus full-body mobility and light stretching."


@dataclass(frozen=True)
class DailyDecision:
    planned_day_type: str | None
    recommended_day_type: str
    intensity_modifier: float
    avoid_focus_areas: tuple[str, ...]
    rationale: str
    flags: tuple[str, ...]
    is_override: bool


def _sore_focus_areas(snapshot) -> tuple[str, ...]:
    return tuple(sorted({
        s.focus_area for s in snapshot.soreness
        if s.severity in ("moderate", "severe")
    }))


def _first_sore_group_for_focus(snapshot, focus_area) -> str:
    for s in snapshot.soreness:
        if s.severity in ("moderate", "severe") and s.focus_area == focus_area:
            return s.muscle_group
    return "those muscles"


def _hard_yesterday(snapshot) -> bool:
    yesterday = snapshot.date - timedelta(days=1)
    for wl in snapshot.recent_workouts:
        if wl.date == yesterday:
            if wl.perceived_exertion is not None:
                return wl.perceived_exertion >= HARD_RPE
            return wl.workout_day.day_type in ("strength", "running")
    return False


def _poor_sleep(snapshot) -> bool:
    if snapshot.sleep_quality is not None and snapshot.sleep_quality <= POOR_SLEEP_QUALITY:
        return True
    if snapshot.sleep_hours is not None and snapshot.sleep_hours < POOR_SLEEP_HOURS:
        return True
    return False


def decide(snapshot, workout_day) -> DailyDecision:
    planned = workout_day.day_type if workout_day else None
    avoid = _sore_focus_areas(snapshot)

    # Hard stop 1: planned rest / no workout today.
    if workout_day is None or planned == "rest":
        return DailyDecision(
            planned_day_type=planned, recommended_day_type=planned or "rest",
            intensity_modifier=1.0, avoid_focus_areas=avoid,
            rationale="Rest day — recover well.", flags=(), is_override=False,
        )

    # Hard stop 2: hard session yesterday + poor sleep -> active recovery.
    if _hard_yesterday(snapshot) and _poor_sleep(snapshot):
        return DailyDecision(
            planned_day_type=planned, recommended_day_type="active_recovery",
            intensity_modifier=RECOVERY_INTENSITY, avoid_focus_areas=avoid,
            rationale="Hard session yesterday plus short sleep — active recovery today.",
            flags=(), is_override=True,
        )

    # Hard stop 3: today's focus area is sore -> active recovery.
    if workout_day.focus_area in avoid:
        group = _first_sore_group_for_focus(snapshot, workout_day.focus_area)
        return DailyDecision(
            planned_day_type=planned, recommended_day_type="active_recovery",
            intensity_modifier=RECOVERY_INTENSITY, avoid_focus_areas=avoid,
            rationale=f"{group.title()} still sore — keeping today to active recovery.",
            flags=(), is_override=True,
        )

    # Intensity path (fully implemented in Task 3). Placeholder: on plan.
    return DailyDecision(
        planned_day_type=planned, recommended_day_type=planned,
        intensity_modifier=1.0, avoid_focus_areas=avoid,
        rationale="On plan — go for it.", flags=(), is_override=False,
    )
