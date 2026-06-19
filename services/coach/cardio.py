from dataclasses import dataclass
from datetime import timedelta

STEP_CAP = 10000
STEP_INCREMENT = 500
WEEKLY_MILEAGE_GROWTH = 1.10
DELOAD_MILEAGE_FACTOR = 0.7
TREND_EPSILON = 0.2  # kg; smaller weekly changes read as "flat"


@dataclass(frozen=True)
class WeightTrend:
    current_avg: float
    prior_avg: float | None
    delta_kg: float | None   # signed: current_avg - prior_avg
    direction: str           # down | up | flat


def round_to_500(value: int) -> int:
    return round(value / STEP_INCREMENT) * STEP_INCREMENT


def suggest_step_target(recent_avg_steps: int | None) -> int | None:
    if recent_avg_steps is None:
        return None
    if recent_avg_steps >= STEP_CAP:
        return STEP_CAP
    return min(STEP_CAP, round_to_500(recent_avg_steps) + STEP_INCREMENT)


def suggest_weekly_mileage_km(prior_week_km: float | None, is_deload: bool) -> float | None:
    if not prior_week_km:
        return None
    factor = DELOAD_MILEAGE_FACTOR if is_deload else WEEKLY_MILEAGE_GROWTH
    return round(prior_week_km * factor, 1)


def weekly_average(samples: list) -> float | None:
    return round(sum(samples) / len(samples), 1) if samples else None


def weight_trend(current_avg: float, prior_avg: float | None,
                 epsilon: float = TREND_EPSILON) -> str:
    if prior_avg is None:
        return "flat"
    diff = current_avg - prior_avg
    if diff <= -epsilon:
        return "down"
    if diff >= epsilon:
        return "up"
    return "flat"


def suggest_step_target_for(user, on_date):
    from apps.health.models import WellnessLog
    window_start = on_date - timedelta(days=7)
    steps = list(
        WellnessLog.objects.filter(
            user=user, date__gt=window_start, date__lte=on_date, steps__isnull=False,
        ).values_list("steps", flat=True)
    )
    if not steps:
        return None
    return suggest_step_target(int(sum(steps) / len(steps)))


def suggest_weekly_mileage_for(user, on_date, is_deload):
    from apps.fitness.models import RunningStrategy
    window_start = on_date - timedelta(days=7)
    distances = RunningStrategy.objects.filter(
        workout_day__fitness_plan__user=user,
        workout_day__date__gt=window_start,
        workout_day__date__lte=on_date,
        workout_day__logs__completed=True,
    ).values_list("total_distance_km", flat=True)
    total = float(sum(distances)) if distances else 0.0
    return suggest_weekly_mileage_km(total, is_deload)


def body_weight_trend(user, on_date):
    from apps.health.models import WeightLog
    current_start = on_date - timedelta(days=7)
    prior_start = on_date - timedelta(days=14)
    current = [
        float(w) for w in WeightLog.objects.filter(
            user=user, date__gt=current_start, date__lte=on_date,
        ).values_list("weight_kg", flat=True)
    ]
    if len(current) < 2:
        return None
    prior = [
        float(w) for w in WeightLog.objects.filter(
            user=user, date__gt=prior_start, date__lte=current_start,
        ).values_list("weight_kg", flat=True)
    ]
    current_avg = weekly_average(current)
    prior_avg = weekly_average(prior)
    delta = round(current_avg - prior_avg, 1) if prior_avg is not None else None
    return WeightTrend(
        current_avg=current_avg, prior_avg=prior_avg, delta_kg=delta,
        direction=weight_trend(current_avg, prior_avg),
    )
