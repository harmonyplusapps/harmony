from dataclasses import dataclass

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
