from services.coach.progression import (
    round_to_increment, working_weight, met_target, suggest_next_weight,
)


def test_round_to_increment():
    assert round_to_increment(43.2, 2.5) == 42.5
    assert round_to_increment(44.0, 2.5) == 45.0
    assert round_to_increment(0.0, 2.5) == 0.0


def test_working_weight_is_top_set():
    assert working_weight([40, 42.5, 45]) == 45.0
    assert working_weight([]) is None


def test_met_target_true_when_sets_and_reps_met():
    assert met_target(3, [10, 10, 10], False, 3, 10) is True


def test_met_target_false_when_skipped():
    assert met_target(3, [10, 10, 10], True, 3, 10) is False


def test_met_target_false_when_fewer_sets():
    assert met_target(2, [10, 10], False, 3, 10) is False


def test_met_target_false_when_reps_short():
    assert met_target(3, [10, 9, 10], False, 3, 10) is False


def test_met_target_false_when_no_reps():
    assert met_target(3, [], False, 3, 10) is False


def test_suggest_new_when_no_history():
    weight, reason, note = suggest_next_weight([], 2.5, False)
    assert weight is None
    assert reason == "new"


def test_suggest_progress_after_two_met_sessions():
    weight, reason, note = suggest_next_weight([(40.0, True), (40.0, True)], 2.5, False)
    assert weight == 42.5
    assert reason == "progress"


def test_suggest_hold_on_single_recent_miss():
    weight, reason, note = suggest_next_weight([(40.0, True), (40.0, False)], 2.5, False)
    assert weight == 40.0
    assert reason == "hold"


def test_suggest_hold_on_lone_session():
    weight, reason, note = suggest_next_weight([(40.0, True)], 2.5, False)
    assert weight == 40.0
    assert reason == "hold"


def test_suggest_backoff_after_two_misses():
    weight, reason, note = suggest_next_weight([(40.0, False), (40.0, False)], 2.5, False)
    assert weight == 35.0  # 40*0.9=36 -> nearest 2.5
    assert reason == "backoff"


def test_deload_override_beats_progress():
    weight, reason, note = suggest_next_weight([(40.0, True), (40.0, True)], 2.5, True)
    assert weight == 32.5  # 40*0.8=32 -> nearest 2.5
    assert reason == "deload"
