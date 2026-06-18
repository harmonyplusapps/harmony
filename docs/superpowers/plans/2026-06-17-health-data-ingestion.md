# Health Data Ingestion Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a manual daily health check-in (soreness, steps, resting HR, menstrual cycle) and a snapshot service that assembles all health signals for the future decision engine.

**Architecture:** Extend `WellnessLog` with daily scalars and `UserProfile` with cycle config; add normalized `SorenessLog` and event-based `PeriodLog` models. Pure functions compute cycle phase and momentum; `get_health_snapshot(user, date)` returns a typed `HealthSnapshot` dataclass the decision engine will read so it never touches raw models. A HTMX check-in page writes the data.

**Tech Stack:** Django 5.1, pytest + pytest-django, HTMX, dark-UI templates. Python via `.venv/bin/python`.

**Spec:** `docs/superpowers/specs/2026-06-17-health-data-ingestion-design.md`

**Conventions (verified in codebase):**
- Tests live in `tests/test_<app>/test_*.py`, use `@pytest.mark.django_db`, `reverse()`, and the `client` fixture. Run with `.venv/bin/python -m pytest`.
- Views use `@login_required`; HTMX POST handlers return small HTML fragments.
- Authenticated pages extend `templates/base_app.html` and live under `templates/<app>/`.

---

### Task 1: Data models — schema for new health signals

**Files:**
- Modify: `apps/health/models.py`
- Modify: `apps/accounts/models.py`
- Create: `tests/test_health/__init__.py`
- Test: `tests/test_health/test_models.py`
- Generated: migrations under `apps/health/migrations/` and `apps/accounts/migrations/`

- [ ] **Step 1: Create the test package init**

Create `tests/test_health/__init__.py` (empty file).

- [ ] **Step 2: Write failing model tests**

Create `tests/test_health/test_models.py`:

```python
import pytest
from datetime import date
from django.db import IntegrityError
from django.contrib.auth.models import User
from apps.health.models import SorenessLog, PeriodLog, WellnessLog, MUSCLE_GROUP_TO_FOCUS
from apps.accounts.models import UserProfile


@pytest.fixture
def user(db):
    return User.objects.create_user(username="h", password="x", email="h@e.com")


@pytest.mark.django_db
def test_wellnesslog_has_optional_steps_and_resting_hr(user):
    log = WellnessLog.objects.create(
        user=user, date=date(2026, 6, 17),
        sleep_hours=7, sleep_quality=4, mood_score=6,
        stress_level=4, energy_level=7,
    )
    assert log.steps is None
    assert log.resting_hr_bpm is None
    log.steps = 8200
    log.resting_hr_bpm = 58
    log.save()
    log.refresh_from_db()
    assert log.steps == 8200
    assert log.resting_hr_bpm == 58


@pytest.mark.django_db
def test_sorenesslog_unique_per_user_date_group(user):
    SorenessLog.objects.create(
        user=user, date=date(2026, 6, 17), muscle_group="quads", severity="severe",
    )
    with pytest.raises(IntegrityError):
        SorenessLog.objects.create(
            user=user, date=date(2026, 6, 17), muscle_group="quads", severity="mild",
        )


@pytest.mark.django_db
def test_periodlog_unique_per_user_start_date(user):
    PeriodLog.objects.create(user=user, start_date=date(2026, 6, 1))
    with pytest.raises(IntegrityError):
        PeriodLog.objects.create(user=user, start_date=date(2026, 6, 1))


@pytest.mark.django_db
def test_muscle_group_to_focus_mapping_covers_all_choices():
    groups = {c[0] for c in SorenessLog.MUSCLE_GROUP_CHOICES}
    assert groups == set(MUSCLE_GROUP_TO_FOCUS.keys())
    assert MUSCLE_GROUP_TO_FOCUS["chest"] == "upper_body"
    assert MUSCLE_GROUP_TO_FOCUS["quads"] == "lower_body"
    assert MUSCLE_GROUP_TO_FOCUS["core"] == "core"


@pytest.mark.django_db
def test_userprofile_cycle_defaults(user):
    profile = UserProfile.objects.create(
        user=user, height_cm=170, weight_kg=65, gender="female",
        date_of_birth=date(1992, 3, 3), fitness_experience="beginner",
        primary_goal="Get active", diet_type="omnivore", food_allergies=[],
        daily_routine="", wake_time="07:00", sleep_time="23:00",
        work_schedule="9-5", workout_days_per_week=3, preferred_workout_days=[],
        workout_location="home", available_equipment=[],
        notification_email="h@e.com",
    )
    assert profile.tracks_cycle is False
    assert profile.average_cycle_length == 28
```

- [ ] **Step 3: Run tests to verify they fail**

Run: `.venv/bin/python -m pytest tests/test_health/test_models.py -v`
Expected: FAIL — `ImportError` for `SorenessLog`/`PeriodLog`/`MUSCLE_GROUP_TO_FOCUS`.

- [ ] **Step 4: Add cycle fields to UserProfile**

In `apps/accounts/models.py`, inside `UserProfile`, add after `onboarding_completed`:

```python
    tracks_cycle = models.BooleanField(default=False)
    average_cycle_length = models.IntegerField(default=28)
```

- [ ] **Step 5: Add new health models and fields**

In `apps/health/models.py`, add `steps` and `resting_hr_bpm` to `WellnessLog` (after `mindfulness_type`):

```python
    steps = models.IntegerField(null=True, blank=True)
    resting_hr_bpm = models.IntegerField(null=True, blank=True)
```

Then append to the end of `apps/health/models.py`:

```python
class SorenessLog(models.Model):
    MUSCLE_GROUP_CHOICES = [
        ("chest", "Chest"), ("back", "Back"), ("shoulders", "Shoulders"),
        ("arms", "Arms"), ("core", "Core"), ("glutes", "Glutes"),
        ("quads", "Quads"), ("hamstrings", "Hamstrings"), ("calves", "Calves"),
    ]
    SEVERITY_CHOICES = [("mild", "Mild"), ("moderate", "Moderate"), ("severe", "Severe")]

    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="soreness_logs")
    date = models.DateField()
    muscle_group = models.CharField(max_length=20, choices=MUSCLE_GROUP_CHOICES)
    severity = models.CharField(max_length=10, choices=SEVERITY_CHOICES)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ["user", "date", "muscle_group"]
        ordering = ["date", "muscle_group"]


class PeriodLog(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="period_logs")
    start_date = models.DateField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ["user", "start_date"]
        ordering = ["-start_date"]


# Maps each soreness muscle group to the WorkoutDay.focus_area it belongs to,
# so the decision engine can match logged soreness against a planned focus.
MUSCLE_GROUP_TO_FOCUS = {
    "chest": "upper_body",
    "back": "upper_body",
    "shoulders": "upper_body",
    "arms": "upper_body",
    "core": "core",
    "glutes": "lower_body",
    "quads": "lower_body",
    "hamstrings": "lower_body",
    "calves": "lower_body",
}
```

- [ ] **Step 6: Generate migrations**

Run: `.venv/bin/python manage.py makemigrations health accounts`
Expected: new migration files created for both apps (add fields + two new models).

- [ ] **Step 7: Run tests to verify they pass**

Run: `.venv/bin/python -m pytest tests/test_health/test_models.py -v`
Expected: PASS (5 tests).

- [ ] **Step 8: Commit**

```bash
git add apps/health/models.py apps/accounts/models.py apps/health/migrations apps/accounts/migrations tests/test_health
git commit -m "feat: add soreness, period, and daily-scalar health models"
```

---

### Task 2: Pure calculation functions — cycle phase & momentum

**Files:**
- Create: `services/health/__init__.py`
- Create: `services/health/calculations.py`
- Test: `tests/test_health/test_calculations.py`

- [ ] **Step 1: Write failing calculation tests**

Create `tests/test_health/test_calculations.py`:

```python
from datetime import date, timedelta
from services.health.calculations import compute_cycle_phase, compute_momentum, Momentum


def test_cycle_phase_none_when_no_period():
    assert compute_cycle_phase(None, 28, date(2026, 6, 17)) is None


def test_cycle_phase_none_when_date_before_start():
    assert compute_cycle_phase(date(2026, 6, 10), 28, date(2026, 6, 5)) is None


def test_cycle_phase_period_days_1_to_5():
    start = date(2026, 6, 1)
    assert compute_cycle_phase(start, 28, start) == "period"            # day 1
    assert compute_cycle_phase(start, 28, start + timedelta(4)) == "period"  # day 5


def test_cycle_phase_follicular_days_6_to_13():
    start = date(2026, 6, 1)
    assert compute_cycle_phase(start, 28, start + timedelta(5)) == "follicular"   # day 6
    assert compute_cycle_phase(start, 28, start + timedelta(12)) == "follicular"  # day 13


def test_cycle_phase_ovulation_days_14_to_15():
    start = date(2026, 6, 1)
    assert compute_cycle_phase(start, 28, start + timedelta(13)) == "ovulation"  # day 14
    assert compute_cycle_phase(start, 28, start + timedelta(14)) == "ovulation"  # day 15


def test_cycle_phase_luteal_after_day_15():
    start = date(2026, 6, 1)
    assert compute_cycle_phase(start, 28, start + timedelta(15)) == "luteal"  # day 16
    assert compute_cycle_phase(start, 28, start + timedelta(27)) == "luteal"  # day 28


def test_cycle_phase_wraps_to_next_cycle():
    start = date(2026, 6, 1)
    # day 29 with 28-day cycle == day 1 of next cycle == period
    assert compute_cycle_phase(start, 28, start + timedelta(28)) == "period"


def test_momentum_no_history():
    m = compute_momentum(set(), date(2026, 6, 17))
    assert m == Momentum(current_streak=0, days_since_last=None, bucket="no_history")


def test_momentum_current_streak_of_three():
    on = date(2026, 6, 17)
    dates = {on, on - timedelta(1), on - timedelta(2)}
    m = compute_momentum(dates, on)
    assert m.current_streak == 3
    assert m.days_since_last == 0
    assert m.bucket == "current"


def test_momentum_missed_2_3_bucket():
    on = date(2026, 6, 17)
    m = compute_momentum({on - timedelta(3)}, on)
    assert m.days_since_last == 3
    assert m.bucket == "missed_2_3"


def test_momentum_missed_4_7_bucket():
    on = date(2026, 6, 17)
    m = compute_momentum({on - timedelta(6)}, on)
    assert m.bucket == "missed_4_7"


def test_momentum_full_reset_bucket():
    on = date(2026, 6, 17)
    m = compute_momentum({on - timedelta(20)}, on)
    assert m.bucket == "full_reset"


def test_momentum_ignores_future_dates():
    on = date(2026, 6, 17)
    m = compute_momentum({on + timedelta(2)}, on)
    assert m == Momentum(current_streak=0, days_since_last=None, bucket="no_history")
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `.venv/bin/python -m pytest tests/test_health/test_calculations.py -v`
Expected: FAIL — `ModuleNotFoundError: services.health.calculations`.

- [ ] **Step 3: Create the services.health package**

Create `services/health/__init__.py` (empty file).

- [ ] **Step 4: Implement the calculations**

Create `services/health/calculations.py`:

```python
from dataclasses import dataclass
from datetime import date, timedelta


def compute_cycle_phase(last_period_start, cycle_length, on_date):
    """Return menstrual phase for on_date, or None if untracked / date precedes start.

    Phases (day_in_cycle is 1-based):
      1-5   period
      6-13  follicular
      14-15 ovulation
      16+   luteal
    """
    if last_period_start is None:
        return None
    days_since = (on_date - last_period_start).days
    if days_since < 0:
        return None
    day_in_cycle = days_since % cycle_length + 1
    if day_in_cycle <= 5:
        return "period"
    if day_in_cycle <= 13:
        return "follicular"
    if day_in_cycle <= 15:
        return "ovulation"
    return "luteal"


@dataclass
class Momentum:
    current_streak: int          # consecutive days ending at the most recent completed workout
    days_since_last: int | None  # days from on_date back to last completed workout (None if none)
    bucket: str                  # no_history | current | missed_2_3 | missed_4_7 | missed_long | full_reset


def _momentum_bucket(days_since_last):
    if days_since_last <= 1:
        return "current"
    if days_since_last <= 3:
        return "missed_2_3"
    if days_since_last <= 7:
        return "missed_4_7"
    if days_since_last <= 13:
        return "missed_long"
    return "full_reset"


def compute_momentum(completed_dates, on_date):
    """Derive streak/recency from the set of dates with a completed workout."""
    past = sorted(d for d in completed_dates if d <= on_date)
    if not past:
        return Momentum(current_streak=0, days_since_last=None, bucket="no_history")
    past_set = set(past)
    last = past[-1]
    days_since_last = (on_date - last).days
    streak = 1
    cursor = last
    while (cursor - timedelta(days=1)) in past_set:
        cursor -= timedelta(days=1)
        streak += 1
    return Momentum(
        current_streak=streak,
        days_since_last=days_since_last,
        bucket=_momentum_bucket(days_since_last),
    )
```

- [ ] **Step 5: Run tests to verify they pass**

Run: `.venv/bin/python -m pytest tests/test_health/test_calculations.py -v`
Expected: PASS (13 tests).

- [ ] **Step 6: Commit**

```bash
git add services/health/__init__.py services/health/calculations.py tests/test_health/test_calculations.py
git commit -m "feat: add cycle-phase and momentum calculations"
```

---

### Task 3: Snapshot service — get_health_snapshot

**Files:**
- Create: `services/health/snapshot.py`
- Test: `tests/test_health/test_snapshot.py`

- [ ] **Step 1: Write failing snapshot tests**

Create `tests/test_health/test_snapshot.py`:

```python
import pytest
from datetime import date, timedelta
from django.contrib.auth.models import User
from apps.accounts.models import UserProfile
from apps.health.models import WellnessLog, SorenessLog, PeriodLog
from apps.fitness.models import FitnessPlan, WorkoutDay, WorkoutLog
from services.health.snapshot import get_health_snapshot, HealthSnapshot, SorenessItem


@pytest.fixture
def user(db):
    u = User.objects.create_user(username="s", password="x", email="s@e.com")
    UserProfile.objects.create(
        user=u, height_cm=170, weight_kg=65, gender="female",
        date_of_birth=date(1992, 3, 3), fitness_experience="beginner",
        primary_goal="Get active", diet_type="omnivore", food_allergies=[],
        daily_routine="", wake_time="07:00", sleep_time="23:00",
        work_schedule="9-5", workout_days_per_week=3, preferred_workout_days=[],
        workout_location="home", available_equipment=[],
        notification_email="s@e.com", tracks_cycle=True,
    )
    return u


def _completed_workout(user, on_date):
    plan = FitnessPlan.objects.create(
        user=user, week_number=1, start_date=on_date, end_date=on_date,
        total_workout_days=1, weekly_goal_summary="g", claude_reasoning="r",
    )
    day = WorkoutDay.objects.create(
        fitness_plan=plan, date=on_date, day_of_week="Monday",
        day_type="strength", focus_area="lower_body", estimated_duration_minutes=45,
    )
    return WorkoutLog.objects.create(
        user=user, workout_day=day, date=on_date, completed=True, completion_percentage=100,
    )


@pytest.mark.django_db
def test_snapshot_empty_day_degrades_gracefully(user):
    snap = get_health_snapshot(user, date(2026, 6, 17))
    assert isinstance(snap, HealthSnapshot)
    assert snap.sleep_hours is None
    assert snap.energy is None
    assert snap.soreness == []
    assert snap.cycle_phase is None
    assert snap.steps is None
    assert snap.resting_hr is None
    assert snap.momentum.bucket == "no_history"
    assert list(snap.recent_workouts) == []


@pytest.mark.django_db
def test_snapshot_assembles_logged_data(user):
    on = date(2026, 6, 17)
    WellnessLog.objects.create(
        user=user, date=on, sleep_hours=7, sleep_quality=4, mood_score=6,
        stress_level=3, energy_level=8, steps=9000, resting_hr_bpm=55,
    )
    SorenessLog.objects.create(user=user, date=on, muscle_group="quads", severity="severe")
    SorenessLog.objects.create(user=user, date=on, muscle_group="core", severity="mild")
    PeriodLog.objects.create(user=user, start_date=on - timedelta(2))  # day 3 -> period
    _completed_workout(user, on)

    snap = get_health_snapshot(user, on)
    assert snap.sleep_hours == 7
    assert snap.energy == 8
    assert snap.stress == 3
    assert snap.steps == 9000
    assert snap.resting_hr == 55
    assert SorenessItem("quads", "severe") in snap.soreness
    assert SorenessItem("core", "mild") in snap.soreness
    assert snap.cycle_phase == "period"
    assert snap.momentum.bucket == "current"
    assert len(snap.recent_workouts) == 1


@pytest.mark.django_db
def test_snapshot_cycle_phase_none_when_not_tracked(user):
    user.profile.tracks_cycle = False
    user.profile.save()
    PeriodLog.objects.create(user=user, start_date=date(2026, 6, 15))
    snap = get_health_snapshot(user, date(2026, 6, 17))
    assert snap.cycle_phase is None


@pytest.mark.django_db
def test_snapshot_uses_most_recent_period_on_or_before_date(user):
    PeriodLog.objects.create(user=user, start_date=date(2026, 5, 1))
    PeriodLog.objects.create(user=user, start_date=date(2026, 6, 16))  # day 2 on the 17th
    snap = get_health_snapshot(user, date(2026, 6, 17))
    assert snap.cycle_phase == "period"
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `.venv/bin/python -m pytest tests/test_health/test_snapshot.py -v`
Expected: FAIL — `ModuleNotFoundError: services.health.snapshot`.

- [ ] **Step 3: Implement the snapshot service**

Create `services/health/snapshot.py`:

```python
from dataclasses import dataclass

from apps.health.models import WellnessLog, SorenessLog, PeriodLog
from apps.fitness.models import WorkoutLog
from services.health.calculations import (
    compute_cycle_phase, compute_momentum, Momentum,
)


@dataclass(frozen=True)
class SorenessItem:
    muscle_group: str
    severity: str


@dataclass
class HealthSnapshot:
    date: object
    sleep_hours: object
    sleep_quality: object
    energy: object
    stress: object
    soreness: list
    cycle_phase: object
    momentum: Momentum
    steps: object
    resting_hr: object
    recent_workouts: list


def get_health_snapshot(user, on_date):
    """Assemble all health signals for `user` on `on_date`. Missing data -> None/empty."""
    wellness = WellnessLog.objects.filter(user=user, date=on_date).first()

    soreness = [
        SorenessItem(s.muscle_group, s.severity)
        for s in SorenessLog.objects.filter(user=user, date=on_date)
    ]

    cycle_phase = None
    profile = getattr(user, "profile", None)
    if profile is not None and profile.tracks_cycle:
        last_period = (
            PeriodLog.objects.filter(user=user, start_date__lte=on_date)
            .order_by("-start_date").first()
        )
        if last_period is not None:
            cycle_phase = compute_cycle_phase(
                last_period.start_date, profile.average_cycle_length, on_date,
            )

    completed_dates = set(
        WorkoutLog.objects.filter(user=user, completed=True, date__lte=on_date)
        .values_list("date", flat=True)
    )
    momentum = compute_momentum(completed_dates, on_date)

    recent_workouts = list(
        WorkoutLog.objects.filter(user=user, completed=True, date__lte=on_date)
        .order_by("-date")[:3]
    )

    return HealthSnapshot(
        date=on_date,
        sleep_hours=wellness.sleep_hours if wellness else None,
        sleep_quality=wellness.sleep_quality if wellness else None,
        energy=wellness.energy_level if wellness else None,
        stress=wellness.stress_level if wellness else None,
        soreness=soreness,
        cycle_phase=cycle_phase,
        momentum=momentum,
        steps=wellness.steps if wellness else None,
        resting_hr=wellness.resting_hr_bpm if wellness else None,
        recent_workouts=recent_workouts,
    )
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `.venv/bin/python -m pytest tests/test_health/test_snapshot.py -v`
Expected: PASS (4 tests).

- [ ] **Step 5: Commit**

```bash
git add services/health/snapshot.py tests/test_health/test_snapshot.py
git commit -m "feat: add get_health_snapshot service for the decision engine"
```

---

### Task 4: Daily check-in view, URL, and template

**Files:**
- Modify: `apps/health/views.py`
- Modify: `apps/health/urls.py`
- Create: `templates/health/checkin.html`
- Test: `tests/test_health/test_checkin_view.py`

- [ ] **Step 1: Write failing view tests**

Create `tests/test_health/test_checkin_view.py`:

```python
import pytest
from datetime import date
from django.urls import reverse
from django.contrib.auth.models import User
from apps.accounts.models import UserProfile
from apps.health.models import SorenessLog, WellnessLog, PeriodLog


def _make_user(tracks_cycle=False):
    u = User.objects.create_user(username="c", password="testpass123", email="c@e.com")
    UserProfile.objects.create(
        user=u, height_cm=170, weight_kg=65, gender="female",
        date_of_birth=date(1992, 3, 3), fitness_experience="beginner",
        primary_goal="Get active", diet_type="omnivore", food_allergies=[],
        daily_routine="", wake_time="07:00", sleep_time="23:00",
        work_schedule="9-5", workout_days_per_week=3, preferred_workout_days=[],
        workout_location="home", available_equipment=[],
        notification_email="c@e.com", tracks_cycle=tracks_cycle,
    )
    return u


@pytest.mark.django_db
def test_checkin_redirects_unauthenticated(client):
    resp = client.get(reverse("health_checkin"))
    assert resp.status_code == 302
    assert "/accounts/login" in resp["Location"]


@pytest.mark.django_db
def test_checkin_get_returns_200(client, db):
    _make_user()
    client.login(username="c", password="testpass123")
    resp = client.get(reverse("health_checkin"))
    assert resp.status_code == 200


@pytest.mark.django_db
def test_checkin_hides_cycle_controls_when_not_tracked(client, db):
    _make_user(tracks_cycle=False)
    client.login(username="c", password="testpass123")
    resp = client.get(reverse("health_checkin"))
    assert "Period started today" not in resp.content.decode()


@pytest.mark.django_db
def test_checkin_shows_cycle_controls_when_tracked(client, db):
    _make_user(tracks_cycle=True)
    client.login(username="c", password="testpass123")
    resp = client.get(reverse("health_checkin"))
    assert "Period started today" in resp.content.decode()


@pytest.mark.django_db
def test_checkin_post_saves_soreness_steps_and_resting_hr(client, db):
    _make_user()
    client.login(username="c", password="testpass123")
    resp = client.post(reverse("health_checkin"), {
        "soreness_quads": "severe",
        "soreness_core": "mild",
        "steps": "7400",
        "resting_hr_bpm": "60",
    })
    assert resp.status_code == 200
    today = date.today()
    sore = {s.muscle_group: s.severity for s in SorenessLog.objects.filter(user__username="c", date=today)}
    assert sore == {"quads": "severe", "core": "mild"}
    log = WellnessLog.objects.get(user__username="c", date=today)
    assert log.steps == 7400
    assert log.resting_hr_bpm == 60


@pytest.mark.django_db
def test_checkin_post_replaces_existing_soreness(client, db):
    user = _make_user()
    SorenessLog.objects.create(user=user, date=date.today(), muscle_group="back", severity="moderate")
    client.login(username="c", password="testpass123")
    client.post(reverse("health_checkin"), {"soreness_quads": "mild"})
    groups = {s.muscle_group for s in SorenessLog.objects.filter(user=user, date=date.today())}
    assert groups == {"quads"}  # back cleared, quads added


@pytest.mark.django_db
def test_checkin_post_period_button_creates_periodlog(client, db):
    user = _make_user(tracks_cycle=True)
    client.login(username="c", password="testpass123")
    client.post(reverse("health_checkin"), {"period_started": "true"})
    assert PeriodLog.objects.filter(user=user, start_date=date.today()).exists()
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `.venv/bin/python -m pytest tests/test_health/test_checkin_view.py -v`
Expected: FAIL — `NoReverseMatch: 'health_checkin'`.

- [ ] **Step 3: Add the URL**

In `apps/health/urls.py`, add to `urlpatterns`:

```python
    path("checkin/", views.checkin, name="health_checkin"),
```

- [ ] **Step 4: Implement the view**

In `apps/health/views.py`, update the imports line and append the view. Change the import to:

```python
from .models import NutritionLog, WellnessLog, SorenessLog, PeriodLog
from django.shortcuts import render
```

Append:

```python
@login_required
def checkin(request):
    today = date.today()
    if request.method == "POST":
        # Replace today's soreness with whatever groups were submitted.
        SorenessLog.objects.filter(user=request.user, date=today).delete()
        for group, _label in SorenessLog.MUSCLE_GROUP_CHOICES:
            severity = request.POST.get(f"soreness_{group}")
            if severity in {"mild", "moderate", "severe"}:
                SorenessLog.objects.create(
                    user=request.user, date=today, muscle_group=group, severity=severity,
                )

        steps = request.POST.get("steps") or None
        resting_hr = request.POST.get("resting_hr_bpm") or None
        if steps is not None or resting_hr is not None:
            log, _ = WellnessLog.objects.get_or_create(
                user=request.user, date=today,
                defaults={"sleep_hours": 0, "sleep_quality": 3, "mood_score": 5,
                          "stress_level": 5, "energy_level": 5},
            )
            log.steps = steps
            log.resting_hr_bpm = resting_hr
            log.save()

        if request.POST.get("period_started") == "true" and request.user.profile.tracks_cycle:
            PeriodLog.objects.get_or_create(user=request.user, start_date=today)

        return render(request, "health/checkin.html", _checkin_context(request, today))

    return render(request, "health/checkin.html", _checkin_context(request, today))


def _checkin_context(request, today):
    soreness = {
        s.muscle_group: s.severity
        for s in SorenessLog.objects.filter(user=request.user, date=today)
    }
    wellness = WellnessLog.objects.filter(user=request.user, date=today).first()
    return {
        "muscle_groups": SorenessLog.MUSCLE_GROUP_CHOICES,
        "severities": SorenessLog.SEVERITY_CHOICES,
        "soreness": soreness,
        "steps": wellness.steps if wellness else "",
        "resting_hr_bpm": wellness.resting_hr_bpm if wellness else "",
        "tracks_cycle": request.user.profile.tracks_cycle,
    }
```

- [ ] **Step 5: Create the template**

Create `templates/health/checkin.html`:

```html
{% extends "base_app.html" %}
{% block title %}Daily Check-in · Harmony{% endblock %}
{% block content %}
<section class="checkin-page">
  <h1 class="page-title">Daily Check-in</h1>
  <p class="page-subtitle">Takes 15 seconds. Everything is optional.</p>

  <form method="post" action="{% url 'health_checkin' %}" class="checkin-form">
    {% csrf_token %}

    <fieldset class="checkin-block">
      <legend>Sore anywhere today?</legend>
      <div class="soreness-grid">
        {% for group, label in muscle_groups %}
        <div class="soreness-item">
          <span class="soreness-label">{{ label }}</span>
          <select name="soreness_{{ group }}" class="soreness-select">
            <option value="">No</option>
            {% for value, slabel in severities %}
            <option value="{{ value }}" {% if soreness|get_item:group == value %}selected{% endif %}>{{ slabel }}</option>
            {% endfor %}
          </select>
        </div>
        {% endfor %}
      </div>
    </fieldset>

    <fieldset class="checkin-block">
      <legend>Numbers (if you know them)</legend>
      <label>Steps <input type="number" name="steps" value="{{ steps }}" min="0"></label>
      <label>Resting HR (bpm) <input type="number" name="resting_hr_bpm" value="{{ resting_hr_bpm }}" min="0"></label>
    </fieldset>

    {% if tracks_cycle %}
    <fieldset class="checkin-block">
      <legend>Cycle</legend>
      <label class="period-checkbox">
        <input type="checkbox" name="period_started" value="true">
        Period started today
      </label>
    </fieldset>
    {% endif %}

    <button type="submit" class="btn-primary">Save check-in</button>
  </form>
</section>
{% endblock %}
```

- [ ] **Step 6: Add the `get_item` template filter**

The template needs a dict lookup filter. First check whether one already exists:

Run: `grep -rn "def get_item" apps/ templates/ 2>/dev/null`

If it returns nothing, create `apps/health/templatetags/__init__.py` (empty) and `apps/health/templatetags/health_extras.py`:

```python
from django import template

register = template.Library()


@register.filter
def get_item(d, key):
    return d.get(key, "")
```

Then add `{% load health_extras %}` immediately after the `{% extends %}` line in `templates/health/checkin.html`. (If a `get_item` filter already exists, load that library instead and skip creating a new one.)

- [ ] **Step 7: Run tests to verify they pass**

Run: `.venv/bin/python -m pytest tests/test_health/test_checkin_view.py -v`
Expected: PASS (8 tests).

- [ ] **Step 8: Commit**

```bash
git add apps/health/views.py apps/health/urls.py templates/health/checkin.html apps/health/templatetags tests/test_health/test_checkin_view.py
git commit -m "feat: add daily health check-in page"
```

---

### Task 5: Dashboard entry point to the check-in

**Files:**
- Modify: `templates/base_app.html:38-53` (sidebar nav)
- Test: `tests/test_health/test_checkin_nav.py`

- [ ] **Step 1: Write failing nav test**

Create `tests/test_health/test_checkin_nav.py`:

```python
import pytest
from datetime import date
from django.urls import reverse
from django.contrib.auth.models import User
from apps.accounts.models import UserProfile


@pytest.fixture
def nav_user(db):
    u = User.objects.create_user(username="n", password="testpass123", email="n@e.com")
    UserProfile.objects.create(
        user=u, height_cm=170, weight_kg=65, gender="female",
        date_of_birth=date(1992, 3, 3), fitness_experience="beginner",
        primary_goal="Get active", diet_type="omnivore", food_allergies=[],
        daily_routine="", wake_time="07:00", sleep_time="23:00",
        work_schedule="9-5", workout_days_per_week=3, preferred_workout_days=[],
        workout_location="home", available_equipment=[],
        notification_email="n@e.com", onboarding_completed=True,
    )
    return u


@pytest.mark.django_db
def test_dashboard_sidebar_links_to_checkin(client, nav_user):
    client.login(username="n", password="testpass123")
    resp = client.get(reverse("dashboard"))
    assert reverse("health_checkin") in resp.content.decode()
```

- [ ] **Step 2: Run test to verify it fails**

Run: `.venv/bin/python -m pytest tests/test_health/test_checkin_nav.py -v`
Expected: FAIL — `health_checkin` URL not present in dashboard HTML.

- [ ] **Step 3: Add the sidebar nav item**

In `templates/base_app.html`, add after the profile nav item (the block ending at line 47, before `<div class="nav-spacer"></div>`):

```html
    <a href="{% url 'health_checkin' %}"
       class="nav-item {% if request.resolver_match.url_name == 'health_checkin' %}active{% endif %}"
       title="Daily Check-in">📝</a>
```

- [ ] **Step 4: Run test to verify it passes**

Run: `.venv/bin/python -m pytest tests/test_health/test_checkin_nav.py -v`
Expected: PASS.

- [ ] **Step 5: Run the full health test suite**

Run: `.venv/bin/python -m pytest tests/test_health/ -v`
Expected: PASS (all tasks' tests green — 31 tests).

- [ ] **Step 6: Commit**

```bash
git add templates/base_app.html tests/test_health/test_checkin_nav.py
git commit -m "feat: link daily check-in from the app sidebar"
```

---

## Notes for the implementer

- Always run Python through `.venv/bin/python` so the project virtualenv and `DJANGO_SETTINGS_MODULE` from `pytest.ini` are used.
- This branch is `feature/health-data-ingestion`. The spec it implements is committed alongside this plan.
- Out of scope (do not build here): the decision engine that consumes `HealthSnapshot`, progressive-overload/deload tracking, and wearable sync.
