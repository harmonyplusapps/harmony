# Dashboard UI Redesign Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace the plain white Harmony dashboard with a dark, health-app-inspired UI — persistent branded sidebar, logo header, profile hero, daily progress rings, and dark card styling on all authenticated pages.

**Architecture:** A new `base_app.html` acts as the shell for all authenticated pages (dashboard, weekly plan, profile edit), containing a 56px header with the C-style H logo and stacked wordmark, plus a 64px icon-only sidebar. A new `static/css/app.css` holds all dark-theme styles. `base.html` and `main.css` are not touched (they serve login/register/onboarding).

**Tech Stack:** Django 5.1 templates, vanilla CSS (CSS custom properties, CSS Grid), Alpine.js (existing, for weekly plan day tabs), pytest-django.

---

## File Map

| Action | Path | Responsibility |
|---|---|---|
| Create | `static/css/app.css` | All dark-theme styles for authenticated pages |
| Create | `templates/base_app.html` | App shell: header + sidebar + content block |
| Create | `tests/test_dashboard/test_dashboard.py` | Tests for dashboard view context + rendered content |
| Modify | `apps/dashboard/views.py` | Add `profile` and `progress_dots` to dashboard + weekly_plan contexts |
| Modify | `templates/dashboard/index.html` | Full dashboard redesign |
| Modify | `templates/dashboard/weekly_plan.html` | Extend base_app, restyle with dark cards |
| Modify | `templates/accounts/profile_edit.html` | Extend base_app, restyle form sections |

---

### Task 1: Create `static/css/app.css`

**Files:**
- Create: `static/css/app.css`

- [ ] **Step 1: Create `static/css/app.css`**

```css
*, *::before, *::after { box-sizing: border-box; }

:root {
  --bg: #090912;
  --surface: #0f0f1a;
  --card: #13131e;
  --border: #1c1c2e;
  --accent: #6c63ff;
  --accent-light: #a78bfa;
  --green: #22c55e;
  --green-light: #4ade80;
  --orange: #f97316;
  --text: #e0e0f0;
  --muted: #555;
}

body {
  font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
  background: var(--bg);
  color: var(--text);
  margin: 0;
  min-height: 100vh;
}

.app-shell {
  display: grid;
  grid-template-columns: 64px 1fr;
  grid-template-rows: 56px 1fr;
  min-height: 100vh;
}

/* ── Header ── */
.app-header {
  grid-column: 1 / -1;
  height: 56px;
  background: #090912;
  border-bottom: 1px solid var(--border);
  display: flex;
  align-items: center;
  padding: 0 20px;
  justify-content: space-between;
}

.header-brand {
  display: flex;
  align-items: center;
  gap: 10px;
  text-decoration: none;
}

.header-wordmark {
  display: flex;
  flex-direction: column;
  line-height: 1.2;
}

.wordmark-name {
  font-size: 18px;
  font-weight: 800;
  letter-spacing: -0.03em;
  background: linear-gradient(90deg, #fff 50%, #a78bfa);
  -webkit-background-clip: text;
  -webkit-text-fill-color: transparent;
  background-clip: text;
}

.wordmark-tagline {
  font-size: 8px;
  font-weight: 500;
  letter-spacing: 0.12em;
  text-transform: uppercase;
  color: #444;
}

.header-notif {
  width: 32px;
  height: 32px;
  background: #1a1a28;
  border-radius: 8px;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 14px;
  cursor: pointer;
  border: none;
}

/* ── Sidebar ── */
.app-sidebar {
  background: #0d0d16;
  border-right: 1px solid #1a1a28;
  display: flex;
  flex-direction: column;
  align-items: center;
  padding: 16px 0;
  gap: 6px;
}

.nav-item {
  width: 44px;
  height: 44px;
  border-radius: 12px;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 18px;
  cursor: pointer;
  color: #444;
  text-decoration: none;
  position: relative;
  border: none;
  background: transparent;
}

.nav-item:hover:not(.active) {
  background: #1a1a28;
  color: #888;
}

.nav-item.active {
  background: rgba(108, 99, 255, 0.18);
  color: #a78bfa;
}

.nav-item.active::before {
  content: '';
  position: absolute;
  left: -1px;
  width: 3px;
  height: 24px;
  background: #6c63ff;
  border-radius: 0 4px 4px 0;
}

.nav-spacer { flex: 1; }

.nav-logout {
  background: transparent;
  border: none;
  padding: 0;
  cursor: pointer;
}

/* ── Main ── */
.app-main {
  background: var(--surface);
  overflow-y: auto;
  padding: 20px;
}

/* ── Generic card ── */
.card {
  background: var(--card);
  border: 1px solid var(--border);
  border-radius: 14px;
  padding: 14px 16px;
}

/* ── Section headers ── */
.section-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin: 18px 0 10px;
}

.section-title {
  font-size: 11px;
  font-weight: 700;
  color: var(--muted);
  text-transform: uppercase;
  letter-spacing: 0.1em;
}

.section-link {
  font-size: 11px;
  color: var(--accent);
  text-decoration: none;
}

/* ── Profile hero ── */
.profile-hero {
  background: linear-gradient(135deg, #12082a 0%, #0d1a3f 50%, #071a14 100%);
  border-radius: 16px;
  padding: 16px 18px;
  display: flex;
  align-items: center;
  gap: 14px;
  border: 1px solid rgba(108, 99, 255, 0.15);
  position: relative;
  overflow: hidden;
}

.profile-hero::after {
  content: '';
  position: absolute;
  top: -40px;
  right: -40px;
  width: 160px;
  height: 160px;
  background: radial-gradient(circle, rgba(108, 99, 255, 0.12) 0%, transparent 70%);
  pointer-events: none;
}

.profile-avatar {
  width: 48px;
  height: 48px;
  background: linear-gradient(135deg, #6c63ff, #a78bfa);
  border-radius: 14px;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 20px;
  font-weight: 800;
  color: #fff;
  flex-shrink: 0;
}

.profile-info { flex: 1; }

.profile-name {
  font-size: 17px;
  font-weight: 800;
  color: #fff;
  margin-bottom: 2px;
}

.profile-goal {
  font-size: 11px;
  color: var(--accent-light);
  font-weight: 600;
  margin-bottom: 8px;
}

.profile-stats { display: flex; gap: 14px; }

.pstat-val { font-size: 14px; font-weight: 800; color: var(--text); }

.pstat-lbl {
  font-size: 9px;
  color: var(--muted);
  text-transform: uppercase;
  letter-spacing: 0.06em;
}

.profile-edit-btn {
  background: rgba(108, 99, 255, 0.15);
  border: 1px solid rgba(108, 99, 255, 0.25);
  color: var(--accent-light);
  font-size: 11px;
  font-weight: 600;
  padding: 6px 12px;
  border-radius: 8px;
  cursor: pointer;
  text-decoration: none;
  white-space: nowrap;
  z-index: 1;
}

/* ── Progress rings ── */
.rings-grid {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 10px;
}

.ring-card {
  background: var(--card);
  border-radius: 12px;
  padding: 12px 14px;
  border: 1px solid var(--border);
  display: flex;
  align-items: center;
  gap: 10px;
}

.ring {
  width: 38px;
  height: 38px;
  border-radius: 50%;
  border: 3px solid;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 9px;
  font-weight: 800;
  flex-shrink: 0;
  text-align: center;
  line-height: 1.1;
}

.ring-label { font-size: 10px; font-weight: 700; color: #ccc; }
.ring-sub { font-size: 9px; color: var(--muted); margin-top: 1px; }

/* ── Content cards ── */
.cards-list { display: flex; flex-direction: column; gap: 10px; }

.content-card { display: flex; align-items: center; gap: 14px; }

.card-icon {
  width: 42px;
  height: 42px;
  border-radius: 12px;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 18px;
  flex-shrink: 0;
}

.card-title { font-size: 13px; font-weight: 700; color: var(--text); margin-bottom: 3px; }
.card-sub { font-size: 11px; color: var(--muted); }

.card-badge {
  margin-left: auto;
  font-size: 10px;
  font-weight: 700;
  padding: 4px 10px;
  border-radius: 20px;
  white-space: nowrap;
  flex-shrink: 0;
}

.card-chevron {
  margin-left: auto;
  color: #333;
  font-size: 20px;
  text-decoration: none;
}

/* ── Wellness card ── */
.wellness-card {
  background: linear-gradient(135deg, #0d1a10, #141427);
  border-radius: 14px;
  padding: 14px 16px;
  border: 1px solid #1e2e22;
}

.wellness-row { display: flex; gap: 8px; }

.wellness-chip {
  flex: 1;
  background: rgba(0, 0, 0, 0.3);
  border-radius: 8px;
  padding: 8px 6px;
  text-align: center;
}

.wellness-icon { font-size: 14px; margin-bottom: 2px; }
.wellness-chip-lbl { font-size: 9px; color: var(--muted); text-transform: uppercase; }
.wellness-chip-val { font-size: 12px; font-weight: 700; color: var(--green-light); }

/* ── Progress dots ── */
.progress-dots { display: flex; gap: 6px; }
.day-dot { flex: 1; height: 6px; border-radius: 3px; }

/* ── Weekly plan ── */
.day-tabs { display: flex; gap: 6px; flex-wrap: wrap; margin-bottom: 16px; }

.day-tab {
  padding: 6px 14px;
  border-radius: 20px;
  font-size: 12px;
  font-weight: 600;
  cursor: pointer;
}

.exercise-table { width: 100%; border-collapse: collapse; margin: 8px 0; font-size: 12px; }

.exercise-table th {
  border-bottom: 1px solid var(--border);
  text-align: left;
  padding: 6px 8px;
  font-size: 10px;
  font-weight: 700;
  color: var(--muted);
  text-transform: uppercase;
  letter-spacing: 0.06em;
}

.exercise-table td {
  border-bottom: 1px solid #1a1a28;
  padding: 6px 8px;
  color: var(--text);
}

.running-block {
  margin-top: 10px;
  padding: 10px 14px;
  background: rgba(34, 197, 94, 0.08);
  border-left: 3px solid var(--green);
  border-radius: 0 8px 8px 0;
  font-size: 12px;
  color: var(--text);
}

.macro-strip {
  display: flex;
  gap: 12px;
  flex-wrap: wrap;
  font-size: 12px;
  color: var(--muted);
  margin-bottom: 16px;
}

.macro-strip strong { color: var(--text); }

.meal-card { margin-bottom: 8px; }
.meal-name { font-size: 13px; font-weight: 700; color: var(--text); margin-bottom: 3px; }
.meal-desc { font-size: 11px; color: var(--muted); margin-bottom: 4px; }
.meal-macros { font-size: 11px; color: var(--muted); }

/* ── Profile edit form ── */
.form-page-title { font-size: 18px; font-weight: 800; color: #fff; margin-bottom: 4px; }
.form-page-sub { font-size: 13px; color: var(--muted); margin-bottom: 20px; }

.form-section { margin-bottom: 16px; }

.form-section h2 {
  font-size: 11px;
  font-weight: 700;
  color: var(--accent-light);
  text-transform: uppercase;
  letter-spacing: 0.1em;
  margin-bottom: 12px;
  padding-bottom: 6px;
  border-bottom: 1px solid var(--border);
}

.form-field { margin-bottom: 12px; }

.form-field label {
  display: block;
  font-size: 11px;
  font-weight: 600;
  color: #888;
  margin-bottom: 4px;
  text-transform: uppercase;
  letter-spacing: 0.06em;
}

.form-field input,
.form-field select,
.form-field textarea {
  width: 100%;
  background: #0d0d16;
  border: 1px solid var(--border);
  border-radius: 8px;
  color: var(--text);
  padding: 8px 12px;
  font-size: 13px;
  font-family: inherit;
}

.form-field input:focus,
.form-field select:focus,
.form-field textarea:focus {
  outline: none;
  border-color: var(--accent);
}

.form-field .errorlist {
  color: #f87171;
  font-size: 11px;
  list-style: none;
  padding: 0;
  margin: 4px 0 0;
}

/* ── Save banner ── */
.save-banner {
  background: rgba(34, 197, 94, 0.1);
  border: 1px solid rgba(34, 197, 94, 0.25);
  border-radius: 10px;
  padding: 12px 16px;
  margin-bottom: 16px;
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  font-size: 13px;
  color: var(--green-light);
  flex-wrap: wrap;
}

.save-banner-actions { display: flex; gap: 8px; align-items: center; }

.btn-primary {
  background: var(--accent);
  color: #fff;
  border: none;
  border-radius: 8px;
  padding: 7px 16px;
  font-size: 12px;
  font-weight: 700;
  cursor: pointer;
}

.btn-ghost { color: var(--muted); font-size: 12px; text-decoration: none; }

.submit-btn {
  background: var(--accent);
  color: #fff;
  border: none;
  border-radius: 10px;
  padding: 10px 24px;
  font-size: 14px;
  font-weight: 700;
  cursor: pointer;
  margin-top: 8px;
}

.submit-btn:hover { background: #5b53e8; }
```

- [ ] **Step 2: Commit**

```bash
cd /Users/sreelekhapotluri/Desktop/Harmony
git add static/css/app.css
git commit -m "style: add dark theme CSS for authenticated app shell"
```

---

### Task 2: Create `templates/base_app.html` and tests

**Files:**
- Create: `templates/base_app.html`
- Create: `tests/test_dashboard/test_dashboard.py`

- [ ] **Step 1: Write the failing tests**

Create `tests/test_dashboard/test_dashboard.py`:

```python
import pytest
from datetime import date
from django.urls import reverse
from django.contrib.auth.models import User
from apps.accounts.models import UserProfile


@pytest.fixture
def onboarded_user(db):
    user = User.objects.create_user(
        username="dashuser", password="testpass123",
        first_name="Alex", last_name="Smith",
    )
    UserProfile.objects.create(
        user=user,
        height_cm=175, weight_kg=70, gender="male",
        date_of_birth=date(1995, 1, 1),
        fitness_experience="intermediate",
        primary_goal="Build muscle",
        diet_type="omnivore",
        food_allergies=[],
        food_preferences="",
        daily_routine="Office job",
        wake_time="07:00", sleep_time="23:00",
        work_schedule="9-5",
        workout_days_per_week=4,
        preferred_workout_days=["Monday", "Tuesday", "Thursday", "Friday"],
        running_days_per_week=0,
        workout_location="gym",
        available_equipment=["barbell", "dumbbells"],
        notification_email="alex@example.com",
        onboarding_completed=True,
    )
    return user


@pytest.mark.django_db
def test_dashboard_redirects_unauthenticated(client):
    resp = client.get(reverse("dashboard"))
    assert resp.status_code == 302
    assert "/accounts/login" in resp["Location"]


@pytest.mark.django_db
def test_dashboard_returns_200(client, onboarded_user):
    client.login(username="dashuser", password="testpass123")
    resp = client.get(reverse("dashboard"))
    assert resp.status_code == 200


@pytest.mark.django_db
def test_dashboard_context_has_profile(client, onboarded_user):
    client.login(username="dashuser", password="testpass123")
    resp = client.get(reverse("dashboard"))
    assert resp.context["profile"] is not None
    assert resp.context["profile"].primary_goal == "Build muscle"


@pytest.mark.django_db
def test_dashboard_context_has_progress_dots(client, onboarded_user):
    client.login(username="dashuser", password="testpass123")
    resp = client.get(reverse("dashboard"))
    assert "progress_dots" in resp.context
    assert isinstance(resp.context["progress_dots"], list)


@pytest.mark.django_db
def test_dashboard_renders_user_full_name(client, onboarded_user):
    client.login(username="dashuser", password="testpass123")
    resp = client.get(reverse("dashboard"))
    assert "Alex Smith" in resp.content.decode()


@pytest.mark.django_db
def test_dashboard_renders_primary_goal(client, onboarded_user):
    client.login(username="dashuser", password="testpass123")
    resp = client.get(reverse("dashboard"))
    assert "Build muscle" in resp.content.decode()


@pytest.mark.django_db
def test_dashboard_renders_logo_wordmark(client, onboarded_user):
    client.login(username="dashuser", password="testpass123")
    resp = client.get(reverse("dashboard"))
    content = resp.content.decode()
    assert "wordmark-name" in content
    assert "Your fitness companion" in content


@pytest.mark.django_db
def test_dashboard_renders_sidebar(client, onboarded_user):
    client.login(username="dashuser", password="testpass123")
    resp = client.get(reverse("dashboard"))
    content = resp.content.decode()
    assert "app-sidebar" in content
    assert reverse("weekly_plan") in content
    assert reverse("profile_edit") in content


@pytest.mark.django_db
def test_dashboard_renders_no_plan_message_when_no_plan(client, onboarded_user):
    client.login(username="dashuser", password="testpass123")
    resp = client.get(reverse("dashboard"))
    assert "No plan yet" in resp.content.decode()
```

- [ ] **Step 2: Run tests to confirm they fail**

```bash
cd /Users/sreelekhapotluri/Desktop/Harmony && source .venv/bin/activate && pytest tests/test_dashboard/test_dashboard.py -v 2>&1 | head -50
```

Expected: Most tests FAIL — `base_app.html` and updated `index.html` don't exist yet.

- [ ] **Step 3: Create `templates/base_app.html`**

```html
{% load static %}
<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>{% block title %}Harmony{% endblock %}</title>
  <link rel="stylesheet" href="{% static 'css/app.css' %}">
  <script src="https://unpkg.com/htmx.org@2.0.0" defer></script>
  <script defer src="https://cdn.jsdelivr.net/npm/alpinejs@3.x.x/dist/cdn.min.js"></script>
</head>
<body>
<div class="app-shell">

  <header class="app-header">
    <a href="{% url 'dashboard' %}" class="header-brand">
      <svg width="36" height="36" viewBox="0 0 56 56" fill="none" xmlns="http://www.w3.org/2000/svg">
        <rect width="56" height="56" rx="10" fill="#1a1a2e"/>
        <rect x="13" y="12" width="7" height="32" rx="2" fill="none" stroke="url(#logo-grad)" stroke-width="2.5"/>
        <rect x="36" y="12" width="7" height="32" rx="2" fill="none" stroke="url(#logo-grad)" stroke-width="2.5"/>
        <line x1="20" y1="26" x2="36" y2="26" stroke="url(#logo-grad)" stroke-width="3" stroke-linecap="round"/>
        <circle cx="28" cy="26" r="3" fill="url(#logo-grad)"/>
        <defs>
          <linearGradient id="logo-grad" x1="13" y1="12" x2="43" y2="44" gradientUnits="userSpaceOnUse">
            <stop stop-color="#a78bfa"/>
            <stop offset="1" stop-color="#6c63ff"/>
          </linearGradient>
        </defs>
      </svg>
      <div class="header-wordmark">
        <span class="wordmark-name">Harmony</span>
        <span class="wordmark-tagline">Your fitness companion</span>
      </div>
    </a>
    <button class="header-notif" type="button" aria-label="Notifications">🔔</button>
  </header>

  <nav class="app-sidebar">
    <a href="{% url 'dashboard' %}"
       class="nav-item {% if request.resolver_match.url_name == 'dashboard' %}active{% endif %}"
       title="Dashboard">🏠</a>
    <a href="{% url 'weekly_plan' %}"
       class="nav-item {% if request.resolver_match.url_name == 'weekly_plan' %}active{% endif %}"
       title="Weekly Plan">📅</a>
    <a href="{% url 'profile_edit' %}"
       class="nav-item {% if request.resolver_match.url_name == 'profile_edit' %}active{% endif %}"
       title="Profile">👤</a>
    <div class="nav-spacer"></div>
    <form method="post" action="{% url 'logout' %}">
      {% csrf_token %}
      <button type="submit" class="nav-item nav-logout" title="Logout">🚪</button>
    </form>
  </nav>

  <main class="app-main">
    {% block content %}{% endblock %}
  </main>

</div>
</body>
</html>
```

- [ ] **Step 4: Commit**

```bash
git add templates/base_app.html tests/test_dashboard/test_dashboard.py
git commit -m "feat: add base_app.html shell and dashboard tests"
```

---

### Task 3: Update `apps/dashboard/views.py`

**Files:**
- Modify: `apps/dashboard/views.py`

Both `dashboard` and `weekly_plan` views already have `profile` as a local variable (used for the onboarding redirect check at lines 10 and 74). This task adds it to the render context and adds `progress_dots` to the dashboard context.

- [ ] **Step 1: Update the `dashboard` view's `return render(...)` call**

In `apps/dashboard/views.py`, replace lines 58–69:

```python
    return render(request, "dashboard/index.html", {
        "today": today,
        "today_workout": today_workout,
        "workout_log": workout_log,
        "today_meals": today_meals,
        "wellness_log": wellness_log,
        "fitness_plan": fitness_plan,
        "health_plan": health_plan,
        "completed_days": completed_days,
        "planned_days": planned_days,
        "meal_types": MealPlan.MEAL_TYPE_CHOICES,
    })
```

with:

```python
    progress_dots = [i < completed_days for i in range(max(planned_days, 1))]

    return render(request, "dashboard/index.html", {
        "profile": profile,
        "today": today,
        "today_workout": today_workout,
        "workout_log": workout_log,
        "today_meals": today_meals,
        "wellness_log": wellness_log,
        "fitness_plan": fitness_plan,
        "health_plan": health_plan,
        "completed_days": completed_days,
        "planned_days": planned_days,
        "progress_dots": progress_dots,
        "meal_types": MealPlan.MEAL_TYPE_CHOICES,
    })
```

- [ ] **Step 2: Update the `weekly_plan` view's `return render(...)` call**

In `apps/dashboard/views.py`, replace the `return render(...)` at the end of `weekly_plan` (currently lines 108–113):

```python
    return render(request, "dashboard/weekly_plan.html", {
        "fitness_plan": fitness_plan,
        "health_plan": health_plan,
        "days": days,
        "today_name": today_name,
    })
```

with:

```python
    return render(request, "dashboard/weekly_plan.html", {
        "profile": profile,
        "fitness_plan": fitness_plan,
        "health_plan": health_plan,
        "days": days,
        "today_name": today_name,
    })
```

- [ ] **Step 3: Run context tests**

```bash
pytest tests/test_dashboard/test_dashboard.py::test_dashboard_context_has_profile tests/test_dashboard/test_dashboard.py::test_dashboard_context_has_progress_dots -v
```

Expected: Both PASS.

- [ ] **Step 4: Commit**

```bash
git add apps/dashboard/views.py
git commit -m "feat: add profile and progress_dots to dashboard and weekly_plan contexts"
```

---

### Task 4: Redesign `templates/dashboard/index.html`

**Files:**
- Modify: `templates/dashboard/index.html`

- [ ] **Step 1: Replace the entire contents of `templates/dashboard/index.html`**

```html
{% extends "base_app.html" %}
{% block title %}Dashboard — Harmony{% endblock %}
{% block content %}

<div class="profile-hero">
  <div class="profile-avatar">{{ request.user.get_full_name|default:request.user.username|slice:":1"|upper }}</div>
  <div class="profile-info">
    <div class="profile-name">{{ request.user.get_full_name|default:request.user.username }}</div>
    <div class="profile-goal">🎯 {{ profile.primary_goal }}</div>
    <div class="profile-stats">
      <div><div class="pstat-val">{{ profile.weight_kg }}kg</div><div class="pstat-lbl">Weight</div></div>
      <div><div class="pstat-val">{{ profile.height_cm }}cm</div><div class="pstat-lbl">Height</div></div>
      <div><div class="pstat-val">{{ profile.workout_location|title }}</div><div class="pstat-lbl">Location</div></div>
      <div><div class="pstat-val">{{ profile.fitness_experience|title }}</div><div class="pstat-lbl">Level</div></div>
    </div>
  </div>
  <a href="{% url 'profile_edit' %}" class="profile-edit-btn">Edit Profile</a>
</div>

<div class="section-header" style="margin-top:18px;">
  <span class="section-title">Today's Progress</span>
  <span style="font-size:11px;color:#555;text-transform:uppercase;letter-spacing:0.08em;">{{ today|date:"l, N j Y" }}</span>
</div>
<div class="rings-grid">
  <div class="ring-card">
    <div class="ring" style="border-color:#6c63ff;color:#a78bfa">{{ completed_days }}/{{ planned_days }}</div>
    <div><div class="ring-label">Workouts</div><div class="ring-sub">This week</div></div>
  </div>
  <div class="ring-card">
    <div class="ring" style="border-color:#f97316;color:#fb923c">{% if health_plan %}{{ health_plan.daily_calorie_target }}{% else %}—{% endif %}</div>
    <div><div class="ring-label">Calories</div><div class="ring-sub">Daily target</div></div>
  </div>
  <div class="ring-card">
    <div class="ring" style="border-color:#22c55e;color:#4ade80">{{ wellness_log.sleep_hours }}h</div>
    <div><div class="ring-label">Sleep</div><div class="ring-sub">Last night</div></div>
  </div>
</div>

<div class="section-header">
  <span class="section-title">Today</span>
  <a href="{% url 'weekly_plan' %}" class="section-link">View full week →</a>
</div>

{% if not fitness_plan %}
<div class="card">
  <div class="content-card">
    <div class="card-icon" style="background:rgba(108,99,255,0.15)">📋</div>
    <div>
      <div class="card-title">No plan yet</div>
      <div class="card-sub">Generate your fitness and nutrition plan to get started.</div>
    </div>
  </div>
</div>
{% else %}
<div class="cards-list">
  <div class="card">
    <div class="content-card">
      <div class="card-icon" style="background:rgba(108,99,255,0.15)">🏋️</div>
      <div>
        <div class="card-title">{% if today_workout %}{{ today_workout.day_type|title }} · {{ today_workout.focus_area|title }}{% else %}Rest Day{% endif %}</div>
        <div class="card-sub">{% if today_workout %}{{ today_workout.estimated_duration_minutes }} min{% else %}Recovery &amp; mobility{% endif %}</div>
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
  <div class="card">
    <div class="content-card">
      <div class="card-icon" style="background:rgba(34,197,94,0.15)">🥗</div>
      <div>
        <div class="card-title">Today's Meals</div>
        <div class="card-sub">{{ today_meals|length }} meals{% if health_plan %} · {{ health_plan.daily_calorie_target }} kcal target{% endif %}</div>
      </div>
      <a href="{% url 'weekly_plan' %}" class="card-chevron">›</a>
    </div>
  </div>
</div>
{% endif %}

<div class="section-header">
  <span class="section-title">Wellness Check-in</span>
</div>
<div class="wellness-card">
  <div class="wellness-row">
    <div class="wellness-chip"><div class="wellness-icon">😴</div><div class="wellness-chip-lbl">Mood</div><div class="wellness-chip-val">{{ wellness_log.mood_score }}/10</div></div>
    <div class="wellness-chip"><div class="wellness-icon">⚡</div><div class="wellness-chip-lbl">Energy</div><div class="wellness-chip-val">{{ wellness_log.energy_level }}/10</div></div>
    <div class="wellness-chip"><div class="wellness-icon">😤</div><div class="wellness-chip-lbl">Stress</div><div class="wellness-chip-val">{{ wellness_log.stress_level }}/10</div></div>
    <div class="wellness-chip"><div class="wellness-icon">🌙</div><div class="wellness-chip-lbl">Sleep</div><div class="wellness-chip-val">{{ wellness_log.sleep_hours }}h</div></div>
  </div>
</div>

<div class="section-header">
  <span class="section-title">Weekly Progress</span>
  <span style="font-size:13px;font-weight:800;color:#a78bfa">{{ completed_days }} / {{ planned_days }} days</span>
</div>
<div class="card">
  <div class="progress-dots">
    {% for dot in progress_dots %}
      <div class="day-dot" style="background:{% if dot %}#6c63ff{% else %}#2a2a3e{% endif %}"></div>
    {% endfor %}
  </div>
</div>

{% endblock %}
```

- [ ] **Step 2: Run new dashboard tests**

```bash
pytest tests/test_dashboard/test_dashboard.py -v
```

Expected: All 9 tests PASS.

- [ ] **Step 3: Run full suite (excluding pre-existing broken test)**

```bash
pytest tests/ -v --ignore=tests/test_services/test_plan_generator.py 2>&1 | tail -20
```

Expected: All tests pass.

- [ ] **Step 4: Commit**

```bash
git add templates/dashboard/index.html
git commit -m "feat: redesign dashboard with dark UI, profile hero, and progress rings"
```

---

### Task 5: Restyle `templates/dashboard/weekly_plan.html`

**Files:**
- Modify: `templates/dashboard/weekly_plan.html`

- [ ] **Step 1: Run existing weekly plan tests as baseline**

```bash
pytest tests/test_dashboard/test_weekly_plan.py -v
```

Expected: All 6 tests PASS before any changes.

- [ ] **Step 2: Replace the entire contents of `templates/dashboard/weekly_plan.html`**

```html
{% extends "base_app.html" %}
{% block title %}Weekly Plan — Harmony{% endblock %}
{% block content %}

{% if not fitness_plan %}
  <h1 style="font-size:18px;font-weight:800;color:#fff;margin-bottom:8px;">Weekly Plan</h1>
  <p style="color:#555;">No active plan found. <a href="{% url 'dashboard' %}" style="color:#6c63ff;">Back to dashboard</a></p>
{% else %}

<div style="margin-bottom:16px;">
  <h1 style="font-size:18px;font-weight:800;color:#fff;margin-bottom:4px;">Week {{ fitness_plan.week_number }}</h1>
  <p style="font-size:12px;color:#555;">{{ fitness_plan.start_date }} – {{ fitness_plan.end_date }}</p>
</div>

<div class="card" style="margin-bottom:12px;">
  <div class="card-title">Weekly Goal</div>
  <p style="font-size:13px;color:#ccc;margin:6px 0 8px;">{{ fitness_plan.weekly_goal_summary }}</p>
  <div x-data="{ open: false }">
    <button @click="open = !open" type="button"
      style="background:rgba(108,99,255,0.15);border:1px solid rgba(108,99,255,0.25);color:#a78bfa;font-size:11px;font-weight:600;padding:5px 12px;border-radius:8px;cursor:pointer;">
      <span x-text="open ? 'Hide reasoning ▲' : 'Show reasoning ▼'"></span>
    </button>
    <div x-show="open" style="margin-top:10px;padding:10px 14px;background:rgba(108,99,255,0.08);border-left:3px solid #6c63ff;border-radius:0 8px 8px 0;font-size:12px;color:#ccc;">
      {{ fitness_plan.claude_reasoning }}
    </div>
  </div>
</div>

{% if health_plan %}
<div class="macro-strip">
  <span><strong>{{ health_plan.daily_calorie_target }}</strong> kcal</span>
  <span><strong>{{ health_plan.daily_protein_g }}g</strong> protein</span>
  <span><strong>{{ health_plan.daily_carbs_g }}g</strong> carbs</span>
  <span><strong>{{ health_plan.daily_fat_g }}g</strong> fat</span>
  <span><strong>{{ health_plan.daily_fiber_g }}g</strong> fiber</span>
  <span><strong>{{ health_plan.daily_water_ml }}ml</strong> water</span>
</div>
{% endif %}

<div x-data="{ activeDay: '{{ today_name }}' }">

  <div class="day-tabs">
    {% for day in days %}
    <button
      type="button"
      @click="activeDay = '{{ day.name }}'"
      class="day-tab"
      :style="activeDay === '{{ day.name }}' ? 'background:#6c63ff;color:#fff;border:none;' : 'background:#13131e;color:#555;border:1px solid #1c1c2e;'"
    >{{ day.short }}</button>
    {% endfor %}
  </div>

  {% for day in days %}
  <div x-show="activeDay === '{{ day.name }}'">

    <div class="section-header">
      <span class="section-title">{{ day.name }} — Workout</span>
    </div>

    {% if day.workout %}
    <div class="card" style="margin-bottom:10px;">
      <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:8px;">
        <div>
          <span style="font-size:13px;font-weight:700;color:#e0e0f0;">{{ day.workout.day_type|title }}</span>
          <span style="font-size:11px;color:#555;margin-left:8px;">{{ day.workout.focus_area|title }} · {{ day.workout.estimated_duration_minutes }} min</span>
        </div>
      </div>

      {% if day.workout.warmup_description %}
      <p style="font-size:12px;color:#888;margin-bottom:8px;"><strong style="color:#a78bfa;">Warmup:</strong> {{ day.workout.warmup_description }}</p>
      {% endif %}

      {% if day.workout.exercises.all %}
      <table class="exercise-table">
        <thead>
          <tr><th>Exercise</th><th>Section</th><th>Volume</th><th>Intensity</th><th>Notes</th></tr>
        </thead>
        <tbody>
          {% for ex in day.workout.exercises.all %}
          <tr>
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
      <div class="running-block">
        <strong>Running: {{ rs.run_type|title }}</strong> —
        {{ rs.total_distance_km }}km · {{ rs.total_duration_minutes }} min · Pace: {{ rs.pace_target }}
        {% if rs.heart_rate_zone %} · HR: {{ rs.heart_rate_zone }}{% endif %}
        {% if rs.notes %}<p style="margin:4px 0 0;">{{ rs.notes }}</p>{% endif %}
      </div>
      {% endif %}
      {% endwith %}

      {% if day.workout.cooldown_description %}
      <p style="font-size:12px;color:#888;margin-top:8px;"><strong style="color:#a78bfa;">Cooldown:</strong> {{ day.workout.cooldown_description }}</p>
      {% endif %}

      {% if day.workout.notes %}
      <p style="font-size:12px;color:#555;font-style:italic;margin-top:8px;">{{ day.workout.notes }}</p>
      {% endif %}
    </div>
    {% else %}
    <div class="card" style="margin-bottom:10px;">
      <p style="font-size:13px;color:#555;">Rest day.</p>
    </div>
    {% endif %}

    <div class="section-header">
      <span class="section-title">{{ day.name }} — Meals</span>
    </div>

    {% if day.meals %}
      {% for meal in day.meals %}
      <div class="card meal-card">
        <div class="meal-name">{{ meal.get_meal_type_display }}: {{ meal.meal_name }}</div>
        <div class="meal-desc">{{ meal.description }}</div>
        <div class="meal-macros">{{ meal.calories }} kcal · P: {{ meal.protein_g }}g · C: {{ meal.carbs_g }}g · F: {{ meal.fat_g }}g · Fiber: {{ meal.fiber_g }}g</div>
        {% if meal.ingredients %}<p style="font-size:11px;color:#555;margin-top:4px;">{{ meal.ingredients|join:", " }}</p>{% endif %}
        {% if meal.preparation_notes %}<p style="font-size:11px;color:#555;font-style:italic;margin-top:2px;">{{ meal.preparation_notes }}</p>{% endif %}
      </div>
      {% endfor %}
    {% else %}
      <div class="card"><p style="font-size:13px;color:#555;">No meals planned.</p></div>
    {% endif %}

  </div>
  {% endfor %}

</div>

{% endif %}

<p style="margin-top:20px;"><a href="{% url 'dashboard' %}" style="color:#6c63ff;font-size:13px;">← Back to Dashboard</a></p>

{% endblock %}
```

- [ ] **Step 3: Run existing weekly plan tests**

```bash
pytest tests/test_dashboard/test_weekly_plan.py -v
```

Expected: All 6 tests PASS.

- [ ] **Step 4: Commit**

```bash
git add templates/dashboard/weekly_plan.html
git commit -m "feat: restyle weekly plan page with dark UI"
```

---

### Task 6: Update `templates/accounts/profile_edit.html`

**Files:**
- Modify: `templates/accounts/profile_edit.html`

- [ ] **Step 1: Run existing profile edit tests as baseline**

```bash
pytest tests/test_accounts/test_profile_edit.py -v
```

Expected: All 22 tests PASS before any changes.

- [ ] **Step 2: Replace the entire contents of `templates/accounts/profile_edit.html`**

```html
{% extends "base_app.html" %}
{% block title %}Edit Profile — Harmony{% endblock %}
{% block content %}

{% if saved == "1" %}
<div class="save-banner">
  <span>Profile saved. Would you like to regenerate your fitness and nutrition plan with the updated information?</span>
  <div class="save-banner-actions">
    <form method="post" action="{% url 'regenerate_plan' %}" style="display:inline;">
      {% csrf_token %}
      <button type="submit" class="btn-primary">Yes, regenerate</button>
    </form>
    <a href="{% url 'dashboard' %}" class="btn-ghost">No, keep current</a>
  </div>
</div>
{% endif %}

<h1 class="form-page-title">Edit Profile</h1>
<p class="form-page-sub">Update your details to keep your plan accurate.</p>

<form method="post">
  {% csrf_token %}

  <div class="card form-section">
    <h2>Body Metrics</h2>
    <div class="form-field">{{ form.date_of_birth.label_tag }}{{ form.date_of_birth }}{{ form.date_of_birth.errors }}</div>
    <div class="form-field">{{ form.gender.label_tag }}{{ form.gender }}{{ form.gender.errors }}</div>
    <div class="form-field">{{ form.height_cm.label_tag }}{{ form.height_cm }}{{ form.height_cm.errors }}</div>
    <div class="form-field">{{ form.weight_kg.label_tag }}{{ form.weight_kg }}{{ form.weight_kg.errors }}</div>
  </div>

  <div class="card form-section">
    <h2>Goals &amp; Diet</h2>
    <div class="form-field">{{ form.primary_goal.label_tag }}{{ form.primary_goal }}{{ form.primary_goal.errors }}</div>
    <div class="form-field">{{ form.fitness_experience.label_tag }}{{ form.fitness_experience }}{{ form.fitness_experience.errors }}</div>
    <div class="form-field">{{ form.diet_type.label_tag }}{{ form.diet_type }}{{ form.diet_type.errors }}</div>
    <div class="form-field">{{ form.food_preferences.label_tag }}{{ form.food_preferences }}{{ form.food_preferences.errors }}</div>
    <div class="form-field">{{ form.food_allergies.label_tag }}{{ form.food_allergies }}{{ form.food_allergies.errors }}</div>
  </div>

  <div class="card form-section">
    <h2>Schedule</h2>
    <div class="form-field">{{ form.daily_routine.label_tag }}{{ form.daily_routine }}{{ form.daily_routine.errors }}</div>
    <div class="form-field">{{ form.wake_time.label_tag }}{{ form.wake_time }}{{ form.wake_time.errors }}</div>
    <div class="form-field">{{ form.sleep_time.label_tag }}{{ form.sleep_time }}{{ form.sleep_time.errors }}</div>
    <div class="form-field">{{ form.work_schedule.label_tag }}{{ form.work_schedule }}{{ form.work_schedule.errors }}</div>
  </div>

  <div class="card form-section">
    <h2>Workout Preferences</h2>
    <div class="form-field">{{ form.workout_days_per_week.label_tag }}{{ form.workout_days_per_week }}{{ form.workout_days_per_week.errors }}</div>
    <div class="form-field">{{ form.preferred_workout_days.label_tag }}{{ form.preferred_workout_days }}{{ form.preferred_workout_days.errors }}</div>
    <div class="form-field">{{ form.running_days_per_week.label_tag }}{{ form.running_days_per_week }}{{ form.running_days_per_week.errors }}</div>
    <div class="form-field">{{ form.workout_location.label_tag }}{{ form.workout_location }}{{ form.workout_location.errors }}</div>
    <div class="form-field">{{ form.available_equipment.label_tag }}{{ form.available_equipment }}{{ form.available_equipment.errors }}</div>
  </div>

  <div class="card form-section">
    <h2>Health</h2>
    <div class="form-field">{{ form.injury_history.label_tag }}{{ form.injury_history }}{{ form.injury_history.errors }}</div>
    <div class="form-field">{{ form.medical_conditions.label_tag }}{{ form.medical_conditions }}{{ form.medical_conditions.errors }}</div>
  </div>

  <div class="card form-section">
    <h2>Notifications</h2>
    <div class="form-field">{{ form.notification_email.label_tag }}{{ form.notification_email }}{{ form.notification_email.errors }}</div>
    <div class="form-field">{{ form.notification_time.label_tag }}{{ form.notification_time }}{{ form.notification_time.errors }}</div>
  </div>

  <button type="submit" class="submit-btn">Save Profile</button>
</form>

{% endblock %}
```

- [ ] **Step 3: Run profile edit tests**

```bash
pytest tests/test_accounts/test_profile_edit.py -v
```

Expected: All 22 tests PASS.

- [ ] **Step 4: Run the full test suite**

```bash
pytest tests/ -v --ignore=tests/test_services/test_plan_generator.py 2>&1 | tail -20
```

Expected: All tests pass. The only excluded file (`test_plan_generator.py`) has a pre-existing failure unrelated to this feature.

- [ ] **Step 5: Commit**

```bash
git add templates/accounts/profile_edit.html
git commit -m "feat: restyle profile edit page with dark UI"
```
