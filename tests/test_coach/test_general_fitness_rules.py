from services.coach.general_fitness import consistent_week


def test_consistent_week_at_threshold():
    # 4 of 5 = 0.8 exactly -> consistent
    assert consistent_week(planned=5, completed=4) is True


def test_consistent_week_below_threshold():
    # 3 of 5 = 0.6 -> not consistent
    assert consistent_week(planned=5, completed=3) is False


def test_consistent_week_zero_planned_is_false():
    assert consistent_week(planned=0, completed=0) is False


from services.coach.general_fitness import duration_bump


def test_duration_bump_below_two_weeks_is_zero():
    assert duration_bump(0) == (0, False)
    assert duration_bump(1) == (0, False)


def test_duration_bump_accrues_every_two_consistent_weeks():
    assert duration_bump(2) == (5, False)
    assert duration_bump(4) == (10, False)
    assert duration_bump(6) == (15, False)


def test_duration_bump_caps_at_thirty():
    assert duration_bump(12) == (30, True)
    assert duration_bump(20) == (30, True)


from services.coach.general_fitness import should_add_training_day


def test_add_day_fires_after_three_weeks_under_four_days():
    assert should_add_training_day(streak_weeks=3, current_days=3) is True


def test_add_day_not_before_three_weeks():
    assert should_add_training_day(streak_weeks=2, current_days=3) is False


def test_add_day_not_when_already_four_days():
    assert should_add_training_day(streak_weeks=5, current_days=4) is False


from services.coach.general_fitness import suggest_run_rotation


def test_rotation_fires_on_monotonous_window():
    suggested, note = suggest_run_rotation(["easy", "easy", "easy"])
    assert suggested == "interval"          # first preference not already used
    assert "easy" in note and "interval" in note


def test_rotation_none_when_varied():
    assert suggest_run_rotation(["easy", "interval", "easy"]) == (None, "")


def test_rotation_none_when_window_too_short():
    assert suggest_run_rotation(["easy", "easy"]) == (None, "")


def test_rotation_skips_long_run_underscore_in_copy():
    suggested, note = suggest_run_rotation(["long_run", "long_run", "long_run"])
    assert suggested == "easy"
    assert "long run" in note               # underscores humanized in copy
