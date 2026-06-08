# Profile Edit Page — Design Spec

**Date:** 2026-06-08
**Status:** Approved

## Overview

A single-page form at `/accounts/profile/edit/` that lets users update their `UserProfile` with all fields pre-filled. After saving, a confirmation prompt asks whether to regenerate the fitness/nutrition plan.

## URL & Routing

- URL: `/accounts/profile/edit/`
- View name: `profile_edit`
- Defined in: `apps/accounts/urls.py`
- View function: `apps/accounts/views.py`
- Template: `templates/accounts/profile_edit.html`
- Access: `login_required`

## Form

A new `ProfileEditForm(ModelForm)` in `apps/accounts/forms.py` covering all editable `UserProfile` fields:

- **Body Metrics:** height_cm, weight_kg, gender, date_of_birth
- **Goals & Diet:** fitness_experience, primary_goal, diet_type, food_allergies, food_preferences
- **Schedule:** daily_routine, wake_time, sleep_time, work_schedule
- **Workout Preferences:** workout_days_per_week, preferred_workout_days, running_days_per_week, workout_location, available_equipment
- **Health:** injury_history, medical_conditions
- **Notifications:** notification_email

Fields excluded from the form: `user`, `onboarding_completed`, `additional_comments`.

The form is initialised with the user's current `UserProfile` instance so all fields are pre-filled on GET.

## POST Flow

1. Validate form — if invalid, re-render with errors
2. Save profile
3. Redirect to `/accounts/profile/edit/?saved=1` — the template detects `saved=1` in the query string and shows a confirmation banner:
   > "Profile saved. Would you like to regenerate your fitness and nutrition plan with the updated information?"
   > **[Yes, regenerate]** · **[No, keep current plan]**
4. "Yes" → POST to a new `regenerate_plan` view that resets `onboarding_completed = False`, fires `generate_plan_task`, redirects to `/accounts/onboarding/generating/`
5. "No" → redirect to `/dashboard/`

## New Views

### `profile_edit` (GET + POST)
- GET: render form pre-filled with current profile
- POST: validate and save, redirect to `?saved=1`

### `regenerate_plan` (POST only)
- Resets `onboarding_completed = False`
- Fires `generate_plan_task(user.id)`
- Redirects to `onboarding_generating`

## Dashboard Link

Add an "Edit Profile" link to the dashboard nav or Weekly Progress section pointing to `profile_edit`.

## Styling

Follows existing conventions — grouped sections with `<h2>` headings, plain HTML inputs, existing `main.css` button style.

## Out of Scope

- Changing username or password (separate Django auth flow)
- Partial/per-section saves
- Live preview of plan impact
