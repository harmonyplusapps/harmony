# Profile Edit Page Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a `/accounts/profile/edit/` page where logged-in users can update all their `UserProfile` fields, with a post-save prompt to optionally regenerate their fitness/nutrition plan.

**Architecture:** A `ProfileEditForm(ModelForm)` covering all editable fields (with custom handling for three JSONFields), a `profile_edit` view (GET pre-fills form, POST saves and redirects `?saved=1`), a `regenerate_plan` view (POST-only, resets `onboarding_completed=False` and redirects to the existing `onboarding_generating` page), and a template that renders grouped sections and the post-save confirmation banner.

**Tech Stack:** Django 5.1, pytest-django, existing `main.css` styles, existing `conftest.py` fixtures

---

## File Map

| Action | File | Responsibility |
|--------|------|---------------|
| Modify | `apps/accounts/forms.py` | Add `ProfileEditForm` with JSONField handling |
| Modify | `apps/accounts/views.py` | Add `profile_edit` and `regenerate_plan` views |
| Modify | `apps/accounts/urls.py` | Add two URL entries |
| Create | `templates/accounts/profile_edit.html` | Form template with grouped sections + banner |
| Modify | `templates/dashboard/index.html` | Add "Edit Profile" link |
| Create | `tests/test_accounts/test_profile_edit.py` | Tests for form and views |

---

### Task 1: ProfileEditForm

**Files:**
- Modify: `apps/accounts/forms.py`
- Test: `tests/test_accounts/test_profile_edit.py`

- [ ] **Step 1: Write failing tests for the form**

Create `tests/test_accounts/test_profile_edit.py`:

```python
import pytest
from datetime import date
from apps.accounts.forms import ProfileEditForm
from apps.accounts.models import UserProfile
from django.contrib.auth.models import User


@pytest.fixture
def profile_with_json(db):
    user = User.objects.create_user(username="edituser", password="pass")
    return UserProfile.objects.create(
        user=user,
        height_cm=170, weight_kg=70, gender="female",
        date_of_birth=date(1995, 3, 10),
        fitness_experience="beginner",
        primary_goal="Lose weight",
        diet_type="vegan",
        food_allergies=["gluten", "dairy"],
        food_preferences="Low oil",
        daily_routine="Work from home",
        wake_time="07:00", sleep_time="23:00",
        work_schedule="flexible",
        workout_days_per_week=4,
        preferred_workout_days=["Monday", "Wednesday", "Friday", "Sunday"],
        running_days_per_week=1,
        workout_location="home",
        available_equipment=["resistance bands", "dumbbells"],
        injury_history="Left knee strain",
        medical_conditions="",
        notification_email="edit@example.com",
        onboarding_completed=True,
    )


@pytest.mark.django_db
def test_form_pre_fills_preferred_workout_days(profile_with_json):
    form = ProfileEditForm(instance=profile_with_json)
    assert form.initial["preferred_workout_days"] == ["Monday", "Wednesday", "Friday", "Sunday"]


@pytest.mark.django_db
def test_form_pre_fills_available_equipment(profile_with_json):
    form = ProfileEditForm(instance=profile_with_json)
    assert form.initial["available_equipment"] == "resistance bands, dumbbells"


@pytest.mark.django_db
def test_form_pre_fills_food_allergies(profile_with_json):
    form = ProfileEditForm(instance=profile_with_json)
    assert form.initial["food_allergies"] == "gluten, dairy"


@pytest.mark.django_db
def test_form_clean_available_equipment_returns_list(profile_with_json):
    data = {
        "height_cm": "170", "weight_kg": "70", "gender": "female",
        "date_of_birth": "1995-03-10", "fitness_experience": "beginner",
        "primary_goal": "Lose weight", "diet_type": "vegan",
        "food_allergies": "nuts",
        "food_preferences": "", "daily_routine": "",
        "wake_time": "07:00", "sleep_time": "23:00",
        "work_schedule": "flexible",
        "workout_days_per_week": "4",
        "preferred_workout_days": ["Monday", "Wednesday"],
        "running_days_per_week": "1",
        "workout_location": "home",
        "available_equipment": "dumbbells, kettlebell",
        "injury_history": "", "medical_conditions": "",
        "notification_email": "edit@example.com",
    }
    form = ProfileEditForm(data, instance=profile_with_json)
    assert form.is_valid(), form.errors
    assert form.cleaned_data["available_equipment"] == ["dumbbells", "kettlebell"]


@pytest.mark.django_db
def test_form_clean_food_allergies_returns_list(profile_with_json):
    data = {
        "height_cm": "170", "weight_kg": "70", "gender": "female",
        "date_of_birth": "1995-03-10", "fitness_experience": "beginner",
        "primary_goal": "Lose weight", "diet_type": "vegan",
        "food_allergies": "gluten, soy",
        "food_preferences": "", "daily_routine": "",
        "wake_time": "07:00", "sleep_time": "23:00",
        "work_schedule": "flexible",
        "workout_days_per_week": "4",
        "preferred_workout_days": ["Monday"],
        "running_days_per_week": "1",
        "workout_location": "home",
        "available_equipment": "",
        "injury_history": "", "medical_conditions": "",
        "notification_email": "edit@example.com",
    }
    form = ProfileEditForm(data, instance=profile_with_json)
    assert form.is_valid(), form.errors
    assert form.cleaned_data["food_allergies"] == ["gluten", "soy"]


@pytest.mark.django_db
def test_form_empty_equipment_returns_empty_list(profile_with_json):
    data = {
        "height_cm": "170", "weight_kg": "70", "gender": "female",
        "date_of_birth": "1995-03-10", "fitness_experience": "beginner",
        "primary_goal": "Lose weight", "diet_type": "vegan",
        "food_allergies": "",
        "food_preferences": "", "daily_routine": "",
        "wake_time": "07:00", "sleep_time": "23:00",
        "work_schedule": "flexible",
        "workout_days_per_week": "4",
        "preferred_workout_days": ["Monday"],
        "running_days_per_week": "1",
        "workout_location": "home",
        "available_equipment": "",
        "injury_history": "", "medical_conditions": "",
        "notification_email": "edit@example.com",
    }
    form = ProfileEditForm(data, instance=profile_with_json)
    assert form.is_valid(), form.errors
    assert form.cleaned_data["available_equipment"] == []
```

- [ ] **Step 2: Run tests to confirm they fail**

```bash
cd /Users/sreelekhapotluri/Desktop/Harmony && source .venv/bin/activate && pytest tests/test_accounts/test_profile_edit.py -v
```

Expected: FAIL with `ImportError: cannot import name 'ProfileEditForm'`

- [ ] **Step 3: Add ProfileEditForm to apps/accounts/forms.py**

Append after `OnboardingStep3Form` in `apps/accounts/forms.py`:

```python
class ProfileEditForm(forms.ModelForm):
    preferred_workout_days = forms.MultipleChoiceField(
        choices=[(d, d) for d in ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]],
        widget=forms.CheckboxSelectMultiple,
    )
    available_equipment = forms.CharField(
        required=False,
        help_text="Comma-separated, e.g. dumbbells, resistance bands",
        widget=forms.TextInput,
    )
    food_allergies = forms.CharField(
        required=False,
        help_text="Comma-separated, e.g. gluten, dairy",
        widget=forms.TextInput,
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if self.instance and self.instance.pk:
            self.initial["preferred_workout_days"] = self.instance.preferred_workout_days
            self.initial["available_equipment"] = ", ".join(self.instance.available_equipment or [])
            self.initial["food_allergies"] = ", ".join(self.instance.food_allergies or [])

    def clean_available_equipment(self):
        val = self.cleaned_data.get("available_equipment", "")
        return [v.strip() for v in val.split(",") if v.strip()]

    def clean_food_allergies(self):
        val = self.cleaned_data.get("food_allergies", "")
        return [v.strip() for v in val.split(",") if v.strip()]

    class Meta:
        model = UserProfile
        fields = [
            "height_cm", "weight_kg", "gender", "date_of_birth",
            "fitness_experience", "primary_goal",
            "diet_type", "food_allergies", "food_preferences",
            "daily_routine", "wake_time", "sleep_time", "work_schedule",
            "workout_days_per_week", "preferred_workout_days", "running_days_per_week",
            "workout_location", "available_equipment",
            "injury_history", "medical_conditions",
            "notification_email",
        ]
        widgets = {
            "date_of_birth": forms.DateInput(attrs={"type": "date"}),
            "wake_time": forms.TimeInput(attrs={"type": "time"}),
            "sleep_time": forms.TimeInput(attrs={"type": "time"}),
        }
```

- [ ] **Step 4: Run tests to confirm they pass**

```bash
cd /Users/sreelekhapotluri/Desktop/Harmony && source .venv/bin/activate && pytest tests/test_accounts/test_profile_edit.py -v
```

Expected: 6 tests PASS

- [ ] **Step 5: Commit**

```bash
git add apps/accounts/forms.py tests/test_accounts/test_profile_edit.py
git commit -m "feat: add ProfileEditForm with JSONField pre-filling"
```

---

### Task 2: profile_edit and regenerate_plan views

**Files:**
- Modify: `apps/accounts/views.py`
- Test: `tests/test_accounts/test_profile_edit.py`

- [ ] **Step 1: Write failing tests for the views**

Append to `tests/test_accounts/test_profile_edit.py`:

```python
from django.urls import reverse


@pytest.mark.django_db
def test_profile_edit_get_requires_login(client):
    resp = client.get(reverse("profile_edit"))
    assert resp.status_code == 302
    assert "login" in resp["Location"]


@pytest.mark.django_db
def test_profile_edit_get_renders_form_with_prefill(client, profile_with_json):
    client.login(username="edituser", password="pass")
    resp = client.get(reverse("profile_edit"))
    assert resp.status_code == 200
    content = resp.content.decode()
    assert "170" in content  # height pre-filled
    assert "gluten, dairy" in content  # food_allergies pre-filled
    assert "resistance bands, dumbbells" in content  # available_equipment pre-filled


@pytest.mark.django_db
def test_profile_edit_post_saves_and_redirects(client, profile_with_json):
    client.login(username="edituser", password="pass")
    resp = client.post(reverse("profile_edit"), {
        "height_cm": "172",
        "weight_kg": "68",
        "gender": "female",
        "date_of_birth": "1995-03-10",
        "fitness_experience": "intermediate",
        "primary_goal": "Build endurance",
        "diet_type": "vegan",
        "food_allergies": "nuts",
        "food_preferences": "",
        "daily_routine": "",
        "wake_time": "07:00",
        "sleep_time": "23:00",
        "work_schedule": "flexible",
        "workout_days_per_week": "5",
        "preferred_workout_days": ["Monday", "Tuesday"],
        "running_days_per_week": "2",
        "workout_location": "gym",
        "available_equipment": "barbell",
        "injury_history": "",
        "medical_conditions": "",
        "notification_email": "edit@example.com",
    })
    assert resp.status_code == 302
    assert "saved=1" in resp["Location"]
    profile_with_json.refresh_from_db()
    assert float(profile_with_json.height_cm) == 172.0
    assert profile_with_json.available_equipment == ["barbell"]
    assert profile_with_json.food_allergies == ["nuts"]
    assert profile_with_json.preferred_workout_days == ["Monday", "Tuesday"]


@pytest.mark.django_db
def test_profile_edit_get_shows_banner_when_saved(client, profile_with_json):
    client.login(username="edituser", password="pass")
    resp = client.get(reverse("profile_edit") + "?saved=1")
    assert resp.status_code == 200
    assert "Would you like to regenerate" in resp.content.decode()


@pytest.mark.django_db
def test_regenerate_plan_requires_login(client):
    resp = client.post(reverse("regenerate_plan"))
    assert resp.status_code == 302
    assert "login" in resp["Location"]


@pytest.mark.django_db
def test_regenerate_plan_resets_onboarding_and_redirects(client, profile_with_json):
    client.login(username="edituser", password="pass")
    resp = client.post(reverse("regenerate_plan"))
    assert resp.status_code == 302
    assert "generating" in resp["Location"]
    profile_with_json.refresh_from_db()
    assert profile_with_json.onboarding_completed is False
```

- [ ] **Step 2: Run tests to confirm they fail**

```bash
cd /Users/sreelekhapotluri/Desktop/Harmony && source .venv/bin/activate && pytest tests/test_accounts/test_profile_edit.py::test_profile_edit_get_requires_login tests/test_accounts/test_profile_edit.py::test_regenerate_plan_requires_login -v
```

Expected: FAIL with `NoReverseMatch: Reverse for 'profile_edit' not found`

- [ ] **Step 3: Add profile_edit and regenerate_plan to apps/accounts/views.py**

At the top of `apps/accounts/views.py`, update the imports line:

```python
from .forms import RegisterForm, OnboardingStep1Form, OnboardingStep2Form, OnboardingStep3Form, ProfileEditForm
```

Then append after `onboarding_generating` at the bottom of `apps/accounts/views.py`:

```python
@login_required
def profile_edit(request):
    profile = get_object_or_404(UserProfile, user=request.user)
    if request.method == "POST":
        form = ProfileEditForm(request.POST, instance=profile)
        if form.is_valid():
            obj = form.save(commit=False)
            obj.preferred_workout_days = form.cleaned_data["preferred_workout_days"]
            obj.food_allergies = form.cleaned_data["food_allergies"]
            obj.available_equipment = form.cleaned_data["available_equipment"]
            obj.save()
            return redirect(reverse("profile_edit") + "?saved=1")
    else:
        form = ProfileEditForm(instance=profile)
    return render(request, "accounts/profile_edit.html", {"form": form})


@login_required
@require_POST
def regenerate_plan(request):
    profile = get_object_or_404(UserProfile, user=request.user)
    profile.onboarding_completed = False
    profile.save()
    return redirect("onboarding_generating")
```

Also add `reverse` to the django.shortcuts import at the top:

```python
from django.shortcuts import render, redirect, get_object_or_404, reverse
```

- [ ] **Step 4: Run all view tests to confirm they pass**

```bash
cd /Users/sreelekhapotluri/Desktop/Harmony && source .venv/bin/activate && pytest tests/test_accounts/test_profile_edit.py -v
```

Expected: All 12 tests PASS (Note: the banner test and regenerate redirect test will fail until URLs and template are added in the next tasks — that's expected at this step. The 6 form tests + 2 redirect/login tests should pass.)

- [ ] **Step 5: Commit**

```bash
git add apps/accounts/views.py tests/test_accounts/test_profile_edit.py
git commit -m "feat: add profile_edit and regenerate_plan views"
```

---

### Task 3: URL entries

**Files:**
- Modify: `apps/accounts/urls.py`

- [ ] **Step 1: Add URL patterns to apps/accounts/urls.py**

```python
from django.urls import path
from . import views

urlpatterns = [
    path("login/", views.login_view, name="login"),
    path("logout/", views.logout_view, name="logout"),
    path("register/", views.register_view, name="register"),
    path("onboarding/1/", views.onboarding_step1, name="onboarding_step1"),
    path("onboarding/2/", views.onboarding_step2, name="onboarding_step2"),
    path("onboarding/3/", views.onboarding_step3, name="onboarding_step3"),
    path("onboarding/generating/", views.onboarding_generating, name="onboarding_generating"),
    path("profile/edit/", views.profile_edit, name="profile_edit"),
    path("profile/regenerate/", views.regenerate_plan, name="regenerate_plan"),
]
```

- [ ] **Step 2: Run the full test suite to confirm no regressions**

```bash
cd /Users/sreelekhapotluri/Desktop/Harmony && source .venv/bin/activate && pytest tests/test_accounts/ -v
```

Expected: All account tests pass (the 6 form tests and the login/redirect/login tests in test_profile_edit.py that don't depend on the template)

- [ ] **Step 3: Commit**

```bash
git add apps/accounts/urls.py
git commit -m "feat: add profile/edit/ and profile/regenerate/ URL routes"
```

---

### Task 4: Profile edit template

**Files:**
- Create: `templates/accounts/profile_edit.html`

- [ ] **Step 1: Create the template**

```html
{% extends "base.html" %}
{% block title %}Edit Profile — Harmony{% endblock %}
{% block content %}
<h1>Edit Profile</h1>

{% if request.GET.saved %}
<div class="banner">
  <p>Profile saved. Would you like to regenerate your fitness and nutrition plan with the updated information?</p>
  <form method="post" action="{% url 'regenerate_plan' %}" style="display:inline">
    {% csrf_token %}
    <button type="submit">Yes, regenerate</button>
  </form>
  <a href="{% url 'dashboard' %}">No, keep current plan</a>
</div>
{% endif %}

<form method="post">
  {% csrf_token %}

  <h2>Body Metrics</h2>
  <p>{{ form.height_cm.label_tag }} {{ form.height_cm }} {{ form.height_cm.errors }}</p>
  <p>{{ form.weight_kg.label_tag }} {{ form.weight_kg }} {{ form.weight_kg.errors }}</p>
  <p>{{ form.gender.label_tag }} {{ form.gender }} {{ form.gender.errors }}</p>
  <p>{{ form.date_of_birth.label_tag }} {{ form.date_of_birth }} {{ form.date_of_birth.errors }}</p>

  <h2>Goals &amp; Diet</h2>
  <p>{{ form.fitness_experience.label_tag }} {{ form.fitness_experience }} {{ form.fitness_experience.errors }}</p>
  <p>{{ form.primary_goal.label_tag }} {{ form.primary_goal }} {{ form.primary_goal.errors }}</p>
  <p>{{ form.diet_type.label_tag }} {{ form.diet_type }} {{ form.diet_type.errors }}</p>
  <p>{{ form.food_allergies.label_tag }} {{ form.food_allergies }} {{ form.food_allergies.errors }}</p>
  <p>{{ form.food_preferences.label_tag }} {{ form.food_preferences }} {{ form.food_preferences.errors }}</p>

  <h2>Schedule</h2>
  <p>{{ form.daily_routine.label_tag }} {{ form.daily_routine }} {{ form.daily_routine.errors }}</p>
  <p>{{ form.wake_time.label_tag }} {{ form.wake_time }} {{ form.wake_time.errors }}</p>
  <p>{{ form.sleep_time.label_tag }} {{ form.sleep_time }} {{ form.sleep_time.errors }}</p>
  <p>{{ form.work_schedule.label_tag }} {{ form.work_schedule }} {{ form.work_schedule.errors }}</p>

  <h2>Workout Preferences</h2>
  <p>{{ form.workout_days_per_week.label_tag }} {{ form.workout_days_per_week }} {{ form.workout_days_per_week.errors }}</p>
  <p>{{ form.preferred_workout_days.label_tag }} {{ form.preferred_workout_days }} {{ form.preferred_workout_days.errors }}</p>
  <p>{{ form.running_days_per_week.label_tag }} {{ form.running_days_per_week }} {{ form.running_days_per_week.errors }}</p>
  <p>{{ form.workout_location.label_tag }} {{ form.workout_location }} {{ form.workout_location.errors }}</p>
  <p>{{ form.available_equipment.label_tag }} {{ form.available_equipment }} {{ form.available_equipment.errors }}</p>

  <h2>Health</h2>
  <p>{{ form.injury_history.label_tag }} {{ form.injury_history }} {{ form.injury_history.errors }}</p>
  <p>{{ form.medical_conditions.label_tag }} {{ form.medical_conditions }} {{ form.medical_conditions.errors }}</p>

  <h2>Notifications</h2>
  <p>{{ form.notification_email.label_tag }} {{ form.notification_email }} {{ form.notification_email.errors }}</p>

  <button type="submit">Save Profile</button>
</form>
{% endblock %}
```

- [ ] **Step 2: Run the full profile_edit test suite**

```bash
cd /Users/sreelekhapotluri/Desktop/Harmony && source .venv/bin/activate && pytest tests/test_accounts/test_profile_edit.py -v
```

Expected: All 12 tests PASS

- [ ] **Step 3: Commit**

```bash
git add templates/accounts/profile_edit.html
git commit -m "feat: add profile edit template with grouped sections and save banner"
```

---

### Task 5: Dashboard "Edit Profile" link

**Files:**
- Modify: `templates/dashboard/index.html`

- [ ] **Step 1: Write a failing test**

Append to `tests/test_accounts/test_profile_edit.py`:

```python
@pytest.mark.django_db
def test_dashboard_has_edit_profile_link(client, base_user, complete_profile):
    client.login(username="base", password="testpass123")
    resp = client.get(reverse("dashboard"))
    assert resp.status_code == 200
    assert "/accounts/profile/edit/" in resp.content.decode()
```

- [ ] **Step 2: Run the test to confirm it fails**

```bash
cd /Users/sreelekhapotluri/Desktop/Harmony && source .venv/bin/activate && pytest tests/test_accounts/test_profile_edit.py::test_dashboard_has_edit_profile_link -v
```

Expected: FAIL with assertion error (link not present)

- [ ] **Step 3: Add Edit Profile link to templates/dashboard/index.html**

In `templates/dashboard/index.html`, update the `Weekly Progress` section to include the link (and add a separate Edit Profile link below the weekly plan link):

```html
{% extends "base.html" %}
{% block title %}Dashboard — Harmony{% endblock %}
{% block content %}
<h1>Welcome, {{ request.user.first_name|default:request.user.username }}!</h1>

<section>
  <h2>Today's Workout</h2>
  {% include "dashboard/partials/workout_today.html" %}
</section>

<section>
  <h2>Today's Meals</h2>
  {% include "dashboard/partials/meal_today.html" %}
</section>

<section>
  <h2>Wellness Check-in</h2>
  {% include "dashboard/partials/wellness_checkin.html" %}
</section>

<section>
  <h2>Weekly Progress</h2>
  <p>{{ completed_days }} / {{ planned_days }} workout days completed this week.</p>
  <a href="{% url 'weekly_plan' %}">View Full Week →</a>
  &nbsp;·&nbsp;
  <a href="{% url 'profile_edit' %}">Edit Profile</a>
</section>
{% endblock %}
```

- [ ] **Step 4: Run the test to confirm it passes**

```bash
cd /Users/sreelekhapotluri/Desktop/Harmony && source .venv/bin/activate && pytest tests/test_accounts/test_profile_edit.py::test_dashboard_has_edit_profile_link -v
```

Expected: PASS

- [ ] **Step 5: Run the full test suite to check for regressions**

```bash
cd /Users/sreelekhapotluri/Desktop/Harmony && source .venv/bin/activate && pytest -v
```

Expected: All tests pass

- [ ] **Step 6: Commit**

```bash
git add templates/dashboard/index.html tests/test_accounts/test_profile_edit.py
git commit -m "feat: add Edit Profile link to dashboard"
```

---

## Spec Coverage Check

- ✅ URL `/accounts/profile/edit/` → Task 3
- ✅ View name `profile_edit` → Task 3
- ✅ `ProfileEditForm(ModelForm)` with all editable fields → Task 1
- ✅ Excluded: `user`, `onboarding_completed`, `additional_comments` → Task 1
- ✅ Form pre-filled on GET → Task 2 (view), Task 1 (form `__init__`)
- ✅ POST validates, saves, redirects `?saved=1` → Task 2
- ✅ `saved=1` banner with Yes/No → Task 4
- ✅ `regenerate_plan` view resets `onboarding_completed=False`, redirects to `onboarding_generating` → Task 2
- ✅ URL `profile/regenerate/` → Task 3
- ✅ Dashboard "Edit Profile" link → Task 5
- ✅ Grouped sections with `<h2>` headings → Task 4
- ✅ `login_required` on both views → Task 2
