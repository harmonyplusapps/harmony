from dataclasses import dataclass
from datetime import date, timedelta


def compute_cycle_phase(last_period_start, cycle_length, on_date):
    """Return menstrual phase for on_date, or None if untracked / invalid / date precedes start.

    Phases (day_in_cycle is 1-based):
      1-5   period
      6-13  follicular
      14-15 ovulation
      16+   luteal
    """
    if last_period_start is None or cycle_length <= 0:
        return None
    days_since = (on_date - last_period_start).days
    if days_since < 0:
        return None
    day_in_cycle = days_since % cycle_length + 1
    if day_in_cycle <= 5:
        return "period"
    if day_in_cycle <= 13:
        return "follicular"
    if day_in_cycle <= 15:
        return "ovulation"
    return "luteal"


@dataclass
class Momentum:
    current_streak: int          # consecutive days ending at the most recent completed workout
    days_since_last: int | None  # days from on_date back to last completed workout (None if none)
    bucket: str                  # no_history | current | missed_2_3 | missed_4_7 | missed_long | full_reset


def _momentum_bucket(days_since_last):
    if days_since_last <= 1:
        return "current"
    if days_since_last <= 3:
        return "missed_2_3"
    if days_since_last <= 7:
        return "missed_4_7"
    if days_since_last <= 13:
        return "missed_long"
    return "full_reset"


def compute_momentum(completed_dates, on_date):
    """Derive streak/recency from the set of dates with a completed workout."""
    past = sorted(d for d in completed_dates if d <= on_date)
    if not past:
        return Momentum(current_streak=0, days_since_last=None, bucket="no_history")
    past_set = set(past)
    last = past[-1]
    days_since_last = (on_date - last).days
    streak = 1
    cursor = last
    while (cursor - timedelta(days=1)) in past_set:
        cursor -= timedelta(days=1)
        streak += 1
    return Momentum(
        current_streak=streak,
        days_since_last=days_since_last,
        bucket=_momentum_bucket(days_since_last),
    )
