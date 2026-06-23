# General-Fitness Progression Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add advisory general-fitness progressions — gradual session-duration growth, a "add a 4th day" volume nudge, and run-type rotation — surfaced on the dashboard and weekly plan.

**Architecture:** One new self-contained module `services/coach/general_fitness.py` holds pure rule functions plus compute-on-read DB services and two frozen dataclasses. All output is advisory; nothing mutates the plan or calls Claude. Surfaced read-only on the dashboard and weekly-plan views. Mirrors the `services/coach/cardio.py` (#4b) pattern.

**Tech Stack:** Python 3, Django 5.1, pytest + pytest-django. Metric units.

---

## File Structure

- **Create** `services/coach/general_fitness.py` — constants, `RunRotation` + `GeneralFitnessSuggestions` dataclasses, pure rules (`consistent_week`, `duration_bump`, `should_add_training_day`, `suggest_run_rotation`), DB services (`consistent_week_streak`, `get_suggestions`).
- **Create** `tests/test_coach/test_general_fitness_rules.py` — pure-rule unit tests.
- **Create** `tests/test_coach/test_general_fitness_services.py` — DB-service tests.
- **Create** `tests/test_dashboard/test_general_fitness_surfacing.py` — dashboard + weekly-plan surfacing tests.
- **Modify** `apps/dashboard/views.py` — call `get_suggestions` in `dashboard` and `weekly_plan`, add to context.
- **Modify** `templates/dashboard/index.html` — coach block.
- **Modify** `templates/dashboard/weekly_plan.html` — per-session duration hint + run-rotation note.

Each pure rule is one TDD cycle. DB services and surfacing follow. Reference module to imitate: `services/coach/cardio.py`.

---

### Task 1: Module scaffold + `consistent_week`

**Files:**
- Create: `services/coach/general_fitness.py`
- Test: `tests/test_coach/test_general_fitness_rules.py`

- [ ] **Step 1: Write the failing test**

```python
# tests/test_coach/test_general_fitness_rules.py
from services.coach.general_fitness import consistent_week


def test_consistent_week_at_threshold():
    # 4 of 5 = 0.8 exactly -> consistent
    assert consistent_week(planned=5, completed=4) is True


def test_consistent_week_below_threshold():
    # 3 of 5 = 0.6 -> not consistent
    assert consistent_week(planned=5, completed=3) is False


def test_consistent_week_zero_planned_is_false():
    assert consistent_week(planned=0, completed=0) is False
```

- [ ] **Step 2: Run test to verify it fails**

Run: `.venv/bin/python -m pytest tests/test_coach/test_general_fitness_rules.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'services.coach.general_fitness'`

- [ ] **Step 3: Write minimal implementation**

```python
# services/coach/general_fitness.py
from dataclasses import dataclass

# --- Tunable constants -------------------------------------------------------
CONSISTENCY_THRESHOLD = 0.8
DURATION_INCREMENT_MIN = 5
BUMP_EVERY_CONSISTENT_WEEKS = 2
DURATION_CAP_MIN = 30
FOURTH_DAY_STREAK = 3
MAX_TRAINING_DAYS = 4
RUN_MONOTONY_WINDOW = 3
DURATION_BUMP_DAY_TYPES = ("strength", "yoga")
ROTATION_PREFERENCE = ["easy", "interval", "tempo", "long_run", "fartlek"]


def consistent_week(planned: int, completed: int,
                    threshold: float = CONSISTENCY_THRESHOLD) -> bool:
    """A week counts as consistent when >= threshold of its planned (non-rest)
    workouts were completed. A week with nothing planned is not consistent."""
    return planned > 0 and completed / planned >= threshold
```

- [ ] **Step 4: Run test to verify it passes**

Run: `.venv/bin/python -m pytest tests/test_coach/test_general_fitness_rules.py -v`
Expected: PASS (3 passed)

- [ ] **Step 5: Commit**

```bash
git add services/coach/general_fitness.py tests/test_coach/test_general_fitness_rules.py
git commit -m "feat: add general-fitness module scaffold and consistent_week rule"
```

---

### Task 2: `duration_bump` rule

**Files:**
- Modify: `services/coach/general_fitness.py`
- Test: `tests/test_coach/test_general_fitness_rules.py`

- [ ] **Step 1: Write the failing test** (append)

```python
from services.coach.general_fitness import duration_bump


def test_duration_bump_below_two_weeks_is_zero():
    assert duration_bump(0) == (0, False)
    assert duration_bump(1) == (0, False)


def test_duration_bump_accrues_every_two_consistent_weeks():
    assert duration_bump(2) == (5, False)
    assert duration_bump(4) == (10, False)
    assert duration_bump(6) == (15, False)


def test_duration_bump_caps_at_thirty():
    # 12 consistent weeks -> 6 bumps * 5 = 30, capped
    assert duration_bump(12) == (30, True)
    # beyond the cap still clamps to 30 and stays capped
    assert duration_bump(20) == (30, True)
```

- [ ] **Step 2: Run test to verify it fails**

Run: `.venv/bin/python -m pytest tests/test_coach/test_general_fitness_rules.py -k duration_bump -v`
Expected: FAIL — `ImportError: cannot import name 'duration_bump'`

- [ ] **Step 3: Write minimal implementation** (append to `general_fitness.py`)

```python
def duration_bump(streak_weeks: int) -> tuple[int, bool]:
    """Minutes to add per session given a consistent-week streak, and whether the
    +30 min cap has been reached. +5 min per 2 consistent weeks."""
    bumps = streak_weeks // BUMP_EVERY_CONSISTENT_WEEKS
    raw = bumps * DURATION_INCREMENT_MIN
    return min(raw, DURATION_CAP_MIN), raw >= DURATION_CAP_MIN
```

- [ ] **Step 4: Run test to verify it passes**

Run: `.venv/bin/python -m pytest tests/test_coach/test_general_fitness_rules.py -k duration_bump -v`
Expected: PASS (3 passed)

- [ ] **Step 5: Commit**

```bash
git add services/coach/general_fitness.py tests/test_coach/test_general_fitness_rules.py
git commit -m "feat: add duration_bump progression rule"
```

---

### Task 3: `should_add_training_day` rule

**Files:**
- Modify: `services/coach/general_fitness.py`
- Test: `tests/test_coach/test_general_fitness_rules.py`

- [ ] **Step 1: Write the failing test** (append)

```python
from services.coach.general_fitness import should_add_training_day


def test_add_day_fires_after_three_weeks_under_four_days():
    assert should_add_training_day(streak_weeks=3, current_days=3) is True


def test_add_day_not_before_three_weeks():
    assert should_add_training_day(streak_weeks=2, current_days=3) is False


def test_add_day_not_when_already_four_days():
    assert should_add_training_day(streak_weeks=5, current_days=4) is False
```

- [ ] **Step 2: Run test to verify it fails**

Run: `.venv/bin/python -m pytest tests/test_coach/test_general_fitness_rules.py -k add_day -v`
Expected: FAIL — `ImportError: cannot import name 'should_add_training_day'`

- [ ] **Step 3: Write minimal implementation** (append)

```python
def should_add_training_day(streak_weeks: int, current_days: int) -> bool:
    """Nudge to add a training day after a 3-consistent-week streak, but only for
    users training fewer than 4 days/week."""
    return streak_weeks >= FOURTH_DAY_STREAK and current_days < MAX_TRAINING_DAYS
```

- [ ] **Step 4: Run test to verify it passes**

Run: `.venv/bin/python -m pytest tests/test_coach/test_general_fitness_rules.py -k add_day -v`
Expected: PASS (3 passed)

- [ ] **Step 5: Commit**

```bash
git add services/coach/general_fitness.py tests/test_coach/test_general_fitness_rules.py
git commit -m "feat: add should_add_training_day rule"
```

---

### Task 4: `RunRotation` dataclass + `suggest_run_rotation` rule

**Files:**
- Modify: `services/coach/general_fitness.py`
- Test: `tests/test_coach/test_general_fitness_rules.py`

- [ ] **Step 1: Write the failing test** (append)

```python
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
```

- [ ] **Step 2: Run test to verify it fails**

Run: `.venv/bin/python -m pytest tests/test_coach/test_general_fitness_rules.py -k rotation -v`
Expected: FAIL — `ImportError: cannot import name 'suggest_run_rotation'`

- [ ] **Step 3: Write minimal implementation**

Add the dataclass near the top of `general_fitness.py` (after the constants):

```python
@dataclass(frozen=True)
class RunRotation:
    recent_type: str
    suggested_type: str
    note: str
```

Add the rule (append):

```python
def suggest_run_rotation(recent_run_types: list[str]) -> tuple[str | None, str]:
    """Anti-monotony nudge: when the recent run window is full and all one type,
    suggest the first preferred type not used recently. Otherwise (None, "")."""
    if len(recent_run_types) < RUN_MONOTONY_WINDOW:
        return None, ""
    recent_set = set(recent_run_types)
    if len(recent_set) != 1:
        return None, ""
    recent_type = recent_run_types[0]
    suggested = next((t for t in ROTATION_PREFERENCE if t not in recent_set), None)
    if suggested is None:
        return None, ""
    note = (f"Your last {len(recent_run_types)} runs were all "
            f"{recent_type.replace('_', ' ')} — try a "
            f"{suggested.replace('_', ' ')} run.")
    return suggested, note
```

- [ ] **Step 4: Run test to verify it passes**

Run: `.venv/bin/python -m pytest tests/test_coach/test_general_fitness_rules.py -k rotation -v`
Expected: PASS (4 passed)

- [ ] **Step 5: Commit**

```bash
git add services/coach/general_fitness.py tests/test_coach/test_general_fitness_rules.py
git commit -m "feat: add run-type rotation rule and RunRotation dataclass"
```

---

### Task 5: `consistent_week_streak` DB service

**Files:**
- Modify: `services/coach/general_fitness.py`
- Test: `tests/test_coach/test_general_fitness_services.py`

- [ ] **Step 1: Write the failing test**

```python
# tests/test_coach/test_general_fitness_services.py
import pytest
from datetime import date, timedelta
from django.contrib.auth.models import User
from apps.fitness.models import FitnessPlan, WorkoutDay, WorkoutLog
from services.coach.general_fitness import consistent_week_streak

TODAY = date.today()


def _user(username="g"):
    return User.objects.create_user(username=username, password="x", email=f"{username}@e.com")


def _week(user, week_number, weeks_ago, day_types, completed_count, is_active=False):
    """Create a one-week plan ending `weeks_ago` weeks before today, with the given
    non-rest day_types, marking the first `completed_count` of them completed."""
    end = TODAY - timedelta(weeks=weeks_ago)
    start = end - timedelta(days=6)
    plan = FitnessPlan.objects.create(
        user=user, week_number=week_number, start_date=start, end_date=end,
        is_active=is_active, total_workout_days=len(day_types),
        weekly_goal_summary="g", claude_reasoning="r",
    )
    days = []
    for i, dt in enumerate(day_types):
        d = start + timedelta(days=i)
        wd = WorkoutDay.objects.create(
            fitness_plan=plan, date=d, day_of_week=d.strftime("%A"),
            day_type=dt, focus_area="full_body", estimated_duration_minutes=40,
        )
        days.append(wd)
    for wd in days[:completed_count]:
        WorkoutLog.objects.create(user=user, workout_day=wd, date=wd.date, completed=True)
    return plan


@pytest.mark.django_db
def test_streak_counts_consecutive_consistent_weeks():
    user = _user()
    # most recent elapsed week first: 3 of 3 done, then 3 of 3 done
    _week(user, 2, weeks_ago=1, day_types=["strength", "running", "yoga"], completed_count=3)
    _week(user, 1, weeks_ago=2, day_types=["strength", "running", "yoga"], completed_count=3)
    assert consistent_week_streak(user, TODAY) == 2


@pytest.mark.django_db
def test_streak_stops_at_inconsistent_week():
    user = _user()
    _week(user, 3, weeks_ago=1, day_types=["strength", "running", "yoga"], completed_count=3)  # 100%
    _week(user, 2, weeks_ago=2, day_types=["strength", "running", "yoga"], completed_count=1)  # 33% breaks
    _week(user, 1, weeks_ago=3, day_types=["strength", "running", "yoga"], completed_count=3)  # 100% (not counted)
    assert consistent_week_streak(user, TODAY) == 1


@pytest.mark.django_db
def test_streak_excludes_in_progress_week_and_rest_days():
    user = _user()
    # current (not yet elapsed) week: ends in the future -> excluded
    _week(user, 2, weeks_ago=-1, day_types=["strength", "running", "yoga"], completed_count=0, is_active=True)
    # elapsed week with a rest day last: 2 non-rest planned (strength, yoga), both done
    # via completed_count=2 (which marks the first two days) -> consistent
    _week(user, 1, weeks_ago=1, day_types=["strength", "yoga", "rest"], completed_count=2)
    assert consistent_week_streak(user, TODAY) == 1


@pytest.mark.django_db
def test_streak_zero_for_new_user():
    assert consistent_week_streak(_user(), TODAY) == 0
```

- [ ] **Step 2: Run test to verify it fails**

Run: `.venv/bin/python -m pytest tests/test_coach/test_general_fitness_services.py -v`
Expected: FAIL — `ImportError: cannot import name 'consistent_week_streak'`

- [ ] **Step 3: Write minimal implementation** (append to `general_fitness.py`)

```python
def consistent_week_streak(user, on_date) -> int:
    """Count consecutive consistent weeks among the user's fully-elapsed week-plans,
    newest first. A week is consistent when >= CONSISTENCY_THRESHOLD of its non-rest
    workout days have a completed WorkoutLog. The in-progress week is excluded."""
    from apps.fitness.models import FitnessPlan, WorkoutLog

    plans = FitnessPlan.objects.filter(
        user=user, end_date__lt=on_date,
    ).order_by("-week_number")

    streak = 0
    for plan in plans:
        planned = plan.workout_days.exclude(day_type="rest").count()
        completed = (
            WorkoutLog.objects.filter(
                user=user, workout_day__fitness_plan=plan, completed=True,
            ).exclude(workout_day__day_type="rest").count()
        )
        if consistent_week(planned, completed):
            streak += 1
        else:
            break
    return streak
```

- [ ] **Step 4: Run test to verify it passes**

Run: `.venv/bin/python -m pytest tests/test_coach/test_general_fitness_services.py -v`
Expected: PASS (4 passed)

- [ ] **Step 5: Commit**

```bash
git add services/coach/general_fitness.py tests/test_coach/test_general_fitness_services.py
git commit -m "feat: add consistent_week_streak DB service"
```

---

### Task 6: `GeneralFitnessSuggestions` dataclass + `get_suggestions` DB service

**Files:**
- Modify: `services/coach/general_fitness.py`
- Test: `tests/test_coach/test_general_fitness_services.py`

- [ ] **Step 1: Write the failing test** (append, reusing `_user`/`_week`/`TODAY`)

```python
from decimal import Decimal
from apps.fitness.models import RunningStrategy
from services.coach.general_fitness import get_suggestions


def _run_week(user, week_number, weeks_ago, run_types, is_active=False):
    end = TODAY - timedelta(weeks=weeks_ago)
    start = end - timedelta(days=6)
    plan = FitnessPlan.objects.create(
        user=user, week_number=week_number, start_date=start, end_date=end,
        is_active=is_active, total_workout_days=len(run_types),
        weekly_goal_summary="g", claude_reasoning="r",
    )
    for i, rt in enumerate(run_types):
        d = start + timedelta(days=i)
        wd = WorkoutDay.objects.create(
            fitness_plan=plan, date=d, day_of_week=d.strftime("%A"),
            day_type="running", focus_area="cardio", estimated_duration_minutes=30,
        )
        RunningStrategy.objects.create(
            workout_day=wd, run_type=rt, total_distance_km=Decimal("5"),
            total_duration_minutes=30, pace_target="6:00/km",
        )
        WorkoutLog.objects.create(user=user, workout_day=wd, date=d, completed=True)
    return plan


@pytest.mark.django_db
def test_get_suggestions_bundles_streak_bump_and_addday():
    user = _user()
    # two consistent 3-day weeks of strength so current_days=3, streak=2
    _week(user, 2, weeks_ago=1, day_types=["strength", "strength", "yoga"], completed_count=3)
    _week(user, 1, weeks_ago=2, day_types=["strength", "strength", "yoga"], completed_count=3)
    # active (current) plan with 3 non-rest days, normal week number (not deload)
    _week(user, 3, weeks_ago=-1, day_types=["strength", "strength", "yoga"], completed_count=0, is_active=True)
    s = get_suggestions(user, TODAY)
    assert s.consistent_week_streak == 2
    assert s.duration_bump_min == 5 and s.duration_capped is False
    assert s.current_training_days == 3
    assert s.add_training_day is False        # streak 2 < 3
    assert s.run_rotation is None


@pytest.mark.django_db
def test_get_suggestions_suppresses_bump_on_deload_week():
    user = _user()
    _week(user, 2, weeks_ago=1, day_types=["strength", "strength", "yoga"], completed_count=3)
    _week(user, 1, weeks_ago=2, day_types=["strength", "strength", "yoga"], completed_count=3)
    # active plan is week 4 -> deload
    _week(user, 4, weeks_ago=-1, day_types=["strength", "strength", "yoga"], completed_count=0, is_active=True)
    s = get_suggestions(user, TODAY)
    assert s.consistent_week_streak == 2
    assert s.duration_bump_min == 0 and s.duration_capped is False


@pytest.mark.django_db
def test_get_suggestions_run_rotation_on_monotonous_history():
    user = _user("r")
    _run_week(user, 1, weeks_ago=1, run_types=["easy", "easy", "easy"])
    s = get_suggestions(user, TODAY)
    assert s.run_rotation is not None
    assert s.run_rotation.recent_type == "easy"
    assert s.run_rotation.suggested_type == "interval"


@pytest.mark.django_db
def test_get_suggestions_empty_for_new_user():
    s = get_suggestions(_user("n"), TODAY)
    assert s.consistent_week_streak == 0
    assert s.duration_bump_min == 0
    assert s.add_training_day is False
    assert s.current_training_days == 0
    assert s.run_rotation is None
```

- [ ] **Step 2: Run test to verify it fails**

Run: `.venv/bin/python -m pytest tests/test_coach/test_general_fitness_services.py -k get_suggestions -v`
Expected: FAIL — `ImportError: cannot import name 'get_suggestions'`

- [ ] **Step 3: Write minimal implementation**

Add the dataclass after `RunRotation`:

```python
@dataclass(frozen=True)
class GeneralFitnessSuggestions:
    consistent_week_streak: int
    duration_bump_min: int
    duration_capped: bool
    add_training_day: bool
    current_training_days: int
    run_rotation: RunRotation | None
```

Add the service (append):

```python
def get_suggestions(user, on_date) -> GeneralFitnessSuggestions:
    """Assemble the advisory general-fitness bundle for `user` as of `on_date`.
    Compute-on-read; reads only. The duration bump is suppressed on a deload week."""
    from apps.fitness.models import FitnessPlan, RunningStrategy
    from services.coach.engine import is_deload_week

    streak = consistent_week_streak(user, on_date)

    active_plan = FitnessPlan.objects.filter(user=user, is_active=True).first()
    is_deload = is_deload_week(active_plan.week_number) if active_plan else False
    current_days = (
        active_plan.workout_days.exclude(day_type="rest").count()
        if active_plan else 0
    )

    bump_min, capped = duration_bump(streak)
    if is_deload:
        bump_min, capped = 0, False

    add_day = should_add_training_day(streak, current_days)

    recent_types = list(
        RunningStrategy.objects.filter(
            workout_day__fitness_plan__user=user,
            workout_day__logs__user=user,
            workout_day__logs__completed=True,
        ).order_by("-workout_day__date").values_list("run_type", flat=True)[:RUN_MONOTONY_WINDOW]
    )
    suggested, note = suggest_run_rotation(recent_types)
    rotation = (
        RunRotation(recent_type=recent_types[0], suggested_type=suggested, note=note)
        if suggested else None
    )

    return GeneralFitnessSuggestions(
        consistent_week_streak=streak,
        duration_bump_min=bump_min,
        duration_capped=capped,
        add_training_day=add_day,
        current_training_days=current_days,
        run_rotation=rotation,
    )
```

- [ ] **Step 4: Run test to verify it passes**

Run: `.venv/bin/python -m pytest tests/test_coach/test_general_fitness_services.py -v`
Expected: PASS (8 passed)

- [ ] **Step 5: Commit**

```bash
git add services/coach/general_fitness.py tests/test_coach/test_general_fitness_services.py
git commit -m "feat: add get_suggestions bundle service with deload suppression"
```

---

### Task 7: Dashboard surfacing

**Files:**
- Modify: `apps/dashboard/views.py` (imports near line 8; `dashboard` context near line 70-92)
- Modify: `templates/dashboard/index.html` (after the weight/step card, ~line 124)
- Test: `tests/test_dashboard/test_general_fitness_surfacing.py`

- [ ] **Step 1: Write the failing test**

```python
# tests/test_dashboard/test_general_fitness_surfacing.py
import pytest
from datetime import date, timedelta
from django.urls import reverse
from django.contrib.auth.models import User
from apps.accounts.models import UserProfile
from apps.fitness.models import FitnessPlan, WorkoutDay, WorkoutLog

TODAY = date.today()


def _user(username="gf"):
    u = User.objects.create_user(username=username, password="testpass123", email=f"{username}@e.com")
    UserProfile.objects.create(
        user=u, height_cm=170, weight_kg=65, gender="female",
        date_of_birth=date(1992, 3, 3), fitness_experience="beginner",
        primary_goal="Get active", diet_type="omnivore", food_allergies=[],
        daily_routine="", wake_time="07:00", sleep_time="23:00",
        work_schedule="9-5", workout_days_per_week=3, preferred_workout_days=[],
        workout_location="home", available_equipment=[],
        notification_email=f"{username}@e.com", onboarding_completed=True,
    )
    return u


def _consistent_week(user, week_number, weeks_ago, is_active=False):
    end = TODAY - timedelta(weeks=weeks_ago)
    start = end - timedelta(days=6)
    plan = FitnessPlan.objects.create(
        user=user, week_number=week_number, start_date=start, end_date=end,
        is_active=is_active, total_workout_days=3,
        weekly_goal_summary="g", claude_reasoning="r",
    )
    for i, dt in enumerate(["strength", "strength", "yoga"]):
        d = start + timedelta(days=i)
        wd = WorkoutDay.objects.create(
            fitness_plan=plan, date=d, day_of_week=d.strftime("%A"),
            day_type=dt, focus_area="full_body", estimated_duration_minutes=40,
        )
        if not is_active:
            WorkoutLog.objects.create(user=user, workout_day=wd, date=d, completed=True)
    return plan


@pytest.mark.django_db
def test_dashboard_shows_add_day_nudge(client):
    user = _user()
    for wk, ago in [(1, 3), (2, 2), (3, 1)]:
        _consistent_week(user, wk, ago)
    _consistent_week(user, 5, weeks_ago=-1, is_active=True)   # 3 non-rest days, not deload
    client.login(username="gf", password="testpass123")
    resp = client.get(reverse("dashboard"))
    gf = resp.context["general_fitness"]
    assert gf.consistent_week_streak == 3
    assert gf.add_training_day is True
    assert "4th training day" in resp.content.decode()


@pytest.mark.django_db
def test_dashboard_clean_for_new_user(client):
    _user("clean")
    client.login(username="clean", password="testpass123")
    resp = client.get(reverse("dashboard"))
    gf = resp.context["general_fitness"]
    assert gf.add_training_day is False
    assert gf.duration_bump_min == 0
    assert gf.run_rotation is None
    assert "4th training day" not in resp.content.decode()
```

- [ ] **Step 2: Run test to verify it fails**

Run: `.venv/bin/python -m pytest tests/test_dashboard/test_general_fitness_surfacing.py -v`
Expected: FAIL — `KeyError: 'general_fitness'` (context key absent)

- [ ] **Step 3: Implement — view**

In `apps/dashboard/views.py`, extend the cardio import line (~line 8):

```python
from services.coach.cardio import body_weight_trend, suggest_step_target_for, suggest_weekly_mileage_for
from services.coach.general_fitness import get_suggestions
```

In `dashboard`, just before the `return render(...)` (after `step_target = ...`):

```python
    general_fitness = get_suggestions(request.user, today)
```

Add to the render context dict (after `"step_target": step_target,`):

```python
        "general_fitness": general_fitness,
```

- [ ] **Step 4: Implement — template**

In `templates/dashboard/index.html`, after the `{% endif %}` that closes the weight/step card (the block opened by `{% if weight_trend or step_target %}` near line 113), add:

```django
{% if general_fitness.add_training_day or general_fitness.duration_bump_min or general_fitness.run_rotation %}
<div class="card">
  <div class="card-title">Coach</div>
  {% if general_fitness.add_training_day %}
  <div class="card-sub">You've trained consistently {{ general_fitness.consistent_week_streak }} weeks — consider adding a 4th training day.</div>
  {% endif %}
  {% if general_fitness.duration_bump_min %}
  <div class="card-sub">Add ~{{ general_fitness.duration_bump_min }} min to your strength &amp; yoga sessions this week.</div>
  {% endif %}
  {% if general_fitness.run_rotation %}
  <div class="card-sub">{{ general_fitness.run_rotation.note }}</div>
  {% endif %}
</div>
{% endif %}
```

- [ ] **Step 5: Run test to verify it passes**

Run: `.venv/bin/python -m pytest tests/test_dashboard/test_general_fitness_surfacing.py -v`
Expected: PASS (2 passed)

- [ ] **Step 6: Commit**

```bash
git add apps/dashboard/views.py templates/dashboard/index.html tests/test_dashboard/test_general_fitness_surfacing.py
git commit -m "feat: surface general-fitness coach nudges on the dashboard"
```

---

### Task 8: Weekly-plan surfacing (duration hint + rotation note)

**Files:**
- Modify: `apps/dashboard/views.py` (`weekly_plan` view, context near line 138-147)
- Modify: `templates/dashboard/weekly_plan.html` (duration line ~70; running block ~102-105)
- Test: `tests/test_dashboard/test_general_fitness_surfacing.py`

- [ ] **Step 1: Write the failing test** (append; reuses `_user`, `_consistent_week`, `TODAY`)

```python
@pytest.mark.django_db
def test_weekly_plan_shows_duration_hint(client):
    user = _user("wp")
    # 4 consistent weeks -> bump 10 min; active non-deload plan with strength/yoga days
    for wk, ago in [(1, 4), (2, 3), (3, 2), (5, 1)]:
        _consistent_week(user, wk, ago)
    _consistent_week(user, 6, weeks_ago=-1, is_active=True)
    client.login(username="wp", password="testpass123")
    resp = client.get(reverse("weekly_plan"))
    gf = resp.context["general_fitness"]
    assert gf.duration_bump_min == 10
    assert "+10 min suggested" in resp.content.decode()
```

- [ ] **Step 2: Run test to verify it fails**

Run: `.venv/bin/python -m pytest tests/test_dashboard/test_general_fitness_surfacing.py -k weekly_plan -v`
Expected: FAIL — `KeyError: 'general_fitness'`

- [ ] **Step 3: Implement — view**

In `weekly_plan`, after `weekly_mileage_km = suggest_weekly_mileage_for(...)` (inside the `if fitness_plan:` block is fine, but compute unconditionally so new users still get an empty bundle). Just before `return render(...)`:

```python
    general_fitness = get_suggestions(request.user, today)
```

Add to the render context dict (after `"weekly_mileage_km": weekly_mileage_km,`):

```python
        "general_fitness": general_fitness,
        "duration_bump_types": DURATION_BUMP_DAY_TYPES,
```

Extend the general-fitness import to include the constant:

```python
from services.coach.general_fitness import get_suggestions, DURATION_BUMP_DAY_TYPES
```

- [ ] **Step 4: Implement — template**

In `templates/dashboard/weekly_plan.html`, the duration span (~line 70) currently reads:

```django
<span style="font-size:11px;color:#555;margin-left:8px;">{{ day.workout.focus_area|title }} · {{ day.workout.estimated_duration_minutes }} min</span>
```

Replace it with:

```django
<span style="font-size:11px;color:#555;margin-left:8px;">{{ day.workout.focus_area|title }} · {{ day.workout.estimated_duration_minutes }} min{% if general_fitness.duration_bump_min and day.workout.day_type in duration_bump_types %} <span style="color:#34d399;font-weight:700;">+{{ general_fitness.duration_bump_min }} min suggested</span>{% endif %}</span>
```

In the running-strategy block (the `{% with rs=day.workout.running_strategy %}` section, after the `<strong>Running: …</strong>` line ~105), add the rotation note:

```django
{% if general_fitness.run_rotation %}<div style="font-size:11px;color:#34d399;margin-top:2px;">{{ general_fitness.run_rotation.note }}</div>{% endif %}
```

- [ ] **Step 5: Run test to verify it passes**

Run: `.venv/bin/python -m pytest tests/test_dashboard/test_general_fitness_surfacing.py -k weekly_plan -v`
Expected: PASS (1 passed)

- [ ] **Step 6: Commit**

```bash
git add apps/dashboard/views.py templates/dashboard/weekly_plan.html tests/test_dashboard/test_general_fitness_surfacing.py
git commit -m "feat: surface duration hint and run rotation on the weekly plan"
```

---

### Task 9: Full-suite verification

**Files:** none (verification only)

- [ ] **Step 1: Run the entire test suite**

Run: `.venv/bin/python -m pytest -q`
Expected: all tests pass (prior 190 + the new general-fitness rules/services/surfacing tests), no failures.

- [ ] **Step 2: If green, the slice is complete**

The branch `feature/general-fitness-progression` is ready for a PR (follow the same flow as PRs #3–#5). If anything fails, fix before opening the PR.

---

## Notes for the implementer

- **Pattern to imitate:** `services/coach/cardio.py` — pure rules first, then I/O services with lazy `from apps...import` inside the function body. Keep `general_fitness.py` reads-only.
- **`in` operator in Django templates** is supported (`{% if day.workout.day_type in duration_bump_types %}`), which is why the view passes `DURATION_BUMP_DAY_TYPES` to the template.
- **The in-progress week** is excluded from the streak via `end_date__lt=on_date`; tests use negative `weeks_ago` to create a future-ending active plan.
- **Deload weeks** are `week_number % 4 == 0` (`is_deload_week`); the suite uses week 4 as the active plan to assert bump suppression.
