from datetime import date, timedelta
from services.health.calculations import compute_cycle_phase, compute_momentum, Momentum


def test_cycle_phase_none_when_no_period():
    assert compute_cycle_phase(None, 28, date(2026, 6, 17)) is None


def test_cycle_phase_none_when_date_before_start():
    assert compute_cycle_phase(date(2026, 6, 10), 28, date(2026, 6, 5)) is None


def test_cycle_phase_none_when_cycle_length_not_positive():
    assert compute_cycle_phase(date(2026, 6, 1), 0, date(2026, 6, 17)) is None


def test_cycle_phase_period_days_1_to_5():
    start = date(2026, 6, 1)
    assert compute_cycle_phase(start, 28, start) == "period"
    assert compute_cycle_phase(start, 28, start + timedelta(4)) == "period"


def test_cycle_phase_follicular_days_6_to_13():
    start = date(2026, 6, 1)
    assert compute_cycle_phase(start, 28, start + timedelta(5)) == "follicular"
    assert compute_cycle_phase(start, 28, start + timedelta(12)) == "follicular"


def test_cycle_phase_ovulation_days_14_to_15():
    start = date(2026, 6, 1)
    assert compute_cycle_phase(start, 28, start + timedelta(13)) == "ovulation"
    assert compute_cycle_phase(start, 28, start + timedelta(14)) == "ovulation"


def test_cycle_phase_luteal_after_day_15():
    start = date(2026, 6, 1)
    assert compute_cycle_phase(start, 28, start + timedelta(15)) == "luteal"
    assert compute_cycle_phase(start, 28, start + timedelta(27)) == "luteal"


def test_cycle_phase_wraps_to_next_cycle():
    start = date(2026, 6, 1)
    assert compute_cycle_phase(start, 28, start + timedelta(28)) == "period"


def test_momentum_no_history():
    m = compute_momentum(set(), date(2026, 6, 17))
    assert m == Momentum(current_streak=0, days_since_last=None, bucket="no_history")


def test_momentum_current_streak_of_three():
    on = date(2026, 6, 17)
    dates = {on, on - timedelta(1), on - timedelta(2)}
    m = compute_momentum(dates, on)
    assert m.current_streak == 3
    assert m.days_since_last == 0
    assert m.bucket == "current"


def test_momentum_missed_2_3_bucket():
    on = date(2026, 6, 17)
    m = compute_momentum({on - timedelta(3)}, on)
    assert m.days_since_last == 3
    assert m.bucket == "missed_2_3"


def test_momentum_missed_4_7_bucket():
    on = date(2026, 6, 17)
    m = compute_momentum({on - timedelta(6)}, on)
    assert m.bucket == "missed_4_7"


def test_momentum_full_reset_bucket():
    on = date(2026, 6, 17)
    m = compute_momentum({on - timedelta(20)}, on)
    assert m.bucket == "full_reset"


def test_momentum_ignores_future_dates():
    on = date(2026, 6, 17)
    m = compute_momentum({on + timedelta(2)}, on)
    assert m == Momentum(current_streak=0, days_since_last=None, bucket="no_history")
