from dataclasses import dataclass

from apps.health.models import WellnessLog, SorenessLog, PeriodLog
from apps.fitness.models import WorkoutLog
from services.health.calculations import (
    compute_cycle_phase, compute_momentum, Momentum,
)


@dataclass(frozen=True)
class SorenessItem:
    muscle_group: str
    severity: str


@dataclass
class HealthSnapshot:
    date: object
    sleep_hours: object
    sleep_quality: object
    energy: object
    stress: object
    soreness: list
    cycle_phase: object
    momentum: Momentum
    steps: object
    resting_hr: object
    recent_workouts: list


def get_health_snapshot(user, on_date):
    """Assemble all health signals for `user` on `on_date`. Missing data -> None/empty."""
    wellness = WellnessLog.objects.filter(user=user, date=on_date).first()

    soreness = [
        SorenessItem(s.muscle_group, s.severity)
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

    completed_dates = set(
        WorkoutLog.objects.filter(user=user, completed=True, date__lte=on_date)
        .values_list("date", flat=True)
    )
    momentum = compute_momentum(completed_dates, on_date)

    recent_workouts = list(
        WorkoutLog.objects.filter(user=user, completed=True, date__lte=on_date)
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
