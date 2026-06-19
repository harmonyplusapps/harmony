# Weight-loss + Running Progression Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a body-weight log + weekly trend, a daily step-target progression, and a weekly running-mileage progression (10% rule + running deload), surfaced where their data exists.

**Architecture:** New `WeightLog` model + check-in logging (the only data/UI work). Compute-on-read pure rules + thin DB services in a new `services/coach/cardio.py` (kept separate from strength `progression.py`). Suggestions gate by data presence; reuses `is_deload_week`. No Claude, no plan mutation.

**Tech Stack:** Python 3.13, Django 5.1, pytest + pytest-django, HTMX dark-UI templates. Run Python via `.venv/bin/python`.

**Spec:** `docs/superpowers/specs/2026-06-18-cardio-progression-design.md`

**Conventions (verified):**
- Tests in `tests/test_<app>/test_*.py`; `@pytest.mark.django_db` only where DB is needed; pure functions tested without DB.
- `WellnessLog.steps` (nullable int) exists. `RunningStrategy` is OneToOne with `WorkoutDay` (`total_distance_km` Decimal). `WorkoutLog.workout_day` has `related_name="logs"` and a `completed` flag.
- Check-in view (`apps/health/views.py::checkin`) uses `_parse_optional_int`, a `transaction.atomic()` block, and Post/Redirect/Get; `_checkin_context` builds the template context; template is `templates/health/checkin.html` (loads `health_extras`).

---

### Task 1: WeightLog model

**Files:**
- Modify: `apps/health/models.py`
- Test: `tests/test_health/test_weightlog_model.py`
- Generated: migration under `apps/health/migrations/`

- [ ] **Step 1: Write failing model test**

Create `tests/test_health/test_weightlog_model.py`:

```python
import pytest
from datetime import date
from decimal import Decimal
from django.db import IntegrityError
from django.contrib.auth.models import User
from apps.health.models import WeightLog


@pytest.fixture
def user(db):
    return User.objects.create_user(username="w", password="x", email="w@e.com")


@pytest.mark.django_db
def test_weightlog_persists(user):
    log = WeightLog.objects.create(user=user, date=date(2026, 6, 18), weight_kg=Decimal("64.5"))
    log.refresh_from_db()
    assert log.weight_kg == Decimal("64.5")


@pytest.mark.django_db
def test_weightlog_unique_per_user_date(user):
    WeightLog.objects.create(user=user, date=date(2026, 6, 18), weight_kg=Decimal("64.5"))
    with pytest.raises(IntegrityError):
        WeightLog.objects.create(user=user, date=date(2026, 6, 18), weight_kg=Decimal("65.0"))
```

- [ ] **Step 2: Run test to verify it fails**

Run: `.venv/bin/python -m pytest tests/test_health/test_weightlog_model.py -v`
Expected: FAIL — `ImportError: cannot import name 'WeightLog'`.

- [ ] **Step 3: Add the model**

Append to `apps/health/models.py`:

```python
class WeightLog(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="weight_logs")
    date = models.DateField()
    weight_kg = models.DecimalField(max_digits=5, decimal_places=1)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ["user", "date"]
        ordering = ["-date"]
```

- [ ] **Step 4: Generate the migration**

Run: `.venv/bin/python manage.py makemigrations health`
Expected: a new migration adding `WeightLog`.

- [ ] **Step 5: Run test to verify it passes**

Run: `.venv/bin/python -m pytest tests/test_health/test_weightlog_model.py -v`
Expected: PASS (2 tests).

- [ ] **Step 6: Commit**

```bash
git add apps/health/models.py apps/health/migrations tests/test_health/test_weightlog_model.py
git commit -m "feat: add WeightLog model"
```

---

### Task 2: Cardio progression — pure rules

**Files:**
- Create: `services/coach/cardio.py`
- Test: `tests/test_coach/test_cardio_rules.py`

- [ ] **Step 1: Write failing rule tests**

Create `tests/test_coach/test_cardio_rules.py`:

```python
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
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `.venv/bin/python -m pytest tests/test_coach/test_cardio_rules.py -v`
Expected: FAIL — `services.coach.cardio` does not exist.

- [ ] **Step 3: Implement the pure rules**

Create `services/coach/cardio.py`:

```python
from dataclasses import dataclass

STEP_CAP = 10000
STEP_INCREMENT = 500
WEEKLY_MILEAGE_GROWTH = 1.10
DELOAD_MILEAGE_FACTOR = 0.7
TREND_EPSILON = 0.2  # kg; smaller weekly changes read as "flat"


@dataclass(frozen=True)
class WeightTrend:
    current_avg: float
    prior_avg: float | None
    delta_kg: float | None   # signed: current_avg - prior_avg
    direction: str           # down | up | flat


def round_to_500(value: int) -> int:
    return round(value / STEP_INCREMENT) * STEP_INCREMENT


def suggest_step_target(recent_avg_steps: int | None) -> int | None:
    if recent_avg_steps is None:
        return None
    if recent_avg_steps >= STEP_CAP:
        return STEP_CAP
    return min(STEP_CAP, round_to_500(recent_avg_steps) + STEP_INCREMENT)


def suggest_weekly_mileage_km(prior_week_km: float | None, is_deload: bool) -> float | None:
    if not prior_week_km:
        return None
    factor = DELOAD_MILEAGE_FACTOR if is_deload else WEEKLY_MILEAGE_GROWTH
    return round(prior_week_km * factor, 1)


def weekly_average(samples: list) -> float | None:
    return round(sum(samples) / len(samples), 1) if samples else None


def weight_trend(current_avg: float, prior_avg: float | None,
                 epsilon: float = TREND_EPSILON) -> str:
    if prior_avg is None:
        return "flat"
    diff = current_avg - prior_avg
    if diff <= -epsilon:
        return "down"
    if diff >= epsilon:
        return "up"
    return "flat"
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `.venv/bin/python -m pytest tests/test_coach/test_cardio_rules.py -v`
Expected: PASS (11 tests).

- [ ] **Step 5: Commit**

```bash
git add services/coach/cardio.py tests/test_coach/test_cardio_rules.py
git commit -m "feat: add cardio progression pure rules"
```

---

### Task 3: Cardio progression — DB services

**Files:**
- Modify: `services/coach/cardio.py`
- Test: `tests/test_coach/test_cardio_services.py`

- [ ] **Step 1: Write failing service tests**

Create `tests/test_coach/test_cardio_services.py`:

```python
import pytest
from datetime import date, timedelta
from decimal import Decimal
from django.contrib.auth.models import User
from apps.health.models import WellnessLog, WeightLog
from apps.fitness.models import (
    FitnessPlan, WorkoutDay, WorkoutLog, RunningStrategy,
)
from services.coach.cardio import (
    suggest_step_target_for, suggest_weekly_mileage_for, body_weight_trend,
)

TODAY = date.today()


def _user(username="c"):
    return User.objects.create_user(username=username, password="x", email=f"{username}@e.com")


def _steps(user, days_ago, steps):
    WellnessLog.objects.create(
        user=user, date=TODAY - timedelta(days=days_ago),
        sleep_hours=8, sleep_quality=4, mood_score=5, stress_level=4,
        energy_level=6, steps=steps,
    )


def _run(user, days_ago, km, completed=True):
    d = TODAY - timedelta(days=days_ago)
    plan = FitnessPlan.objects.create(
        user=user, week_number=1, start_date=d, end_date=d, is_active=False,
        total_workout_days=1, weekly_goal_summary="g", claude_reasoning="r",
    )
    wd = WorkoutDay.objects.create(
        fitness_plan=plan, date=d, day_of_week=d.strftime("%A"),
        day_type="running", focus_area="cardio", estimated_duration_minutes=30,
    )
    RunningStrategy.objects.create(
        workout_day=wd, run_type="easy", total_distance_km=Decimal(str(km)),
        total_duration_minutes=30, pace_target="6:00/km",
    )
    if completed:
        WorkoutLog.objects.create(user=user, workout_day=wd, date=d, completed=True)


def _weight(user, days_ago, kg):
    WeightLog.objects.create(user=user, date=TODAY - timedelta(days=days_ago), weight_kg=Decimal(str(kg)))


@pytest.mark.django_db
def test_step_target_none_when_no_steps():
    assert suggest_step_target_for(_user(), TODAY) is None


@pytest.mark.django_db
def test_step_target_averages_recent_steps():
    user = _user()
    _steps(user, 1, 8000)
    _steps(user, 2, 8400)   # avg 8200 -> round 8000 -> +500 = 8500
    assert suggest_step_target_for(user, TODAY) == 8500


@pytest.mark.django_db
def test_step_target_ignores_old_days():
    user = _user()
    _steps(user, 1, 8000)
    _steps(user, 20, 2000)  # outside 7-day window, ignored -> avg 8000 -> 8500
    assert suggest_step_target_for(user, TODAY) == 8500


@pytest.mark.django_db
def test_weekly_mileage_sums_completed_runs():
    user = _user()
    _run(user, 2, 5.0)
    _run(user, 4, 8.0)      # total 13.0 -> *1.10 = 14.3
    assert suggest_weekly_mileage_for(user, TODAY, is_deload=False) == 14.3


@pytest.mark.django_db
def test_weekly_mileage_excludes_uncompleted_and_old():
    user = _user()
    _run(user, 2, 5.0)
    _run(user, 3, 9.0, completed=False)   # excluded
    _run(user, 20, 100.0)                 # outside window
    assert suggest_weekly_mileage_for(user, TODAY, is_deload=False) == 5.5  # 5.0*1.10


@pytest.mark.django_db
def test_weekly_mileage_deload():
    user = _user()
    _run(user, 2, 10.0)
    assert suggest_weekly_mileage_for(user, TODAY, is_deload=True) == 7.0  # 10*0.7


@pytest.mark.django_db
def test_weekly_mileage_none_without_runs():
    assert suggest_weekly_mileage_for(_user(), TODAY, is_deload=False) is None


@pytest.mark.django_db
def test_body_weight_trend_down():
    user = _user()
    _weight(user, 1, 64.0)
    _weight(user, 3, 64.4)   # current window avg 64.2
    _weight(user, 9, 65.0)
    _weight(user, 11, 65.2)  # prior window avg 65.1
    t = body_weight_trend(user, TODAY)
    assert t is not None
    assert t.current_avg == 64.2
    assert t.prior_avg == 65.1
    assert t.direction == "down"


@pytest.mark.django_db
def test_body_weight_trend_none_with_fewer_than_two_current():
    user = _user()
    _weight(user, 1, 64.0)
    assert body_weight_trend(user, TODAY) is None


@pytest.mark.django_db
def test_body_weight_trend_excludes_other_users():
    user = _user("a")
    other = _user("b")
    _weight(other, 1, 90.0)
    _weight(other, 2, 91.0)
    assert body_weight_trend(user, TODAY) is None
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `.venv/bin/python -m pytest tests/test_coach/test_cardio_services.py -v`
Expected: FAIL — the `_for` / `body_weight_trend` functions are not defined.

- [ ] **Step 3: Implement the services**

Append to `services/coach/cardio.py`:

```python
from datetime import timedelta


def suggest_step_target_for(user, on_date):
    from apps.health.models import WellnessLog
    window_start = on_date - timedelta(days=7)
    steps = list(
        WellnessLog.objects.filter(
            user=user, date__gt=window_start, date__lte=on_date, steps__isnull=False,
        ).values_list("steps", flat=True)
    )
    if not steps:
        return None
    return suggest_step_target(int(sum(steps) / len(steps)))


def suggest_weekly_mileage_for(user, on_date, is_deload):
    from apps.fitness.models import RunningStrategy
    window_start = on_date - timedelta(days=7)
    distances = RunningStrategy.objects.filter(
        workout_day__fitness_plan__user=user,
        workout_day__date__gt=window_start,
        workout_day__date__lte=on_date,
        workout_day__logs__completed=True,
    ).values_list("total_distance_km", flat=True)
    total = float(sum(distances)) if distances else 0.0
    return suggest_weekly_mileage_km(total, is_deload)


def body_weight_trend(user, on_date):
    from apps.health.models import WeightLog
    current_start = on_date - timedelta(days=7)
    prior_start = on_date - timedelta(days=14)
    current = [
        float(w) for w in WeightLog.objects.filter(
            user=user, date__gt=current_start, date__lte=on_date,
        ).values_list("weight_kg", flat=True)
    ]
    if len(current) < 2:
        return None
    prior = [
        float(w) for w in WeightLog.objects.filter(
            user=user, date__gt=prior_start, date__lte=current_start,
        ).values_list("weight_kg", flat=True)
    ]
    current_avg = weekly_average(current)
    prior_avg = weekly_average(prior)
    delta = round(current_avg - prior_avg, 1) if prior_avg is not None else None
    return WeightTrend(
        current_avg=current_avg, prior_avg=prior_avg, delta_kg=delta,
        direction=weight_trend(current_avg, prior_avg),
    )
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `.venv/bin/python -m pytest tests/test_coach/test_cardio_services.py -v`
Expected: PASS (10 tests).

- [ ] **Step 5: Commit**

```bash
git add services/coach/cardio.py tests/test_coach/test_cardio_services.py
git commit -m "feat: add cardio progression DB services"
```

---

### Task 4: Log body weight on the daily check-in

**Files:**
- Modify: `apps/health/views.py`
- Modify: `templates/health/checkin.html`
- Test: `tests/test_health/test_checkin_weight.py`

- [ ] **Step 1: Write failing tests**

Create `tests/test_health/test_checkin_weight.py`:

```python
import pytest
from datetime import date, timedelta
from decimal import Decimal
from django.urls import reverse
from django.contrib.auth.models import User
from apps.accounts.models import UserProfile
from apps.health.models import WeightLog, WellnessLog


def _user():
    u = User.objects.create_user(username="cw", password="testpass123", email="cw@e.com")
    UserProfile.objects.create(
        user=u, height_cm=170, weight_kg=65, gender="female",
        date_of_birth=date(1992, 3, 3), fitness_experience="beginner",
        primary_goal="Get active", diet_type="omnivore", food_allergies=[],
        daily_routine="", wake_time="07:00", sleep_time="23:00",
        work_schedule="9-5", workout_days_per_week=3, preferred_workout_days=[],
        workout_location="home", available_equipment=[],
        notification_email="cw@e.com",
    )
    return u


@pytest.mark.django_db
def test_checkin_post_saves_weight(client):
    _user()
    client.login(username="cw", password="testpass123")
    client.post(reverse("health_checkin"), {"weight_kg": "64.5"})
    log = WeightLog.objects.get(user__username="cw", date=date.today())
    assert log.weight_kg == Decimal("64.5")


@pytest.mark.django_db
def test_checkin_blank_weight_creates_no_log(client):
    _user()
    client.login(username="cw", password="testpass123")
    client.post(reverse("health_checkin"), {"soreness_quads": "mild"})
    assert not WeightLog.objects.filter(user__username="cw", date=date.today()).exists()


@pytest.mark.django_db
def test_checkin_shows_step_target(client):
    user = _user()
    today = date.today()
    WellnessLog.objects.create(
        user=user, date=today - timedelta(days=1), sleep_hours=8, sleep_quality=4,
        mood_score=5, stress_level=4, energy_level=6, steps=8000,
    )
    client.login(username="cw", password="testpass123")
    resp = client.get(reverse("health_checkin"))
    assert resp.context["step_target"] == 8500
    assert "8500" in resp.content.decode()
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `.venv/bin/python -m pytest tests/test_health/test_checkin_weight.py -v`
Expected: FAIL — no WeightLog written / `step_target` absent.

- [ ] **Step 3: Update the view**

In `apps/health/views.py`:

Add imports near the top (with the existing imports):

```python
from decimal import Decimal, InvalidOperation
from .models import WeightLog
from services.coach.cardio import suggest_step_target_for
```

Add a parse helper next to `_parse_optional_int`:

```python
def _parse_optional_decimal(value):
    try:
        return Decimal(value) if value not in (None, "") else None
    except (InvalidOperation, TypeError):
        return None
```

In `checkin`, inside the POST branch, parse the weight alongside the others (add after the `resting_hr = ...` line):

```python
        weight = _parse_optional_decimal(request.POST.get("weight_kg"))
```

Inside the `with transaction.atomic():` block, after the `WellnessLog` upsert block, add:

```python
            if weight is not None:
                WeightLog.objects.update_or_create(
                    user=request.user, date=today, defaults={"weight_kg": weight},
                )
```

In `_checkin_context`, add today's weight and the step target. Before the `return {`:

```python
    weight_log = WeightLog.objects.filter(user=request.user, date=today).first()
```

And add these two keys to the returned dict:

```python
        "weight_kg": weight_log.weight_kg if weight_log else "",
        "step_target": suggest_step_target_for(request.user, today),
```

- [ ] **Step 4: Update the template**

In `templates/health/checkin.html`, replace the "Numbers" fieldset (the `<fieldset class="checkin-block">` containing the Steps and Resting HR inputs) with:

```html
    <fieldset class="checkin-block">
      <legend>Numbers (if you know them)</legend>
      <label>Steps <input type="number" name="steps" value="{{ steps }}" min="0">{% if step_target %} <span class="step-target">goal {{ step_target }}</span>{% endif %}</label>
      <label>Resting HR (bpm) <input type="number" name="resting_hr_bpm" value="{{ resting_hr_bpm }}" min="0"></label>
      <label>Weight (kg) <input type="number" step="0.1" name="weight_kg" value="{{ weight_kg }}" min="0"></label>
    </fieldset>
```

- [ ] **Step 5: Run tests to verify they pass**

Run: `.venv/bin/python -m pytest tests/test_health/test_checkin_weight.py -v`
Expected: PASS (3 tests).

- [ ] **Step 6: Run the full health suite (no regressions)**

Run: `.venv/bin/python -m pytest tests/test_health/ -q`
Expected: PASS.

- [ ] **Step 7: Commit**

```bash
git add apps/health/views.py templates/health/checkin.html tests/test_health/test_checkin_weight.py
git commit -m "feat: log body weight and show step target on the daily check-in"
```

---

### Task 5: Surface weight trend + step goal on the dashboard

**Files:**
- Modify: `apps/dashboard/views.py`
- Modify: `templates/dashboard/index.html`
- Test: `tests/test_dashboard/test_cardio_dashboard.py`

- [ ] **Step 1: Write failing tests**

Create `tests/test_dashboard/test_cardio_dashboard.py`:

```python
import pytest
from datetime import date, timedelta
from decimal import Decimal
from django.urls import reverse
from django.contrib.auth.models import User
from apps.accounts.models import UserProfile
from apps.health.models import WeightLog, WellnessLog


def _user():
    u = User.objects.create_user(username="cd", password="testpass123", email="cd@e.com")
    UserProfile.objects.create(
        user=u, height_cm=170, weight_kg=65, gender="female",
        date_of_birth=date(1992, 3, 3), fitness_experience="beginner",
        primary_goal="Get active", diet_type="omnivore", food_allergies=[],
        daily_routine="", wake_time="07:00", sleep_time="23:00",
        work_schedule="9-5", workout_days_per_week=3, preferred_workout_days=[],
        workout_location="home", available_equipment=[],
        notification_email="cd@e.com", onboarding_completed=True,
    )
    return u


@pytest.mark.django_db
def test_dashboard_shows_step_goal(client):
    user = _user()
    WellnessLog.objects.create(
        user=user, date=date.today() - timedelta(days=1), sleep_hours=8, sleep_quality=4,
        mood_score=5, stress_level=4, energy_level=6, steps=8000,
    )
    client.login(username="cd", password="testpass123")
    resp = client.get(reverse("dashboard"))
    assert resp.context["step_target"] == 8500
    assert "8500" in resp.content.decode()


@pytest.mark.django_db
def test_dashboard_shows_weight_trend(client):
    user = _user()
    today = date.today()
    for d, kg in [(1, "64.0"), (3, "64.4"), (9, "65.0"), (11, "65.2")]:
        WeightLog.objects.create(user=user, date=today - timedelta(days=d), weight_kg=Decimal(kg))
    client.login(username="cd", password="testpass123")
    resp = client.get(reverse("dashboard"))
    assert resp.context["weight_trend"] is not None
    assert resp.context["weight_trend"].direction == "down"
    assert "kg" in resp.content.decode()


@pytest.mark.django_db
def test_dashboard_no_cardio_data_renders_clean(client):
    _user()
    client.login(username="cd", password="testpass123")
    resp = client.get(reverse("dashboard"))
    assert resp.context["weight_trend"] is None
    assert resp.context["step_target"] is None
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `.venv/bin/python -m pytest tests/test_dashboard/test_cardio_dashboard.py -v`
Expected: FAIL — `step_target`/`weight_trend` not in context.

- [ ] **Step 3: Update the dashboard view**

In `apps/dashboard/views.py`, add the import:

```python
from services.coach.cardio import body_weight_trend, suggest_step_target_for
```

In the `dashboard` view, before the `return render(...)`, add:

```python
    weight_trend = body_weight_trend(request.user, today)
    step_target = suggest_step_target_for(request.user, today)
```

Add these two keys to the `render(...)` context dict:

```python
        "weight_trend": weight_trend,
        "step_target": step_target,
```

- [ ] **Step 4: Update the template**

In `templates/dashboard/index.html`, immediately after the closing `</div>` of the `wellness-card` block (the `<div class="wellness-card">…</div>` that ends just before the "Weekly Progress" section header), insert:

```html
{% if weight_trend or step_target %}
<div class="card" style="margin-top:10px;">
  <div class="content-card">
    <div class="card-icon" style="background:rgba(52,211,153,0.15)">📈</div>
    <div>
      {% if weight_trend %}
      <div class="card-title">Weight {{ weight_trend.current_avg }} kg{% if weight_trend.delta_kg is not None %}
        {% if weight_trend.direction == "down" %}· ▼ {{ weight_trend.delta_kg|floatformat:1|cut:"-" }} kg vs last week{% elif weight_trend.direction == "up" %}· ▲ {{ weight_trend.delta_kg|floatformat:1 }} kg vs last week{% else %}· ≈ steady{% endif %}{% endif %}</div>
      {% endif %}
      {% if step_target %}<div class="card-sub">Today's step goal: {{ step_target }}</div>{% endif %}
    </div>
  </div>
</div>
{% endif %}
```

- [ ] **Step 5: Run tests to verify they pass**

Run: `.venv/bin/python -m pytest tests/test_dashboard/test_cardio_dashboard.py -v`
Expected: PASS (3 tests).

- [ ] **Step 6: Commit**

```bash
git add apps/dashboard/views.py templates/dashboard/index.html tests/test_dashboard/test_cardio_dashboard.py
git commit -m "feat: surface weight trend and step goal on the dashboard"
```

---

### Task 6: Surface weekly running mileage on the weekly plan

**Files:**
- Modify: `apps/dashboard/views.py`
- Modify: `templates/dashboard/weekly_plan.html`
- Test: `tests/test_dashboard/test_mileage_surfacing.py`

- [ ] **Step 1: Write failing tests**

Create `tests/test_dashboard/test_mileage_surfacing.py`:

```python
import pytest
from datetime import date, timedelta
from decimal import Decimal
from django.urls import reverse
from django.contrib.auth.models import User
from apps.accounts.models import UserProfile
from apps.fitness.models import FitnessPlan, WorkoutDay, WorkoutLog, RunningStrategy


def _user():
    u = User.objects.create_user(username="mp", password="testpass123", email="mp@e.com")
    UserProfile.objects.create(
        user=u, height_cm=170, weight_kg=65, gender="female",
        date_of_birth=date(1992, 3, 3), fitness_experience="beginner",
        primary_goal="Run a 5K", diet_type="omnivore", food_allergies=[],
        daily_routine="", wake_time="07:00", sleep_time="23:00",
        work_schedule="9-5", workout_days_per_week=3, preferred_workout_days=[],
        workout_location="outdoor", available_equipment=[],
        notification_email="mp@e.com", onboarding_completed=True,
    )
    return u


def _completed_run(user, days_ago, km, week_number=1, is_active=False):
    d = date.today() - timedelta(days=days_ago)
    plan = FitnessPlan.objects.create(
        user=user, week_number=week_number, start_date=d, end_date=d, is_active=is_active,
        total_workout_days=1, weekly_goal_summary="g", claude_reasoning="r",
    )
    wd = WorkoutDay.objects.create(
        fitness_plan=plan, date=d, day_of_week=d.strftime("%A"),
        day_type="running", focus_area="cardio", estimated_duration_minutes=30,
    )
    RunningStrategy.objects.create(
        workout_day=wd, run_type="easy", total_distance_km=Decimal(str(km)),
        total_duration_minutes=30, pace_target="6:00/km",
    )
    WorkoutLog.objects.create(user=user, workout_day=wd, date=d, completed=True)


@pytest.mark.django_db
def test_weekly_plan_shows_mileage_target(client):
    user = _user()
    # Active plan (so the page renders a plan) + prior completed runs in the 7-day window.
    FitnessPlan.objects.create(
        user=user, week_number=2, start_date=date.today(), end_date=date.today(),
        is_active=True, total_workout_days=1, weekly_goal_summary="g", claude_reasoning="r",
    )
    _completed_run(user, 2, 5.0)
    _completed_run(user, 4, 8.0)  # total 13.0 -> 14.3
    client.login(username="mp", password="testpass123")
    resp = client.get(reverse("weekly_plan"))
    assert resp.context["weekly_mileage_km"] == 14.3
    assert "14.3 km" in resp.content.decode()


@pytest.mark.django_db
def test_weekly_plan_no_mileage_without_runs(client):
    user = _user()
    FitnessPlan.objects.create(
        user=user, week_number=2, start_date=date.today(), end_date=date.today(),
        is_active=True, total_workout_days=1, weekly_goal_summary="g", claude_reasoning="r",
    )
    client.login(username="mp", password="testpass123")
    resp = client.get(reverse("weekly_plan"))
    assert resp.context["weekly_mileage_km"] is None
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `.venv/bin/python -m pytest tests/test_dashboard/test_mileage_surfacing.py -v`
Expected: FAIL — `weekly_mileage_km` not in context.

- [ ] **Step 3: Update the weekly_plan view**

In `apps/dashboard/views.py`, extend the cardio import to include the mileage service:

```python
from services.coach.cardio import body_weight_trend, suggest_step_target_for, suggest_weekly_mileage_for
```

In the `weekly_plan` view, add `weekly_mileage_km = None` next to the `is_deload = False` / `weight_suggestions = {}` initializers, and inside the `if fitness_plan:` block (after `is_deload = is_deload_week(...)`), add:

```python
        weekly_mileage_km = suggest_weekly_mileage_for(request.user, date.today(), is_deload)
```

Add the key to the `weekly_plan` `render(...)` context dict:

```python
        "weekly_mileage_km": weekly_mileage_km,
```

- [ ] **Step 4: Update the template**

In `templates/dashboard/weekly_plan.html`, immediately after the Week heading block (the `<div style="margin-bottom:16px;">…</div>` that contains the `<h1>Week …</h1>`), insert:

```html
{% if weekly_mileage_km %}
<p class="mileage-target" style="font-size:12px;color:#34d399;margin:-8px 0 12px;font-weight:700;">Running this week: aim ≤ {{ weekly_mileage_km }} km</p>
{% endif %}
```

- [ ] **Step 5: Run tests to verify they pass**

Run: `.venv/bin/python -m pytest tests/test_dashboard/test_mileage_surfacing.py -v`
Expected: PASS (2 tests).

- [ ] **Step 6: Run dashboard + coach + health suites and Django check**

Run: `.venv/bin/python -m pytest tests/test_dashboard/ tests/test_coach/ tests/test_health/ -q`
Expected: PASS.
Run: `.venv/bin/python manage.py check`
Expected: 0 issues.

- [ ] **Step 7: Commit**

```bash
git add apps/dashboard/views.py templates/dashboard/weekly_plan.html tests/test_dashboard/test_mileage_surfacing.py
git commit -m "feat: surface weekly running mileage target on the weekly plan"
```

---

## Notes for the implementer

- Run Python through `.venv/bin/python`.
- Branch: `feature/cardio-progression` (off `main`, which has slices #2/#3/#4a). Spec committed alongside this plan.
- All new code is read-only except the check-in `WeightLog` upsert. Suggestions gate by data presence — templates render nothing when a value is `None`.
- Out of scope: general-fitness progression / run-type rotation (#4c), standalone cardio-duration, a structured goal field, persisting/auto-applying targets, any Claude call.
