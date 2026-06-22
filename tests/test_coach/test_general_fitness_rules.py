from services.coach.general_fitness import consistent_week


def test_consistent_week_at_threshold():
    # 4 of 5 = 0.8 exactly -> consistent
    assert consistent_week(planned=5, completed=4) is True


def test_consistent_week_below_threshold():
    # 3 of 5 = 0.6 -> not consistent
    assert consistent_week(planned=5, completed=3) is False


def test_consistent_week_zero_planned_is_false():
    assert consistent_week(planned=0, completed=0) is False
