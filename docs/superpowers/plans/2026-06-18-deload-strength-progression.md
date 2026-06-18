# Deload + Strength Progression Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add the mandatory 4th-week deload into the decision engine and a compute-on-read strength weight-progression service, surfaced on the weekly-plan page.

**Architecture:** Deload extends the existing pure `decide`/`decide_today` in `services/coach/engine.py` (intensity ×0.8 + flag + headline rationale on the intensity path; week number from the active plan). Strength progression is a new `services/coach/progression.py` with pure rules + a DB service reading `ExerciseLog` history, matched across weeks by exercise identity. Both are advisory — no writes, no plan mutation, no Claude.

**Tech Stack:** Python 3.13, Django 5.1, pytest + pytest-django, HTMX dark-UI templates. Run Python via `.venv/bin/python`.

**Spec:** `docs/superpowers/specs/2026-06-18-deload-strength-progression-design.md`

**Conventions (verified):**
- Tests in `tests/test_<app>/test_*.py`; `@pytest.mark.django_db` only where DB is needed.
- `HealthSnapshot`/`Momentum`/`SorenessItem` are plain dataclasses; engine pure tests use `types.SimpleNamespace` for `workout_day`.
- `WorkoutExercise`: `section` (main/warmup/…), `sets`/`reps` (nullable ints), `exercise_cache` (FK nullable), `custom_name`, `intensity` (required, choices low/moderate/high), `display_name` = `exercise_cache.name or custom_name`.
- `ExerciseLog`: `workout_log` (→ user, date), `workout_exercise`, `sets_completed`, `reps_completed` (JSON list), `weight_kg` (JSON list), `skipped`.
- `ExerciseCache` requires `wger_id` (unique int), `name`, `category`.

---

### Task 1: Deload in the decision engine

**Files:**
- Modify: `services/coach/engine.py`
- Test: `tests/test_coach/test_deload.py`

- [ ] **Step 1: Write failing deload tests**

Create `tests/test_coach/test_deload.py`:

```python
from datetime import date
from decimal import Decimal
from types import SimpleNamespace

import pytest
from django.contrib.auth.models import User
from apps.accounts.models import UserProfile
from apps.fitness.models import FitnessPlan, WorkoutDay

from services.health.snapshot import HealthSnapshot, SorenessItem
from services.health.calculations import Momentum
from services.coach.engine import decide, decide_today, is_deload_week


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


def _workout(day_type="strength", focus_area="upper_body"):
    return SimpleNamespace(day_type=day_type, focus_area=focus_area)


def test_is_deload_week():
    assert is_deload_week(1) is False
    assert is_deload_week(2) is False
    assert is_deload_week(3) is False
    assert is_deload_week(4) is True
    assert is_deload_week(8) is True
    assert is_deload_week(12) is True
    assert is_deload_week(0) is False


def test_deload_applies_intensity_flag_and_rationale():
    d = decide(_snap(), _workout(), is_deload=True)
    assert d.intensity_modifier == 0.8
    assert "deload" in d.flags
    assert "deload" in d.rationale.lower()
    assert d.is_override is True


def test_deload_compounds_with_low_energy():
    d = decide(_snap(energy=2), _workout(), is_deload=True)  # 0.7 * 0.8
    assert d.intensity_modifier == 0.56
    assert "deload" in d.flags


def test_deload_does_not_fire_on_hard_stop():
    sore = [SorenessItem("quads", "severe", "lower_body")]
    d = decide(_snap(soreness=sore), _workout(focus_area="lower_body"), is_deload=True)
    assert d.recommended_day_type == "active_recovery"
    assert "deload" not in d.flags


def test_decide_without_deload_is_unchanged():
    d = decide(_snap(), _workout())
    assert "deload" not in d.flags
    assert d.intensity_modifier == 1.0


def _user(username):
    u = User.objects.create_user(username=username, password="x", email=f"{username}@e.com")
    UserProfile.objects.create(
        user=u, height_cm=170, weight_kg=65, gender="female",
        date_of_birth=date(1992, 3, 3), fitness_experience="beginner",
        primary_goal="Get active", diet_type="omnivore", food_allergies=[],
        daily_routine="", wake_time="07:00", sleep_time="23:00",
        work_schedule="9-5", workout_days_per_week=3, preferred_workout_days=[],
        workout_location="home", available_equipment=[],
        notification_email=f"{username}@e.com",
    )
    return u


def _plan(user, week_number):
    today = date.today()
    plan = FitnessPlan.objects.create(
        user=user, week_number=week_number, start_date=today, end_date=today,
        total_workout_days=1, weekly_goal_summary="g", claude_reasoning="r",
    )
    WorkoutDay.objects.create(
        fitness_plan=plan, date=today, day_of_week=today.strftime("%A"),
        day_type="strength", focus_area="upper_body", estimated_duration_minutes=45,
    )
    return plan


@pytest.mark.django_db
def test_decide_today_deload_on_week_4():
    user = _user("dl4")
    _plan(user, week_number=4)
    d = decide_today(user, date.today())
    assert "deload" in d.flags


@pytest.mark.django_db
def test_decide_today_no_deload_on_week_3():
    user = _user("dl3")
    _plan(user, week_number=3)
    d = decide_today(user, date.today())
    assert "deload" not in d.flags
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `.venv/bin/python -m pytest tests/test_coach/test_deload.py -v`
Expected: FAIL — `is_deload_week` not defined / `decide` has no `is_deload`.

- [ ] **Step 3: Add deload constants and `is_deload_week`**

In `services/coach/engine.py`, add to the constants block (near `OVERTRAIN_STREAK`):

```python
DELOAD_CYCLE_WEEKS = 4   # every 4th week is a deload week
DELOAD_MULTIPLIER = 0.8  # -20% intensity on a deload week
DELOAD_RATIONALE = "Deload week — lighter loads, trim your sets ~40% to recover."
```

Add this function at module level (e.g. just below the constants, above `decide`):

```python
def is_deload_week(week_number) -> bool:
    return bool(week_number) and week_number % DELOAD_CYCLE_WEEKS == 0
```

- [ ] **Step 4: Thread `is_deload` through `decide`**

In `services/coach/engine.py`, change the `decide` signature:

```python
def decide(snapshot, workout_day, is_deload=False) -> DailyDecision:
```

Then replace the clamp-and-rationale block at the end of the intensity path (currently the lines from `modifier = round(max(...))` through the `if candidates: … else: …` block) with:

```python
    if is_deload:
        modifier *= DELOAD_MULTIPLIER
        flags.append("deload")

    modifier = round(max(MIN_INTENSITY, min(MAX_INTENSITY, modifier)), 3)

    if is_deload:
        rationale = DELOAD_RATIONALE
    elif candidates:
        # Tie on deviation: appearance order wins (energy > momentum > cycle > streak).
        rationale = max(candidates, key=lambda c: abs(c[0] - 1.0))[1]
    else:
        rationale = "On plan — go for it."
```

(The hard stops above return early, so `is_deload` only affects the intensity path — it never overrides active recovery. The final `return DailyDecision(...)` and `is_override=abs(modifier - 1.0) > 1e-9` are unchanged.)

- [ ] **Step 5: Compute `is_deload` in `decide_today`**

In `services/coach/engine.py`, replace the body of `decide_today` with:

```python
def decide_today(user, on_date, workout_day=_UNSET) -> DailyDecision:
    """Fetch today's snapshot + planned workout and return the daily decision.

    Pass `workout_day` (possibly None) to reuse an already-resolved WorkoutDay and
    skip the workout query; omit it to have this function resolve today's
    active-plan workout itself. The active plan is always read once for its
    week number (deload detection).
    """
    from apps.fitness.models import FitnessPlan, WorkoutDay
    snapshot = get_health_snapshot(user, on_date)
    plan = FitnessPlan.objects.filter(user=user, is_active=True).first()
    if workout_day is _UNSET:
        workout_day = None
        if plan is not None:
            workout_day = WorkoutDay.objects.filter(
                fitness_plan=plan, day_of_week=on_date.strftime("%A")
            ).first()
    is_deload = is_deload_week(plan.week_number) if plan is not None else False
    return decide(snapshot, workout_day, is_deload=is_deload)
```

- [ ] **Step 6: Run tests to verify they pass**

Run: `.venv/bin/python -m pytest tests/test_coach/test_deload.py -v`
Expected: PASS (7 tests).

- [ ] **Step 7: Run the full coach suite (no regressions)**

Run: `.venv/bin/python -m pytest tests/test_coach/ -q`
Expected: PASS (existing engine/decide_today tests still green).

- [ ] **Step 8: Commit**

```bash
git add services/coach/engine.py tests/test_coach/test_deload.py
git commit -m "feat: add 4th-week deload to the decision engine"
```

---

### Task 2: Strength progression — pure rules

**Files:**
- Create: `services/coach/progression.py`
- Test: `tests/test_coach/test_progression_rules.py`

- [ ] **Step 1: Write failing rule tests**

Create `tests/test_coach/test_progression_rules.py`:

```python
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
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `.venv/bin/python -m pytest tests/test_coach/test_progression_rules.py -v`
Expected: FAIL — `services.coach.progression` does not exist.

- [ ] **Step 3: Implement the pure rules**

Create `services/coach/progression.py`:

```python
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
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `.venv/bin/python -m pytest tests/test_coach/test_progression_rules.py -v`
Expected: PASS (13 tests).

- [ ] **Step 5: Commit**

```bash
git add services/coach/progression.py tests/test_coach/test_progression_rules.py
git commit -m "feat: add strength weight-progression rules"
```

---

### Task 3: Strength progression — DB service

**Files:**
- Modify: `services/coach/progression.py`
- Test: `tests/test_coach/test_progression_service.py`

- [ ] **Step 1: Write failing service tests**

Create `tests/test_coach/test_progression_service.py`:

```python
import pytest
from datetime import date, timedelta
from django.contrib.auth.models import User
from apps.accounts.models import UserProfile
from apps.exercises.models import ExerciseCache
from apps.fitness.models import (
    FitnessPlan, WorkoutDay, WorkoutExercise, WorkoutLog, ExerciseLog,
)
from services.coach.progression import suggest_strength_progression


def _user(username="pr"):
    u = User.objects.create_user(username=username, password="x", email=f"{username}@e.com")
    UserProfile.objects.create(
        user=u, height_cm=170, weight_kg=65, gender="female",
        date_of_birth=date(1992, 3, 3), fitness_experience="beginner",
        primary_goal="Get active", diet_type="omnivore", food_allergies=[],
        daily_routine="", wake_time="07:00", sleep_time="23:00",
        work_schedule="9-5", workout_days_per_week=3, preferred_workout_days=[],
        workout_location="home", available_equipment=[],
        notification_email=f"{username}@e.com",
    )
    return u


def _session(user, weights, days_ago, custom_name="Goblet Squat", cache=None,
             met=True, sets=3, reps=10, week=1):
    d = date.today() - timedelta(days=days_ago)
    plan = FitnessPlan.objects.create(
        user=user, week_number=week, start_date=d, end_date=d, is_active=False,
        total_workout_days=1, weekly_goal_summary="g", claude_reasoning="r",
    )
    wd = WorkoutDay.objects.create(
        fitness_plan=plan, date=d, day_of_week=d.strftime("%A"),
        day_type="strength", focus_area="lower_body", estimated_duration_minutes=45,
    )
    ex = WorkoutExercise.objects.create(
        workout_day=wd, section="main", sets=sets, reps=reps,
        custom_name="" if cache else custom_name, exercise_cache=cache,
        intensity="moderate",
    )
    wl = WorkoutLog.objects.create(user=user, workout_day=wd, date=d, completed=True)
    reps_completed = [reps] * sets if met else [reps - 5] * sets
    ExerciseLog.objects.create(
        workout_log=wl, workout_exercise=ex,
        sets_completed=sets if met else sets - 1,
        reps_completed=reps_completed, weight_kg=weights,
    )


def _current(user, custom_name="Goblet Squat", cache=None):
    today = date.today()
    plan = FitnessPlan.objects.create(
        user=user, week_number=3, start_date=today, end_date=today, is_active=True,
        total_workout_days=1, weekly_goal_summary="g", claude_reasoning="r",
    )
    wd = WorkoutDay.objects.create(
        fitness_plan=plan, date=today, day_of_week=today.strftime("%A"),
        day_type="strength", focus_area="lower_body", estimated_duration_minutes=45,
    )
    ex = WorkoutExercise.objects.create(
        workout_day=wd, section="main", sets=3, reps=10,
        custom_name="" if cache else custom_name, exercise_cache=cache,
        intensity="moderate",
    )
    return wd, ex


@pytest.mark.django_db
def test_progress_after_two_met_weeks_custom_name():
    user = _user()
    _session(user, [40, 40, 40], days_ago=14)
    _session(user, [40, 40, 40], days_ago=7)
    cwd, cex = _current(user)
    s = suggest_strength_progression(user, cwd, is_deload=False)[cex.id]
    assert s.reason == "progress"
    assert s.suggested_weight_kg == 42.5


@pytest.mark.django_db
def test_new_when_no_history():
    user = _user()
    cwd, cex = _current(user, custom_name="Bench Press")
    s = suggest_strength_progression(user, cwd, is_deload=False)[cex.id]
    assert s.reason == "new"
    assert s.suggested_weight_kg is None


@pytest.mark.django_db
def test_backoff_after_two_misses():
    user = _user()
    _session(user, [60, 60, 60], days_ago=14, custom_name="Deadlift", met=False)
    _session(user, [60, 60, 60], days_ago=7, custom_name="Deadlift", met=False)
    cwd, cex = _current(user, custom_name="Deadlift")
    s = suggest_strength_progression(user, cwd, is_deload=False)[cex.id]
    assert s.reason == "backoff"
    assert s.suggested_weight_kg == 55.0  # 60*0.9=54 -> nearest 2.5


@pytest.mark.django_db
def test_identity_matches_via_exercise_cache():
    user = _user()
    cache = ExerciseCache.objects.create(wger_id=1, name="Back Squat", category="legs")
    _session(user, [80, 80, 80], days_ago=14, cache=cache)
    _session(user, [80, 80, 80], days_ago=7, cache=cache)
    cwd, cex = _current(user, cache=cache)
    s = suggest_strength_progression(user, cwd, is_deload=False)[cex.id]
    assert s.reason == "progress"
    assert s.suggested_weight_kg == 82.5


@pytest.mark.django_db
def test_deload_trims_suggestion():
    user = _user()
    _session(user, [30, 30, 30], days_ago=14, custom_name="Overhead Press")
    _session(user, [30, 30, 30], days_ago=7, custom_name="Overhead Press")
    cwd, cex = _current(user, custom_name="Overhead Press")
    s = suggest_strength_progression(user, cwd, is_deload=True)[cex.id]
    assert s.reason == "deload"
    assert s.suggested_weight_kg == 25.0  # 30*0.8=24 -> nearest 2.5
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `.venv/bin/python -m pytest tests/test_coach/test_progression_service.py -v`
Expected: FAIL — `suggest_strength_progression` not defined.

- [ ] **Step 3: Implement the service**

Append to `services/coach/progression.py`:

```python
def suggest_strength_progression(user, workout_day, is_deload):
    """Map each main-section weighted exercise on `workout_day` to a WeightSuggestion,
    using this user's prior ExerciseLog history for the same exercise identity."""
    from apps.fitness.models import ExerciseLog

    suggestions = {}
    main_exercises = workout_day.exercises.filter(
        section="main", sets__isnull=False, reps__isnull=False,
    )
    for ex in main_exercises:
        if ex.exercise_cache_id is not None:
            logs = ExerciseLog.objects.filter(
                workout_log__user=user,
                workout_exercise__exercise_cache_id=ex.exercise_cache_id,
            )
        else:
            logs = ExerciseLog.objects.filter(
                workout_log__user=user,
                workout_exercise__custom_name=ex.custom_name,
            )
        logs = logs.select_related("workout_exercise").order_by("workout_log__date")

        sessions = []
        for log in logs:
            w = working_weight(log.weight_kg)
            if w is None:
                continue
            we = log.workout_exercise
            sessions.append((
                w,
                met_target(log.sets_completed, log.reps_completed, log.skipped,
                           we.sets or 0, we.reps or 0),
            ))

        weight, reason, note = suggest_next_weight(sessions, INCREMENT_KG, is_deload)
        suggestions[ex.id] = WeightSuggestion(
            exercise_id=ex.id, suggested_weight_kg=weight, reason=reason, note=note,
        )
    return suggestions
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `.venv/bin/python -m pytest tests/test_coach/test_progression_service.py -v`
Expected: PASS (5 tests).

- [ ] **Step 5: Commit**

```bash
git add services/coach/progression.py tests/test_coach/test_progression_service.py
git commit -m "feat: add strength progression service over ExerciseLog history"
```

---

### Task 4: Surface deload + suggestions on the weekly plan

**Files:**
- Modify: `apps/dashboard/views.py`
- Modify: `templates/dashboard/weekly_plan.html`
- Modify: `static/css/app.css`
- Test: `tests/test_dashboard/test_deload_surfacing.py`

- [ ] **Step 1: Write failing surfacing tests**

Create `tests/test_dashboard/test_deload_surfacing.py`:

```python
import pytest
from datetime import date, timedelta
from django.urls import reverse
from django.contrib.auth.models import User
from apps.accounts.models import UserProfile
from apps.fitness.models import (
    FitnessPlan, WorkoutDay, WorkoutExercise, WorkoutLog, ExerciseLog,
)


def _user():
    u = User.objects.create_user(username="wp", password="testpass123", email="wp@e.com")
    UserProfile.objects.create(
        user=u, height_cm=170, weight_kg=65, gender="female",
        date_of_birth=date(1992, 3, 3), fitness_experience="beginner",
        primary_goal="Get active", diet_type="omnivore", food_allergies=[],
        daily_routine="", wake_time="07:00", sleep_time="23:00",
        work_schedule="9-5", workout_days_per_week=3, preferred_workout_days=[],
        workout_location="home", available_equipment=[],
        notification_email="wp@e.com", onboarding_completed=True,
    )
    return u


def _plan(user, week_number):
    today = date.today()
    return FitnessPlan.objects.create(
        user=user, week_number=week_number, start_date=today, end_date=today,
        is_active=True, total_workout_days=1, weekly_goal_summary="g", claude_reasoning="r",
    )


@pytest.mark.django_db
def test_weekly_plan_shows_deload_badge_on_week_4(client):
    _plan(_user(), 4)
    client.login(username="wp", password="testpass123")
    resp = client.get(reverse("weekly_plan"))
    assert resp.context["is_deload"] is True
    assert "deload-badge" in resp.content.decode()


@pytest.mark.django_db
def test_weekly_plan_no_badge_on_week_3(client):
    _plan(_user(), 3)
    client.login(username="wp", password="testpass123")
    resp = client.get(reverse("weekly_plan"))
    assert resp.context["is_deload"] is False
    assert "deload-badge" not in resp.content.decode()


@pytest.mark.django_db
def test_weekly_plan_shows_weight_suggestion(client):
    user = _user()
    plan = _plan(user, 3)
    today = date.today()
    # Today's workout with a main lift (so it renders in the active tab).
    wd = WorkoutDay.objects.create(
        fitness_plan=plan, date=today, day_of_week=today.strftime("%A"),
        day_type="strength", focus_area="lower_body", estimated_duration_minutes=45,
    )
    ex = WorkoutExercise.objects.create(
        workout_day=wd, section="main", sets=3, reps=10,
        custom_name="Goblet Squat", intensity="moderate",
    )
    # One prior logged session of the same lift in an earlier (inactive) plan ->
    # a single-session "hold" suggestion at 40 kg. Kept out of the active plan so it
    # never collides with today's weekday in the weekly view.
    past = today - timedelta(days=7)
    old_plan = FitnessPlan.objects.create(
        user=user, week_number=2, start_date=past, end_date=past, is_active=False,
        total_workout_days=1, weekly_goal_summary="g", claude_reasoning="r",
    )
    pwd = WorkoutDay.objects.create(
        fitness_plan=old_plan, date=past, day_of_week=past.strftime("%A"),
        day_type="strength", focus_area="lower_body", estimated_duration_minutes=45,
    )
    pex = WorkoutExercise.objects.create(
        workout_day=pwd, section="main", sets=3, reps=10,
        custom_name="Goblet Squat", intensity="moderate",
    )
    wl = WorkoutLog.objects.create(user=user, workout_day=pwd, date=past, completed=True)
    ExerciseLog.objects.create(
        workout_log=wl, workout_exercise=pex,
        sets_completed=3, reps_completed=[10, 10, 10], weight_kg=[40, 40, 40],
    )

    client.login(username="wp", password="testpass123")
    resp = client.get(reverse("weekly_plan"))
    assert "weight_suggestions" in resp.context
    assert resp.context["weight_suggestions"][ex.id].suggested_weight_kg == 40.0
    assert "40.0 kg" in resp.content.decode()
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `.venv/bin/python -m pytest tests/test_dashboard/test_deload_surfacing.py -v`
Expected: FAIL — `is_deload` not in context.

- [ ] **Step 3: Compute deload + suggestions in the view**

In `apps/dashboard/views.py`, add near the top imports:

```python
from services.coach.engine import is_deload_week
from services.coach.progression import suggest_strength_progression
```

In the `weekly_plan` view, locate the `if fitness_plan:` block that builds `workout_days`. Initialize the two values before that block and populate them inside it. Concretely, just after `fitness_plan = FitnessPlan.objects.filter(...).first()` add:

```python
    is_deload = False
    weight_suggestions = {}
```

and inside the existing `if fitness_plan:` block (after `workout_days = {...}` is built), add:

```python
        is_deload = is_deload_week(fitness_plan.week_number)
        for wd in workout_days.values():
            weight_suggestions.update(
                suggest_strength_progression(request.user, wd, is_deload)
            )
```

Add these two keys to the `render(...)` context dict for `weekly_plan`:

```python
        "is_deload": is_deload,
        "weight_suggestions": weight_suggestions,
```

- [ ] **Step 4: Render the badge and suggestion column**

In `templates/dashboard/weekly_plan.html`:

Add the filter load immediately after the `{% extends %}` line (line 1):

```html
{% load health_extras %}
```

Replace the Week heading (line 11) with one that shows the badge:

```html
  <h1 style="font-size:18px;font-weight:800;color:#fff;margin-bottom:4px;">Week {{ fitness_plan.week_number }}{% if is_deload %} <span class="deload-badge">Deload</span>{% endif %}</h1>
```

Replace the exercise-table header row (line 76):

```html
          <tr><th>Exercise</th><th>Section</th><th>Volume</th><th>Intensity</th><th>Suggested</th><th>Notes</th></tr>
```

Add a suggestion cell to each row — insert it between the Intensity cell (line 88) and the Notes cell (line 89), i.e. after `<td>{{ ex.intensity }}</td>`:

```html
            <td>{% with s=weight_suggestions|get_item:ex.id %}{% if s and s.suggested_weight_kg %}{{ s.suggested_weight_kg }} kg{% endif %}{% endwith %}</td>
```

- [ ] **Step 5: Add the deload-badge CSS**

In `static/css/app.css`, append:

```css
.deload-badge {
  display: inline-block;
  font-size: 10px;
  font-weight: 800;
  text-transform: uppercase;
  letter-spacing: 0.5px;
  color: #fbbf24;
  background: rgba(251, 191, 36, 0.15);
  border: 1px solid rgba(251, 191, 36, 0.4);
  padding: 2px 8px;
  border-radius: 999px;
  vertical-align: middle;
}
```

- [ ] **Step 6: Run tests to verify they pass**

Run: `.venv/bin/python -m pytest tests/test_dashboard/test_deload_surfacing.py -v`
Expected: PASS (3 tests).

- [ ] **Step 7: Run dashboard + coach suites and Django check**

Run: `.venv/bin/python -m pytest tests/test_dashboard/ tests/test_coach/ -q`
Expected: PASS.
Run: `.venv/bin/python manage.py check`
Expected: 0 issues.

- [ ] **Step 8: Commit**

```bash
git add apps/dashboard/views.py templates/dashboard/weekly_plan.html static/css/app.css tests/test_dashboard/test_deload_surfacing.py
git commit -m "feat: surface deload badge and weight suggestions on the weekly plan"
```

---

## Notes for the implementer

- Run Python through `.venv/bin/python`.
- Branch: `feature/deload-strength-progression` (off the merged `main`, which has slice #3's `engine.py`). Spec committed alongside this plan.
- The engine and progression service perform **no writes**; the weekly `WorkoutExercise`/plan is never mutated. Suggestions are advisory display only.
- Out of scope: weight-loss/running/general progression (#4b, #4c), persistence, auto-applying weights, 1RM/plate math, any Claude call.
