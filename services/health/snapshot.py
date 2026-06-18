from dataclasses import dataclass
from datetime import date
from decimal import Decimal

from django.contrib.auth.models import User

from apps.health.models import WellnessLog, SorenessLog, PeriodLog, MUSCLE_GROUP_TO_FOCUS
from apps.fitness.models import WorkoutLog
from services.health.calculations import (
    compute_cycle_phase, compute_momentum, Momentum,
)


@dataclass(frozen=True)
class SorenessItem:
    muscle_group: str
    severity: str
    focus_area: str


@dataclass
class HealthSnapshot:
    """Read-model of a user's health signals for one day. Treat as immutable:
    the list fields (soreness, recent_workouts) are not meant to be mutated by callers."""
    date: date
    sleep_hours: Decimal | None
    sleep_quality: int | None
    energy: int | None
    stress: int | None
    soreness: list[SorenessItem]
    cycle_phase: str | None
    momentum: Momentum
    steps: int | None
    resting_hr: int | None
    recent_workouts: list[WorkoutLog]


def get_health_snapshot(user: User, on_date: date) -> HealthSnapshot:
    """Assemble all health signals for `user` on `on_date`. Missing data -> None/empty."""
    wellness = WellnessLog.objects.filter(user=user, date=on_date).first()

    soreness = [
        SorenessItem(s.muscle_group, s.severity, MUSCLE_GROUP_TO_FOCUS[s.muscle_group])
        for s in SorenessLog.objects.filter(user=user, date=on_date)
    ]

    cycle_phase = None
    profile = getattr(user, "profile", None)
    if profile is not None and profile.tracks_cycle:
        last_period = (
            PeriodLog.objects.filter(user=user, start_date__lte=on_date)
            .order_by("-start_date").first()
        )
        if last_period is not None:
            cycle_phase = compute_cycle_phase(
                last_period.start_date, profile.average_cycle_length, on_date,
            )

    # Lightweight date-only projection for momentum; recent_workouts below fetches full rows.
    completed_dates = set(
        WorkoutLog.objects.filter(user=user, completed=True, date__lte=on_date)
        .values_list("date", flat=True)
    )
    momentum = compute_momentum(completed_dates, on_date)

    recent_workouts = list(
        WorkoutLog.objects.filter(user=user, completed=True, date__lte=on_date)
        .select_related("workout_day")
        .order_by("-date")[:3]
    )

    return HealthSnapshot(
        date=on_date,
        sleep_hours=wellness.sleep_hours if wellness else None,
        sleep_quality=wellness.sleep_quality if wellness else None,
        energy=wellness.energy_level if wellness else None,
        stress=wellness.stress_level if wellness else None,
        soreness=soreness,
        cycle_phase=cycle_phase,
        momentum=momentum,
        steps=wellness.steps if wellness else None,
        resting_hr=wellness.resting_hr_bpm if wellness else None,
        recent_workouts=recent_workouts,
    )
