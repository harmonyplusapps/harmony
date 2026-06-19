from services.coach.cardio import (
    round_to_500, suggest_step_target, suggest_weekly_mileage_km,
    weekly_average, weight_trend, WeightTrend,
)


def test_round_to_500():
    assert round_to_500(8200) == 8000
    assert round_to_500(8300) == 8500
    assert round_to_500(0) == 0


def test_suggest_step_target_none_when_no_data():
    assert suggest_step_target(None) is None


def test_suggest_step_target_adds_500():
    assert suggest_step_target(8200) == 8500


def test_suggest_step_target_caps_at_10k():
    assert suggest_step_target(9800) == 10000


def test_suggest_step_target_maintains_at_10k():
    assert suggest_step_target(11000) == 10000


def test_suggest_weekly_mileage_none_when_no_prior():
    assert suggest_weekly_mileage_km(None, False) is None
    assert suggest_weekly_mileage_km(0, False) is None


def test_suggest_weekly_mileage_10_percent():
    assert suggest_weekly_mileage_km(13.0, False) == 14.3


def test_suggest_weekly_mileage_deload():
    assert suggest_weekly_mileage_km(13.0, True) == 9.1


def test_weekly_average():
    assert weekly_average([]) is None
    assert weekly_average([64.0, 65.0]) == 64.5


def test_weight_trend_directions():
    assert weight_trend(64.0, 65.0) == "down"
    assert weight_trend(65.0, 64.0) == "up"
    assert weight_trend(64.0, 64.1) == "flat"
    assert weight_trend(64.0, None) == "flat"


def test_weighttrend_is_frozen_dataclass():
    t = WeightTrend(current_avg=64.0, prior_avg=65.0, delta_kg=-1.0, direction="down")
    assert t.direction == "down"
