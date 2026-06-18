from datetime import date
from decimal import Decimal

from services.health.snapshot import HealthSnapshot
from services.health.calculations import Momentum
from services.coach.engine import decide


ON = date(2026, 6, 18)


def _mom(bucket="current", streak=1):
    return Momentum(current_streak=streak, days_since_last=0, bucket=bucket)


def _snap(**over):
    base = dict(
        date=ON, sleep_hours=Decimal("8"), sleep_quality=4, energy=7, stress=4,
        soreness=[], cycle_phase=None, momentum=_mom(),
        steps=None, resting_hr=None, recent_workouts=[],
    )
    base.update(over)
    return HealthSnapshot(**base)


def _workout(day_type="strength", focus_area="upper_body"):
    from types import SimpleNamespace
    return SimpleNamespace(day_type=day_type, focus_area=focus_area)


def test_on_plan_when_nothing_fires():
    d = decide(_snap(), _workout())
    assert d.intensity_modifier == 1.0
    assert d.is_override is False
    assert d.recommended_day_type == "strength"
    assert d.rationale == "On plan — go for it."


def test_low_energy_scales_to_0_7():
    d = decide(_snap(energy=2), _workout())
    assert d.intensity_modifier == 0.7
    assert d.is_override is True
    assert "energy" in d.rationale.lower()


def test_missed_4_7_bucket_scales_to_0_6():
    d = decide(_snap(momentum=_mom(bucket="missed_4_7", streak=0)), _workout())
    assert d.intensity_modifier == 0.6


def test_full_reset_bucket_scales_to_0_5():
    d = decide(_snap(momentum=_mom(bucket="full_reset", streak=0)), _workout())
    assert d.intensity_modifier == 0.5


def test_luteal_phase_scales_to_0_85():
    d = decide(_snap(cycle_phase="luteal"), _workout())
    assert d.intensity_modifier == 0.85


def test_follicular_phase_scales_to_1_1():
    d = decide(_snap(cycle_phase="follicular"), _workout())
    assert d.intensity_modifier == 1.1


def test_push_streak_adds_flag_and_small_bump():
    d = decide(_snap(momentum=_mom(bucket="current", streak=4)), _workout())
    assert "push" in d.flags
    assert d.intensity_modifier == 1.05


def test_overtraining_watch_flag_at_streak_5():
    # streak exactly at OVERTRAIN_STREAK (5) fires the flag
    d = decide(_snap(momentum=_mom(bucket="current", streak=5)), _workout())
    assert "overtraining_watch" in d.flags


def test_compounding_clamps_to_min():
    d = decide(_snap(energy=1, momentum=_mom(bucket="full_reset", streak=0)), _workout())
    assert d.intensity_modifier == 0.4


def test_compounding_clamps_to_max():
    d = decide(_snap(cycle_phase="follicular", momentum=_mom(bucket="current", streak=5)), _workout())
    assert d.intensity_modifier == 1.1


def test_rationale_picks_largest_deviation_rule():
    d = decide(_snap(energy=2, momentum=_mom(bucket="full_reset", streak=0)), _workout())
    assert "restart" in d.rationale.lower() or "light" in d.rationale.lower()


def test_missed_long_bucket_scales_to_0_6_with_its_own_rationale():
    d = decide(_snap(momentum=_mom(bucket="missed_long", streak=0)), _workout())
    assert d.intensity_modifier == 0.6
    assert "break" in d.rationale.lower()


def test_period_phase_scales_to_0_85():
    d = decide(_snap(cycle_phase="period"), _workout())
    assert d.intensity_modifier == 0.85


def test_ovulation_phase_scales_to_1_1():
    d = decide(_snap(cycle_phase="ovulation"), _workout())
    assert d.intensity_modifier == 1.1
