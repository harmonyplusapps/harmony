# Daily Decision Engine Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a rule-based daily decision engine that overlays a `DailyDecision` on today's planned workout (read from `get_health_snapshot`), and surface it on the dashboard.

**Architecture:** Pure logic split from I/O like slice #2. `services/coach/engine.py` holds a pure `decide(snapshot, workout_day) -> DailyDecision` plus a thin `decide_today(user, date)` that fetches the snapshot and today's `WorkoutDay`. The weekly plan is never mutated; the decision is an advisory read-time overlay. No new DB model, no Claude call.

**Tech Stack:** Python 3.13, Django 5.1, pytest + pytest-django, HTMX dark-UI templates. Run Python via `.venv/bin/python`.

**Spec:** `docs/superpowers/specs/2026-06-18-daily-decision-engine-design.md`

**Conventions (verified):**
- Tests in `tests/test_<app>/test_*.py`, use `@pytest.mark.django_db` where DB is needed, `reverse()`, the `client` fixture. Run: `.venv/bin/python -m pytest`.
- `HealthSnapshot`, `Momentum`, `SorenessItem` are plain dataclasses — constructable in tests without the DB. Pure-engine tests use `types.SimpleNamespace` stand-ins for `workout_day` and `recent_workouts` entries (the engine only reads `.day_type` / `.focus_area` / `.date` / `.perceived_exertion` / `.workout_day.day_type`).
- Scales: `energy`/`stress`/`mood` are 1–10; `sleep_quality` is 1–5; `sleep_hours` is a `Decimal`.

---

### Task 1: Add `focus_area` to `SorenessItem` (slice-#2 follow-up)

**Files:**
- Modify: `services/health/snapshot.py`
- Test: `tests/test_health/test_snapshot.py`

- [ ] **Step 1: Update the failing tests**

In `tests/test_health/test_snapshot.py`, replace the two positional `SorenessItem` assertions (currently around lines 72–73):

```python
    assert SorenessItem("quads", "severe") in snap.soreness
    assert SorenessItem("core", "mild") in snap.soreness
```

with field-based assertions plus a focus-area check:

```python
    by_group = {s.muscle_group: s for s in snap.soreness}
    assert by_group["quads"].severity == "severe"
    assert by_group["quads"].focus_area == "lower_body"
    assert by_group["core"].severity == "mild"
    assert by_group["core"].focus_area == "core"
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `.venv/bin/python -m pytest tests/test_health/test_snapshot.py -v`
Expected: FAIL — `SorenessItem` has no `focus_area`.

- [ ] **Step 3: Add the field and populate it**

In `services/health/snapshot.py`, add the import for the mapping (extend the existing `apps.health.models` import line):

```python
from apps.health.models import WellnessLog, SorenessLog, PeriodLog, MUSCLE_GROUP_TO_FOCUS
```

Change the `SorenessItem` dataclass to:

```python
@dataclass(frozen=True)
class SorenessItem:
    muscle_group: str
    severity: str
    focus_area: str
```

Change the soreness comprehension in `get_health_snapshot` to populate `focus_area`:

```python
    soreness = [
        SorenessItem(s.muscle_group, s.severity, MUSCLE_GROUP_TO_FOCUS[s.muscle_group])
        for s in SorenessLog.objects.filter(user=user, date=on_date)
    ]
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `.venv/bin/python -m pytest tests/test_health/test_snapshot.py -v`
Expected: PASS (all snapshot tests).

- [ ] **Step 5: Commit**

```bash
git add services/health/snapshot.py tests/test_health/test_snapshot.py
git commit -m "feat: add focus_area to SorenessItem for the decision engine"
```

---

### Task 2: Engine scaffolding — `DailyDecision`, constants, hard stops

**Files:**
- Create: `services/coach/__init__.py`
- Create: `services/coach/engine.py`
- Create: `tests/test_coach/__init__.py`
- Test: `tests/test_coach/test_engine_hardstops.py`

- [ ] **Step 1: Create the test package init**

Create `tests/test_coach/__init__.py` (empty file).

- [ ] **Step 2: Write failing hard-stop tests**

Create `tests/test_coach/test_engine_hardstops.py`:

```python
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
    # hard yesterday but good sleep -> no recovery hard stop
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
    assert d.avoid_focus_areas == ()  # mild not counted


def test_soreness_in_other_focus_area_no_daytype_override():
    sore = [SorenessItem("core", "severe", "core")]
    d = decide(_snap(soreness=sore), _workout(focus_area="lower_body"))
    assert d.recommended_day_type == "strength"
    assert "core" in d.avoid_focus_areas
    assert d.is_override is False


def test_returns_dailydecision_instance():
    assert isinstance(decide(_snap(), _workout()), DailyDecision)
```

- [ ] **Step 3: Run tests to verify they fail**

Run: `.venv/bin/python -m pytest tests/test_coach/test_engine_hardstops.py -v`
Expected: FAIL — `services.coach.engine` does not exist.

- [ ] **Step 4: Create the package init**

Create `services/coach/__init__.py` (empty file).

- [ ] **Step 5: Implement the engine scaffolding + hard stops**

Create `services/coach/engine.py`:

```python
from dataclasses import dataclass
from datetime import timedelta

# --- Tunable constants -------------------------------------------------------
RECOVERY_INTENSITY = 0.4
MIN_INTENSITY = 0.4
MAX_INTENSITY = 1.1
HARD_RPE = 8              # perceived_exertion (1-10) considered a hard session
POOR_SLEEP_QUALITY = 2   # sleep_quality is 1-5
POOR_SLEEP_HOURS = 6     # sleep_hours
LOW_ENERGY = 3           # energy is 1-10
PUSH_STREAK = 3          # consecutive days to start nudging harder
OVERTRAIN_STREAK = 5     # consecutive days to flag overtraining watch

ACTIVE_RECOVERY_SUGGESTION = "20–30 min easy walk plus full-body mobility and light stretching."


@dataclass(frozen=True)
class DailyDecision:
    planned_day_type: str | None
    recommended_day_type: str
    intensity_modifier: float
    avoid_focus_areas: tuple[str, ...]
    rationale: str
    flags: tuple[str, ...]
    is_override: bool


def _sore_focus_areas(snapshot) -> tuple[str, ...]:
    return tuple(sorted({
        s.focus_area for s in snapshot.soreness
        if s.severity in ("moderate", "severe")
    }))


def _first_sore_group_for_focus(snapshot, focus_area) -> str:
    for s in snapshot.soreness:
        if s.severity in ("moderate", "severe") and s.focus_area == focus_area:
            return s.muscle_group
    return "those muscles"


def _hard_yesterday(snapshot) -> bool:
    yesterday = snapshot.date - timedelta(days=1)
    for wl in snapshot.recent_workouts:
        if wl.date == yesterday:
            if wl.perceived_exertion is not None:
                return wl.perceived_exertion >= HARD_RPE
            return wl.workout_day.day_type in ("strength", "running")
    return False


def _poor_sleep(snapshot) -> bool:
    if snapshot.sleep_quality is not None and snapshot.sleep_quality <= POOR_SLEEP_QUALITY:
        return True
    if snapshot.sleep_hours is not None and snapshot.sleep_hours < POOR_SLEEP_HOURS:
        return True
    return False


def decide(snapshot, workout_day) -> DailyDecision:
    planned = workout_day.day_type if workout_day else None
    avoid = _sore_focus_areas(snapshot)

    # Hard stop 1: planned rest / no workout today.
    if workout_day is None or planned == "rest":
        return DailyDecision(
            planned_day_type=planned, recommended_day_type=planned or "rest",
            intensity_modifier=1.0, avoid_focus_areas=avoid,
            rationale="Rest day — recover well.", flags=(), is_override=False,
        )

    # Hard stop 2: hard session yesterday + poor sleep -> active recovery.
    if _hard_yesterday(snapshot) and _poor_sleep(snapshot):
        return DailyDecision(
            planned_day_type=planned, recommended_day_type="active_recovery",
            intensity_modifier=RECOVERY_INTENSITY, avoid_focus_areas=avoid,
            rationale="Hard session yesterday plus short sleep — active recovery today.",
            flags=(), is_override=True,
        )

    # Hard stop 3: today's focus area is sore -> active recovery.
    if workout_day.focus_area in avoid:
        group = _first_sore_group_for_focus(snapshot, workout_day.focus_area)
        return DailyDecision(
            planned_day_type=planned, recommended_day_type="active_recovery",
            intensity_modifier=RECOVERY_INTENSITY, avoid_focus_areas=avoid,
            rationale=f"{group.title()} still sore — keeping today to active recovery.",
            flags=(), is_override=True,
        )

    # Intensity path (fully implemented in Task 3). Placeholder: on plan.
    return DailyDecision(
        planned_day_type=planned, recommended_day_type=planned,
        intensity_modifier=1.0, avoid_focus_areas=avoid,
        rationale="On plan — go for it.", flags=(), is_override=False,
    )
```

- [ ] **Step 6: Run tests to verify they pass**

Run: `.venv/bin/python -m pytest tests/test_coach/test_engine_hardstops.py -v`
Expected: PASS (9 tests).

- [ ] **Step 7: Commit**

```bash
git add services/coach tests/test_coach
git commit -m "feat: add decision engine scaffolding and hard stops"
```

---

### Task 3: Intensity modifiers + rationale selection

**Files:**
- Modify: `services/coach/engine.py`
- Test: `tests/test_coach/test_engine_intensity.py`

- [ ] **Step 1: Write failing intensity tests**

Create `tests/test_coach/test_engine_intensity.py`:

```python
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
    d = decide(_snap(momentum=_mom(bucket="current", streak=6)), _workout())
    assert "overtraining_watch" in d.flags


def test_compounding_clamps_to_min():
    # low energy (0.7) * full_reset (0.5) = 0.35 -> clamped to 0.4
    d = decide(_snap(energy=1, momentum=_mom(bucket="full_reset", streak=0)), _workout())
    assert d.intensity_modifier == 0.4


def test_compounding_clamps_to_max():
    # follicular (1.1) * push streak (1.05) = 1.155 -> clamped to 1.1
    d = decide(_snap(cycle_phase="follicular", momentum=_mom(bucket="current", streak=5)), _workout())
    assert d.intensity_modifier == 1.1


def test_rationale_picks_largest_deviation_rule():
    # low energy (dev 0.3) vs full_reset (dev 0.5) -> full_reset rationale wins
    d = decide(_snap(energy=2, momentum=_mom(bucket="full_reset", streak=0)), _workout())
    assert "restart" in d.rationale.lower() or "light" in d.rationale.lower()
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `.venv/bin/python -m pytest tests/test_coach/test_engine_intensity.py -v`
Expected: FAIL — placeholder returns 1.0 for everything.

- [ ] **Step 3: Implement the intensity path**

In `services/coach/engine.py`, add these constants after the existing constants block (before `ACTIVE_RECOVERY_SUGGESTION` is fine, anywhere at module level):

```python
LOW_ENERGY_MULTIPLIER = 0.7
PUSH_MULTIPLIER = 1.05
MOMENTUM_MULTIPLIER = {
    "current": 1.0, "no_history": 1.0,
    "missed_2_3": 0.85, "missed_4_7": 0.6, "missed_long": 0.6, "full_reset": 0.5,
}
CYCLE_MULTIPLIER = {
    "luteal": 0.85, "period": 0.85, "follicular": 1.1, "ovulation": 1.1,
}
```

Add these rationale helpers at module level:

```python
def _momentum_rationale(bucket) -> str:
    return {
        "missed_2_3": "A couple days off — easing back in.",
        "missed_4_7": "Been a few days — keeping it moderate.",
        "missed_long": "Welcome back — easing in after the break.",
        "full_reset": "Fresh restart — keeping today light.",
    }.get(bucket, "")


def _cycle_rationale(phase) -> str:
    return {
        "luteal": "Luteal phase — favoring a steadier effort.",
        "period": "On your period — keeping the effort gentle.",
        "follicular": "Follicular phase — good day to push.",
        "ovulation": "Peak-energy window — great day to push.",
    }.get(phase, "")
```

Replace the placeholder intensity-path return at the end of `decide` with:

```python
    # Intensity path: compounding modifiers, single best rationale.
    modifier = 1.0
    candidates = []  # (multiplier, rationale)
    flags = []

    if snapshot.energy is not None and snapshot.energy <= LOW_ENERGY:
        modifier *= LOW_ENERGY_MULTIPLIER
        candidates.append((LOW_ENERGY_MULTIPLIER, "Energy's low today — lighter session."))

    mom_mult = MOMENTUM_MULTIPLIER.get(snapshot.momentum.bucket, 1.0)
    if mom_mult != 1.0:
        modifier *= mom_mult
        candidates.append((mom_mult, _momentum_rationale(snapshot.momentum.bucket)))

    cycle_mult = CYCLE_MULTIPLIER.get(snapshot.cycle_phase, 1.0)
    if cycle_mult != 1.0:
        modifier *= cycle_mult
        candidates.append((cycle_mult, _cycle_rationale(snapshot.cycle_phase)))

    streak = snapshot.momentum.current_streak
    if streak >= PUSH_STREAK:
        modifier *= PUSH_MULTIPLIER
        flags.append("push")
        candidates.append((PUSH_MULTIPLIER, f"{streak}-day streak — pushing a little."))
    if streak >= OVERTRAIN_STREAK:
        flags.append("overtraining_watch")

    modifier = round(max(MIN_INTENSITY, min(MAX_INTENSITY, modifier)), 3)

    if candidates:
        rationale = max(candidates, key=lambda c: abs(c[0] - 1.0))[1]
    else:
        rationale = "On plan — go for it."

    return DailyDecision(
        planned_day_type=planned, recommended_day_type=planned,
        intensity_modifier=modifier, avoid_focus_areas=avoid,
        rationale=rationale, flags=tuple(flags),
        is_override=abs(modifier - 1.0) > 1e-9,
    )
```

Note: `CYCLE_MULTIPLIER.get(snapshot.cycle_phase, 1.0)` returns 1.0 for `None` because `None` is not a key.

- [ ] **Step 4: Run tests to verify they pass**

Run: `.venv/bin/python -m pytest tests/test_coach/test_engine_intensity.py -v`
Expected: PASS (11 tests).

- [ ] **Step 5: Run both engine test files**

Run: `.venv/bin/python -m pytest tests/test_coach/ -v`
Expected: PASS (20 tests).

- [ ] **Step 6: Commit**

```bash
git add services/coach/engine.py tests/test_coach/test_engine_intensity.py
git commit -m "feat: add intensity modifiers and rationale selection to the engine"
```

---

### Task 4: `decide_today` entry point + integration test

**Files:**
- Modify: `services/coach/engine.py`
- Test: `tests/test_coach/test_decide_today.py`

- [ ] **Step 1: Write failing integration test**

Create `tests/test_coach/test_decide_today.py`:

```python
import pytest
from datetime import date
from django.contrib.auth.models import User
from apps.accounts.models import UserProfile
from apps.fitness.models import FitnessPlan, WorkoutDay
from apps.health.models import SorenessLog
from services.coach.engine import decide_today


def _user():
    u = User.objects.create_user(username="dt", password="x", email="dt@e.com")
    UserProfile.objects.create(
        user=u, height_cm=170, weight_kg=65, gender="female",
        date_of_birth=date(1992, 3, 3), fitness_experience="beginner",
        primary_goal="Get active", diet_type="omnivore", food_allergies=[],
        daily_routine="", wake_time="07:00", sleep_time="23:00",
        work_schedule="9-5", workout_days_per_week=3, preferred_workout_days=[],
        workout_location="home", available_equipment=[],
        notification_email="dt@e.com",
    )
    return u


def _plan_with_today(user, focus_area):
    today = date.today()
    plan = FitnessPlan.objects.create(
        user=user, week_number=1, start_date=today, end_date=today,
        total_workout_days=1, weekly_goal_summary="g", claude_reasoning="r",
    )
    WorkoutDay.objects.create(
        fitness_plan=plan, date=today, day_of_week=today.strftime("%A"),
        day_type="strength", focus_area=focus_area, estimated_duration_minutes=45,
    )
    return plan


@pytest.mark.django_db
def test_decide_today_no_plan_is_rest():
    user = _user()
    d = decide_today(user, date.today())
    assert d.recommended_day_type == "rest"
    assert d.is_override is False


@pytest.mark.django_db
def test_decide_today_soreness_conflict_overrides_to_active_recovery():
    user = _user()
    _plan_with_today(user, focus_area="lower_body")
    SorenessLog.objects.create(user=user, date=date.today(), muscle_group="quads", severity="severe")
    d = decide_today(user, date.today())
    assert d.recommended_day_type == "active_recovery"
    assert d.is_override is True
    assert "lower_body" in d.avoid_focus_areas


@pytest.mark.django_db
def test_decide_today_clean_day_is_on_plan():
    user = _user()
    _plan_with_today(user, focus_area="upper_body")
    d = decide_today(user, date.today())
    assert d.recommended_day_type == "strength"
    assert d.is_override is False
```

- [ ] **Step 2: Run test to verify it fails**

Run: `.venv/bin/python -m pytest tests/test_coach/test_decide_today.py -v`
Expected: FAIL — `decide_today` not defined.

- [ ] **Step 3: Implement `decide_today`**

In `services/coach/engine.py`, add the import at the top (below the stdlib imports):

```python
from services.health.snapshot import get_health_snapshot
```

Add this function at the end of the file:

```python
def decide_today(user, on_date) -> DailyDecision:
    """Fetch today's snapshot + planned workout and return the daily decision."""
    from apps.fitness.models import FitnessPlan, WorkoutDay
    snapshot = get_health_snapshot(user, on_date)
    plan = FitnessPlan.objects.filter(user=user, is_active=True).first()
    workout_day = None
    if plan is not None:
        workout_day = WorkoutDay.objects.filter(
            fitness_plan=plan, day_of_week=on_date.strftime("%A")
        ).first()
    return decide(snapshot, workout_day)
```

(The `FitnessPlan`/`WorkoutDay` import is function-local to avoid any app-loading import cycles at module import time.)

- [ ] **Step 4: Run test to verify it passes**

Run: `.venv/bin/python -m pytest tests/test_coach/test_decide_today.py -v`
Expected: PASS (3 tests).

- [ ] **Step 5: Commit**

```bash
git add services/coach/engine.py tests/test_coach/test_decide_today.py
git commit -m "feat: add decide_today entry point for the decision engine"
```

---

### Task 5: Dashboard integration (view + template + CSS)

**Files:**
- Modify: `apps/dashboard/views.py`
- Modify: `templates/dashboard/index.html`
- Modify: `static/css/app.css`
- Test: `tests/test_dashboard/test_decision.py`

- [ ] **Step 1: Write failing dashboard tests**

Create `tests/test_dashboard/test_decision.py`:

```python
import pytest
from datetime import date
from django.urls import reverse
from django.contrib.auth.models import User
from apps.accounts.models import UserProfile
from apps.fitness.models import FitnessPlan, WorkoutDay
from apps.health.models import SorenessLog


def _user():
    u = User.objects.create_user(username="dv", password="testpass123", email="dv@e.com")
    UserProfile.objects.create(
        user=u, height_cm=170, weight_kg=65, gender="female",
        date_of_birth=date(1992, 3, 3), fitness_experience="beginner",
        primary_goal="Get active", diet_type="omnivore", food_allergies=[],
        daily_routine="", wake_time="07:00", sleep_time="23:00",
        work_schedule="9-5", workout_days_per_week=3, preferred_workout_days=[],
        workout_location="home", available_equipment=[],
        notification_email="dv@e.com", onboarding_completed=True,
    )
    return u


def _plan_today(user, focus_area="upper_body"):
    today = date.today()
    plan = FitnessPlan.objects.create(
        user=user, week_number=1, start_date=today, end_date=today,
        total_workout_days=1, weekly_goal_summary="g", claude_reasoning="r",
    )
    WorkoutDay.objects.create(
        fitness_plan=plan, date=today, day_of_week=today.strftime("%A"),
        day_type="strength", focus_area=focus_area, estimated_duration_minutes=45,
    )
    return plan


@pytest.mark.django_db
def test_dashboard_has_decision_in_context(client):
    _user()
    _plan_today(User.objects.get(username="dv"))
    client.login(username="dv", password="testpass123")
    resp = client.get(reverse("dashboard"))
    assert "decision" in resp.context
    assert resp.context["decision"].recommended_day_type == "strength"


@pytest.mark.django_db
def test_dashboard_shows_active_recovery_card_on_soreness_override(client):
    user = _user()
    _plan_today(user, focus_area="lower_body")
    SorenessLog.objects.create(user=user, date=date.today(), muscle_group="quads", severity="severe")
    client.login(username="dv", password="testpass123")
    resp = client.get(reverse("dashboard"))
    body = resp.content.decode()
    assert "Active Recovery" in body
    assert "still sore" in body  # rationale banner


@pytest.mark.django_db
def test_dashboard_clean_day_no_banner(client):
    user = _user()
    _plan_today(user, focus_area="upper_body")
    client.login(username="dv", password="testpass123")
    resp = client.get(reverse("dashboard"))
    assert "coach-banner" not in resp.content.decode()
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `.venv/bin/python -m pytest tests/test_dashboard/test_decision.py -v`
Expected: FAIL — `decision` not in context.

- [ ] **Step 3: Wire the decision into the view**

In `apps/dashboard/views.py`, add the import near the other service/model imports at the top:

```python
from services.coach.engine import decide_today, ACTIVE_RECOVERY_SUGGESTION
```

In the `dashboard` view, after `today_workout` / `workout_log` are resolved and before the `today_meals` block, add:

```python
    decision = decide_today(request.user, today)
    intensity_pct = round(decision.intensity_modifier * 100)
```

Add these three keys to the `render(...)` context dict (alongside `today_workout`):

```python
        "decision": decision,
        "intensity_pct": intensity_pct,
        "active_recovery_suggestion": ACTIVE_RECOVERY_SUGGESTION,
```

- [ ] **Step 4: Render the decision in the template**

In `templates/dashboard/index.html`, replace the workout card block (the `<div class="card">` containing the `🏋️` icon, currently lines 56–71) with this conditional block:

```html
  {% if decision.is_override %}
  <div class="coach-banner">🧭 Today's call: {{ decision.rationale }}</div>
  {% endif %}
  {% if decision.recommended_day_type == "active_recovery" and decision.planned_day_type != "active_recovery" %}
  <div class="card active-recovery-card">
    <div class="content-card">
      <div class="card-icon" style="background:rgba(34,197,94,0.15)">🧘</div>
      <div>
        <div class="card-title">Active Recovery</div>
        <div class="card-sub">{{ active_recovery_suggestion }}</div>
      </div>
    </div>
  </div>
  {% else %}
  <div class="card">
    <div class="content-card">
      <div class="card-icon" style="background:rgba(108,99,255,0.15)">🏋️</div>
      <div>
        <div class="card-title">{% if today_workout %}{{ today_workout.day_type|title }} · {{ today_workout.focus_area|title }}{% else %}Rest Day{% endif %}</div>
        <div class="card-sub">{% if today_workout %}{{ today_workout.estimated_duration_minutes }} min{% if decision.is_override and intensity_pct != 100 %} · aim ~{{ intensity_pct }}% load{% endif %}{% else %}Recovery &amp; mobility{% endif %}</div>
      </div>
      {% if today_workout %}
        {% if workout_log.completed %}
          <span class="card-badge" style="background:rgba(34,197,94,0.15);color:#4ade80">Done ✓</span>
        {% else %}
          <span class="card-badge" style="background:rgba(108,99,255,0.15);color:#a78bfa">Pending</span>
        {% endif %}
      {% endif %}
    </div>
  </div>
  {% endif %}
```

(The surrounding `{% if not fitness_plan %} … {% else %}<div class="cards-list"> … </div>{% endif %}` and the meals card stay exactly as they are; only the single workout card is replaced.)

- [ ] **Step 5: Add CSS for the banner and recovery card**

In `static/css/app.css`, append (these reuse the dark-theme variables already used by the `.checkin-*` rules; if a variable name differs in this file, match the value used nearby):

```css
.coach-banner {
  margin: 0 0 12px;
  padding: 10px 14px;
  border-radius: 12px;
  background: rgba(108, 99, 255, 0.12);
  border: 1px solid rgba(108, 99, 255, 0.35);
  color: var(--text);
  font-size: 13px;
  font-weight: 700;
}

.active-recovery-card {
  border: 1px solid rgba(34, 197, 94, 0.35);
}
```

- [ ] **Step 6: Run tests to verify they pass**

Run: `.venv/bin/python -m pytest tests/test_dashboard/test_decision.py -v`
Expected: PASS (3 tests).

- [ ] **Step 7: Run the dashboard + coach suites and Django check**

Run: `.venv/bin/python -m pytest tests/test_dashboard/ tests/test_coach/ -q`
Expected: PASS.
Run: `.venv/bin/python manage.py check`
Expected: 0 issues.

- [ ] **Step 8: Commit**

```bash
git add apps/dashboard/views.py templates/dashboard/index.html static/css/app.css tests/test_dashboard/test_decision.py
git commit -m "feat: surface the daily decision on the dashboard"
```

---

## Notes for the implementer

- Run Python through `.venv/bin/python` (uses the project venv + `DJANGO_SETTINGS_MODULE` from `pytest.ini`).
- Branch: `feature/daily-decision-engine`. Spec committed alongside this plan.
- The engine performs **no writes** and makes **no Claude call**. The weekly `WorkoutDay` is never mutated.
- Out of scope (do not build): deload/overload (slice #4), Step-10 special situations, exercise regeneration, decision persistence.
