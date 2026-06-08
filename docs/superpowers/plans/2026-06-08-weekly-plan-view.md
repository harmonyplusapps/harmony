# Weekly Plan View Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a `/dashboard/plan/` page showing the full 7-day fitness and nutrition plan with day tabs and a collapsible weekly summary.

**Architecture:** A new view in `apps/dashboard/views.py` fetches the active `FitnessPlan` and `HealthPlan`, builds an ordered list of 7 day objects, and renders `templates/dashboard/weekly_plan.html`. Day tabs and the collapsible reasoning toggle use Alpine.js (already loaded in `base.html`). All data is server-rendered — no HTMX needed.

**Tech Stack:** Django 5.1, Alpine.js 3.x (already in base.html), existing CSS in `static/css/main.css`

---

## File Map

| File | Action | Responsibility |
|---|---|---|
| `tests/test_dashboard/__init__.py` | Create | Make test package |
| `tests/test_dashboard/test_weekly_plan.py` | Create | Tests for weekly_plan view |
| `apps/dashboard/views.py` | Modify | Add `weekly_plan` view |
| `apps/dashboard/urls.py` | Modify | Add `/dashboard/plan/` URL |
| `templates/dashboard/weekly_plan.html` | Create | Full weekly plan template |
| `templates/dashboard/index.html` | Modify | Add "View Full Week →" link |

---

## Task 1: Test scaffolding

**Files:**
- Create: `tests/test_dashboard/__init__.py`
- Create: `tests/test_dashboard/test_weekly_plan.py`

- [ ] **Step 1: Create the test package**

```bash
touch /path/to/Harmony/tests/test_dashboard/__init__.py
```

- [ ] **Step 2: Write the failing tests**

Create `tests/test_dashboard/test_weekly_plan.py`:

```python
import pytest
from datetime import date
from django.urls import reverse
from django.contrib.auth.models import User
from apps.accounts.models import UserProfile
from apps.fitness.models import FitnessPlan, WorkoutDay
from apps.health.models import HealthPlan, MealPlan


@pytest.fixture
def user_with_plan(db):
    user = User.objects.create_user(username="planuser", password="testpass123")
    UserProfile.objects.create(
        user=user,
        height_cm=170, weight_kg=70, gender="female",
        date_of_birth=date(1995, 1, 1),
        fitness_experience="beginner",
        primary_goal="Lose weight",
        diet_type="omnivore",
        food_allergies=[],
        food_preferences="",
        daily_routine="Work from home",
        wake_time="07:00", sleep_time="23:00",
        work_schedule="9-5",
        workout_days_per_week=3,
        preferred_workout_days=["Monday", "Wednesday", "Friday"],
        running_days_per_week=1,
        workout_location="home",
        available_equipment=[],
        notification_email="plan@example.com",
        onboarding_completed=True,
    )
    fitness_plan = FitnessPlan.objects.create(
        user=user,
        week_number=1,
        start_date=date(2026, 6, 8),
        end_date=date(2026, 6, 14),
        total_workout_days=3,
        total_running_days=1,
        weekly_goal_summary="Build base fitness",
        claude_reasoning="Started with beginner-friendly plan",
        is_active=True,
    )
    WorkoutDay.objects.create(
        fitness_plan=fitness_plan,
        date=date(2026, 6, 9),
        day_of_week="Monday",
        day_type="strength",
        focus_area="full_body",
        estimated_duration_minutes=45,
    )
    health_plan = HealthPlan.objects.create(
        user=user,
        week_number=1,
        start_date=date(2026, 6, 8),
        end_date=date(2026, 6, 14),
        daily_calorie_target=1800,
        daily_protein_g=130,
        daily_carbs_g=180,
        daily_fat_g=60,
        daily_fiber_g=25,
        daily_water_ml=2500,
        claude_reasoning="Moderate deficit for fat loss",
        is_active=True,
    )
    MealPlan.objects.create(
        health_plan=health_plan,
        day_of_week="Monday",
        meal_type="breakfast",
        meal_name="Oats with berries",
        description="Steel-cut oats",
        calories=350,
        protein_g=12,
        carbs_g=55,
        fat_g=8,
        fiber_g=6,
        ingredients=["oats", "berries"],
        order=0,
    )
    return user


@pytest.mark.django_db
def test_weekly_plan_redirects_unauthenticated(client):
    resp = client.get(reverse("weekly_plan"))
    assert resp.status_code == 302
    assert "/accounts/login" in resp["Location"]


@pytest.mark.django_db
def test_weekly_plan_redirects_if_not_onboarded(client, base_user):
    client.login(username="base", password="testpass123")
    resp = client.get(reverse("weekly_plan"))
    assert resp.status_code == 302
    assert "onboarding" in resp["Location"]


@pytest.mark.django_db
def test_weekly_plan_shows_no_plan_message(client, complete_profile):
    client.login(username="base", password="testpass123")
    resp = client.get(reverse("weekly_plan"))
    assert resp.status_code == 200
    assert "No active plan" in resp.content.decode()


@pytest.mark.django_db
def test_weekly_plan_renders_all_days(client, user_with_plan):
    client.login(username="planuser", password="testpass123")
    resp = client.get(reverse("weekly_plan"))
    assert resp.status_code == 200
    content = resp.content.decode()
    for day in ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]:
        assert day in content


@pytest.mark.django_db
def test_weekly_plan_renders_workout_data(client, user_with_plan):
    client.login(username="planuser", password="testpass123")
    resp = client.get(reverse("weekly_plan"))
    assert resp.status_code == 200
    content = resp.content.decode()
    assert "strength" in content.lower()
    assert "Build base fitness" in content


@pytest.mark.django_db
def test_weekly_plan_renders_meal_data(client, user_with_plan):
    client.login(username="planuser", password="testpass123")
    resp = client.get(reverse("weekly_plan"))
    assert resp.status_code == 200
    assert "Oats with berries" in resp.content.decode()
```

- [ ] **Step 3: Run tests to confirm they fail**

```bash
cd /Users/sreelekhapotluri/Desktop/Harmony && .venv/bin/pytest tests/test_dashboard/ -v
```

Expected: All fail with `NoReverseMatch` or `ImportError` — the view doesn't exist yet.

- [ ] **Step 4: Commit the tests**

```bash
git add tests/test_dashboard/
git commit -m "test: weekly plan view tests"
```

---

## Task 2: View and URL

**Files:**
- Modify: `apps/dashboard/views.py`
- Modify: `apps/dashboard/urls.py`

- [ ] **Step 1: Add the `weekly_plan` view to `apps/dashboard/views.py`**

Append to the bottom of `apps/dashboard/views.py` (after the existing `dashboard` function):

```python
@login_required
def weekly_plan(request):
    profile = getattr(request.user, "profile", None)
    if not profile or not profile.onboarding_completed:
        return redirect("onboarding_step1")

    DAYS = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
    today_name = date.today().strftime("%A")

    fitness_plan = FitnessPlan.objects.filter(user=request.user, is_active=True).first()
    health_plan = HealthPlan.objects.filter(user=request.user, is_active=True).first()

    days = []
    if fitness_plan and health_plan:
        workout_days = {
            wd.day_of_week: wd
            for wd in fitness_plan.workout_days
                .prefetch_related("exercises__exercise_cache", "running_strategy")
                .all()
        }
        meals_by_day = {}
        for meal in health_plan.meal_plans.order_by("order").all():
            meals_by_day.setdefault(meal.day_of_week, []).append(meal)

        days = [
            {
                "name": day,
                "short": day[:3],
                "workout": workout_days.get(day),
                "meals": meals_by_day.get(day, []),
                "is_today": day == today_name,
            }
            for day in DAYS
        ]

    return render(request, "dashboard/weekly_plan.html", {
        "fitness_plan": fitness_plan,
        "health_plan": health_plan,
        "days": days,
        "today_name": today_name,
    })
```

Also add the missing import at the top of `apps/dashboard/views.py` — `HealthPlan` is not yet imported:

```python
from apps.health.models import HealthPlan, MealPlan
```

- [ ] **Step 2: Add the URL to `apps/dashboard/urls.py`**

```python
from django.urls import path
from . import views

urlpatterns = [
    path("", views.dashboard, name="dashboard"),
    path("plan/", views.weekly_plan, name="weekly_plan"),
]
```

- [ ] **Step 3: Run the tests — expect template-missing errors now, not URL errors**

```bash
.venv/bin/pytest tests/test_dashboard/ -v
```

Expected: Fails with `TemplateDoesNotExist: dashboard/weekly_plan.html` — the view resolves but no template yet.

---

## Task 3: Template

**Files:**
- Create: `templates/dashboard/weekly_plan.html`

- [ ] **Step 1: Create the template**

```html
{% extends "base.html" %}
{% block title %}Weekly Plan — Harmony{% endblock %}
{% block content %}

{% if not fitness_plan %}
  <h1>Weekly Plan</h1>
  <p>No active plan found. <a href="{% url 'dashboard' %}">Back to dashboard</a></p>
{% else %}

<h1>Week {{ fitness_plan.week_number }} · {{ fitness_plan.start_date }} – {{ fitness_plan.end_date }}</h1>

<section>
  <h2>Weekly Goal</h2>
  <p>{{ fitness_plan.weekly_goal_summary }}</p>

  <div x-data="{ open: false }">
    <button @click="open = !open" type="button">
      <span x-text="open ? 'Hide reasoning ▲' : 'Show Claude\'s reasoning ▼'"></span>
    </button>
    <div x-show="open" style="margin-top:0.75rem; padding:0.75rem; background:#f8f9fa; border-left:3px solid #2563eb;">
      <p>{{ fitness_plan.claude_reasoning }}</p>
    </div>
  </div>
</section>

{% if health_plan %}
<section>
  <p>Daily targets: {{ health_plan.daily_calorie_target }} kcal · {{ health_plan.daily_protein_g }}g protein · {{ health_plan.daily_carbs_g }}g carbs · {{ health_plan.daily_fat_g }}g fat · {{ health_plan.daily_fiber_g }}g fiber · {{ health_plan.daily_water_ml }}ml water</p>
</section>
{% endif %}

<div x-data="{ activeDay: '{{ today_name }}' }">

  <div style="display:flex; gap:0.5rem; flex-wrap:wrap; margin:1rem 0;">
    {% for day in days %}
    <button
      type="button"
      @click="activeDay = '{{ day.name }}'"
      :style="activeDay === '{{ day.name }}' ? 'background:#1d4ed8;' : 'background:#6b7280;'"
    >
      {{ day.short }}
    </button>
    {% endfor %}
  </div>

  {% for day in days %}
  <div x-show="activeDay === '{{ day.name }}'">
    <h2>{{ day.name }}</h2>

    <section>
      <h3>Workout</h3>
      {% if day.workout %}
        <p>
          <strong>{{ day.workout.day_type|title }}</strong> —
          {{ day.workout.focus_area|title }} ·
          {{ day.workout.estimated_duration_minutes }} min
        </p>

        {% if day.workout.warmup_description %}
        <p><strong>Warmup:</strong> {{ day.workout.warmup_description }}</p>
        {% endif %}

        {% if day.workout.exercises.all %}
        <table style="width:100%; border-collapse:collapse; margin:0.5rem 0;">
          <thead>
            <tr style="border-bottom:1px solid #eee; text-align:left;">
              <th>Exercise</th><th>Section</th><th>Volume</th><th>Intensity</th><th>Notes</th>
            </tr>
          </thead>
          <tbody>
            {% for ex in day.workout.exercises.all %}
            <tr style="border-bottom:1px solid #f3f4f6;">
              <td>{{ ex.display_name }}</td>
              <td>{{ ex.section }}</td>
              <td>
                {% if ex.sets %}{{ ex.sets }} × {{ ex.reps }} reps{% endif %}
                {% if ex.duration_seconds %}{{ ex.duration_seconds }}s{% endif %}
                {% if ex.distance_km %}{{ ex.distance_km }}km{% endif %}
              </td>
              <td>{{ ex.intensity }}</td>
              <td>{{ ex.notes }}</td>
            </tr>
            {% endfor %}
          </tbody>
        </table>
        {% endif %}

        {% with rs=day.workout.running_strategy %}
        {% if rs %}
        <div style="margin-top:0.75rem; padding:0.75rem; background:#f0fdf4; border-left:3px solid #16a34a;">
          <strong>Running: {{ rs.run_type|title }}</strong> —
          {{ rs.total_distance_km }}km · {{ rs.total_duration_minutes }} min ·
          Pace: {{ rs.pace_target }}
          {% if rs.heart_rate_zone %} · HR: {{ rs.heart_rate_zone }}{% endif %}
          {% if rs.notes %}<p>{{ rs.notes }}</p>{% endif %}
        </div>
        {% endif %}
        {% endwith %}

        {% if day.workout.cooldown_description %}
        <p><strong>Cooldown:</strong> {{ day.workout.cooldown_description }}</p>
        {% endif %}

        {% if day.workout.notes %}
        <p><em>{{ day.workout.notes }}</em></p>
        {% endif %}

      {% else %}
        <p>Rest day.</p>
      {% endif %}
    </section>

    <section>
      <h3>Meals</h3>
      {% if day.meals %}
        {% for meal in day.meals %}
        <div style="border:1px solid #e5e7eb; border-radius:6px; padding:0.75rem; margin-bottom:0.75rem;">
          <strong>{{ meal.get_meal_type_display }}: {{ meal.meal_name }}</strong>
          <p style="margin:0.25rem 0; color:#6b7280;">{{ meal.description }}</p>
          <p style="margin:0.25rem 0; font-size:0.875rem;">
            {{ meal.calories }} kcal · P: {{ meal.protein_g }}g · C: {{ meal.carbs_g }}g ·
            F: {{ meal.fat_g }}g · Fiber: {{ meal.fiber_g }}g
          </p>
          {% if meal.ingredients %}
          <p style="margin:0.25rem 0; font-size:0.875rem;"><strong>Ingredients:</strong> {{ meal.ingredients|join:", " }}</p>
          {% endif %}
          {% if meal.preparation_notes %}
          <p style="margin:0.25rem 0; font-size:0.875rem; font-style:italic;">{{ meal.preparation_notes }}</p>
          {% endif %}
        </div>
        {% endfor %}
      {% else %}
        <p>No meals planned.</p>
      {% endif %}
    </section>

  </div>
  {% endfor %}

</div>

{% endif %}

<p style="margin-top:2rem;"><a href="{% url 'dashboard' %}">← Back to Dashboard</a></p>

{% endblock %}
```

- [ ] **Step 2: Run the tests — all should pass now**

```bash
.venv/bin/pytest tests/test_dashboard/ -v
```

Expected: All 6 tests pass.

- [ ] **Step 3: Commit**

```bash
git add apps/dashboard/views.py apps/dashboard/urls.py templates/dashboard/weekly_plan.html tests/test_dashboard/
git commit -m "feat: weekly plan view with day tabs"
```

---

## Task 4: Dashboard link

**Files:**
- Modify: `templates/dashboard/index.html`

- [ ] **Step 1: Add "View Full Week →" link to the Weekly Progress section**

In `templates/dashboard/index.html`, replace the Weekly Progress section:

```html
<section>
  <h2>Weekly Progress</h2>
  <p>{{ completed_days }} / {{ planned_days }} workout days completed this week.</p>
  <a href="{% url 'weekly_plan' %}">View Full Week →</a>
</section>
```

- [ ] **Step 2: Verify in the browser**

Open http://127.0.0.1:8000/dashboard/ — confirm "View Full Week →" link is visible. Click it — confirm the weekly plan page loads with 7 day tabs and today's tab active.

- [ ] **Step 3: Commit**

```bash
git add templates/dashboard/index.html
git commit -m "feat: add weekly plan link to dashboard"
```
