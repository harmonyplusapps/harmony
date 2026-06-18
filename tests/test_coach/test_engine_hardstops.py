from datetime import date, timedelta
from decimal import Decimal
from types import SimpleNamespace

from services.health.snapshot import HealthSnapshot, SorenessItem
from services.health.calculations import Momentum
from services.coach.engine import decide, DailyDecision


ON = date(2026, 6, 18)


def _snap(**over):
    base = dict(
        date=ON, sleep_hours=Decimal("8"), sleep_quality=4, energy=7, stress=4,
        soreness=[], cycle_phase=None,
        momentum=Momentum(current_streak=0, days_since_last=None, bucket="no_history"),
        steps=None, resting_hr=None, recent_workouts=[],
    )
    base.update(over)
    return HealthSnapshot(**base)


def _workout(day_type="strength", focus_area="lower_body"):
    return SimpleNamespace(day_type=day_type, focus_area=focus_area)


def test_no_workout_is_rest_no_override():
    d = decide(_snap(), None)
    assert d.recommended_day_type == "rest"
    assert d.is_override is False
    assert d.intensity_modifier == 1.0


def test_planned_rest_no_override():
    d = decide(_snap(), _workout(day_type="rest", focus_area="full_body"))
    assert d.recommended_day_type == "rest"
    assert d.is_override is False


def test_recovery_hardstop_on_hard_yesterday_plus_poor_sleep():
    yesterday = ON - timedelta(days=1)
    hard = SimpleNamespace(date=yesterday, perceived_exertion=9,
                           workout_day=SimpleNamespace(day_type="strength"))
    d = decide(_snap(sleep_quality=2, recent_workouts=[hard]), _workout())
    assert d.recommended_day_type == "active_recovery"
    assert d.intensity_modifier == 0.4
    assert d.is_override is True
    assert "active recovery" in d.rationale.lower()


def test_recovery_hardstop_requires_both_conditions():
    yesterday = ON - timedelta(days=1)
    hard = SimpleNamespace(date=yesterday, perceived_exertion=9,
                           workout_day=SimpleNamespace(day_type="strength"))
    d = decide(_snap(sleep_quality=5, recent_workouts=[hard]), _workout())
    assert d.recommended_day_type != "active_recovery"


def test_hard_yesterday_falls_back_to_day_type_when_rpe_missing():
    yesterday = ON - timedelta(days=1)
    hard = SimpleNamespace(date=yesterday, perceived_exertion=None,
                           workout_day=SimpleNamespace(day_type="running"))
    d = decide(_snap(sleep_hours=Decimal("5"), recent_workouts=[hard]), _workout())
    assert d.recommended_day_type == "active_recovery"


def test_soreness_conflict_with_todays_focus_forces_active_recovery():
    sore = [SorenessItem("quads", "severe", "lower_body")]
    d = decide(_snap(soreness=sore), _workout(focus_area="lower_body"))
    assert d.recommended_day_type == "active_recovery"
    assert d.is_override is True
    assert "quads" in d.rationale.lower()
    assert "lower_body" in d.avoid_focus_areas


def test_mild_soreness_does_not_hardstop():
    sore = [SorenessItem("quads", "mild", "lower_body")]
    d = decide(_snap(soreness=sore), _workout(focus_area="lower_body"))
    assert d.recommended_day_type != "active_recovery"
    assert d.avoid_focus_areas == ()


def test_soreness_in_other_focus_area_no_daytype_override():
    sore = [SorenessItem("core", "severe", "core")]
    d = decide(_snap(soreness=sore), _workout(focus_area="lower_body"))
    assert d.recommended_day_type == "strength"
    assert "core" in d.avoid_focus_areas
    assert d.is_override is False


def test_returns_dailydecision_instance():
    assert isinstance(decide(_snap(), _workout()), DailyDecision)


def test_phantom_zero_sleep_does_not_trigger_recovery():
    # sleep_hours == 0 is the unlogged placeholder, not real poor sleep
    yesterday = ON - timedelta(days=1)
    hard = SimpleNamespace(date=yesterday, perceived_exertion=9,
                           workout_day=SimpleNamespace(day_type="strength"))
    d = decide(_snap(sleep_hours=Decimal("0"), sleep_quality=4, recent_workouts=[hard]), _workout())
    assert d.recommended_day_type != "active_recovery"
