from dataclasses import dataclass
from datetime import timedelta

from services.health.snapshot import get_health_snapshot

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

# --- User-facing strings -----------------------------------------------------
ACTIVE_RECOVERY_SUGGESTION = "20–30 min easy walk plus full-body mobility and light stretching."

LOW_ENERGY_MULTIPLIER = 0.7
PUSH_MULTIPLIER = 1.05
MOMENTUM_MULTIPLIER = {
    "current": 1.0, "no_history": 1.0,
    "missed_2_3": 0.85, "missed_4_7": 0.6, "missed_long": 0.6, "full_reset": 0.5,
}
CYCLE_MULTIPLIER = {
    "luteal": 0.85, "period": 0.85, "follicular": 1.1, "ovulation": 1.1,
}


@dataclass(frozen=True)
class DailyDecision:
    planned_day_type: str | None
    recommended_day_type: str
    intensity_modifier: float
    avoid_focus_areas: tuple[str, ...]
    rationale: str
    flags: tuple[str, ...]
    is_override: bool


def _momentum_rationale(bucket) -> str:
    return {
        "missed_2_3": "A couple days off — easing back in.",
        "missed_4_7": "Been a few days — keeping it moderate.",
        "missed_long": "Welcome back — easing in after the break.",
        "full_reset": "Fresh restart — keeping today light.",
    }.get(bucket, "")


def _cycle_rationale(phase) -> str:
    return {
        "luteal": "Luteal phase — favoring a steadier effort.",
        "period": "On your period — keeping the effort gentle.",
        "follicular": "Follicular phase — good day to push.",
        "ovulation": "Peak-energy window — great day to push.",
    }.get(phase, "")


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

    # Intensity path: compounding modifiers, single best rationale.
    modifier = 1.0
    candidates = []  # (multiplier, rationale)
    flags = []

    if snapshot.energy is not None and snapshot.energy <= LOW_ENERGY:
        modifier *= LOW_ENERGY_MULTIPLIER
        candidates.append((LOW_ENERGY_MULTIPLIER, "Energy's low today — lighter session."))

    mom_mult = MOMENTUM_MULTIPLIER.get(snapshot.momentum.bucket, 1.0)
    if mom_mult != 1.0:
        modifier *= mom_mult
        candidates.append((mom_mult, _momentum_rationale(snapshot.momentum.bucket)))

    cycle_mult = CYCLE_MULTIPLIER.get(snapshot.cycle_phase, 1.0)
    if cycle_mult != 1.0:
        modifier *= cycle_mult
        candidates.append((cycle_mult, _cycle_rationale(snapshot.cycle_phase)))

    streak = snapshot.momentum.current_streak
    if streak >= PUSH_STREAK:
        modifier *= PUSH_MULTIPLIER
        flags.append("push")
        candidates.append((PUSH_MULTIPLIER, f"{streak}-day streak — pushing a little."))
    if streak >= OVERTRAIN_STREAK:
        flags.append("overtraining_watch")

    modifier = round(max(MIN_INTENSITY, min(MAX_INTENSITY, modifier)), 3)

    if candidates:
        # Tie on deviation: appearance order wins (energy > momentum > cycle > streak).
        rationale = max(candidates, key=lambda c: abs(c[0] - 1.0))[1]
    else:
        rationale = "On plan — go for it."

    return DailyDecision(
        planned_day_type=planned, recommended_day_type=planned,
        intensity_modifier=modifier, avoid_focus_areas=avoid,
        rationale=rationale, flags=tuple(flags),
        is_override=abs(modifier - 1.0) > 1e-9,
    )


def decide_today(user, on_date) -> DailyDecision:
    """Fetch today's snapshot + planned workout and return the daily decision."""
    from apps.fitness.models import FitnessPlan, WorkoutDay
    snapshot = get_health_snapshot(user, on_date)
    plan = FitnessPlan.objects.filter(user=user, is_active=True).first()
    workout_day = None
    if plan is not None:
        workout_day = WorkoutDay.objects.filter(
            fitness_plan=plan, day_of_week=on_date.strftime("%A")
        ).first()
    return decide(snapshot, workout_day)
