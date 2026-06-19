from dataclasses import dataclass

INCREMENT_KG = 2.5  # default progression step (metric); tunable


@dataclass(frozen=True)
class WeightSuggestion:
    exercise_id: int
    suggested_weight_kg: float | None
    reason: str   # new | progress | hold | backoff | deload
    note: str


def round_to_increment(weight: float, increment: float) -> float:
    return round(round(weight / increment) * increment, 2)


def working_weight(weight_kg: list) -> float | None:
    """Top working set for a session, or None when nothing was logged."""
    return float(max(weight_kg)) if weight_kg else None


def met_target(sets_completed: int, reps_completed: list, skipped: bool,
               prescribed_sets: int, prescribed_reps: int) -> bool:
    if skipped:
        return False
    if sets_completed < prescribed_sets:
        return False
    if not reps_completed:
        return False
    return all(r >= prescribed_reps for r in reps_completed)


def suggest_next_weight(sessions, increment_kg, is_deload):
    """Decide next weight from one exercise's history (oldest -> newest), each
    session a (working_weight, met_target) tuple. Returns (weight|None, reason, note)."""
    if not sessions:
        return (None, "new", "Log a few sessions and I'll start suggesting loads.")
    current = sessions[-1][0]
    if is_deload:
        return (round_to_increment(current * 0.8, increment_kg), "deload",
                "Deload week — back off to ~80%.")
    last_two = sessions[-2:]
    if len(last_two) == 2 and all(met for _, met in last_two):
        return (round_to_increment(current + increment_kg, increment_kg), "progress",
                f"Hit it twice — go up {increment_kg:g} kg.")
    if len(last_two) == 2 and not any(met for _, met in last_two):
        return (round_to_increment(current * 0.9, increment_kg), "backoff",
                "Two tough sessions — drop 10% and rebuild.")
    return (current, "hold", "Stay here and nail all your sets.")
