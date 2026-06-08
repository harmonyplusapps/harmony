# Weekly Plan View — Design Spec

**Date:** 2026-06-08
**Status:** Approved

## Overview

A dedicated page at `/dashboard/plan/` showing the user's full 7-day fitness and nutrition plan with day tabs, weekly summary, and Claude's reasoning.

## URL & Routing

- URL: `/dashboard/plan/`
- View name: `weekly_plan`
- Defined in: `apps/dashboard/urls.py`
- View function: `apps/dashboard/views.py`
- Template: `templates/dashboard/weekly_plan.html`
- Access: `login_required`, redirects to onboarding if not completed

## Data

The view fetches:

1. **FitnessPlan** — active plan for the user, with all `WorkoutDay`s prefetched including `exercises__exercise_cache` and `running_strategy`
2. **HealthPlan** — active plan for the user, with all `MealPlan`s grouped into a dict keyed by `day_of_week` (e.g. `{"Monday": [...], "Tuesday": [...]}`)
3. **Today's date** — used to highlight the current day's tab by default

If no active plan exists, the page shows a message with a link back to the dashboard.

## Template Structure

### Header
- Week number and date range (e.g. "Week 1 · Jun 8 – Jun 14")
- Weekly goal summary (full text)
- Claude's reasoning — collapsed by default, expandable via a toggle button

### Day Tabs
- 7 tab buttons: Mon, Tue, Wed, Thu, Fri, Sat, Sun
- Today's tab is active/highlighted by default
- Tab switching via plain JS toggling `display:none/block` — all data is rendered server-side, no HTMX needed

### Tab Content (per day)
Each day panel contains two sections:

**Workout section:**
- Day type badge (Strength / Running / Yoga / Active Recovery / Rest)
- Focus area and estimated duration
- Warmup description (if present)
- Exercise list: name, section, sets × reps or duration, intensity, notes
- Running strategy (if present): run type, distance, duration, pace target, heart rate zone, structure
- Cooldown description (if present)
- Day notes (if present)

**Meals section:**
- Each meal card: meal type label, meal name, description, macros (calories, protein, carbs, fat, fiber), ingredients, preparation notes

### Footer
- "← Back to Dashboard" link

## Dashboard Link

A "View Full Week →" link added to the dashboard's Weekly Progress section pointing to `weekly_plan`.

## Styling

Follows existing conventions in `base.html` and `static/css/main.css` — plain HTML with minimal inline structure, no new CSS framework.

## Out of Scope

- Editing or regenerating the plan from this page
- Logging workouts or meals from this page (done from dashboard)
- Nutrition plan weekly summary / Claude reasoning (only fitness plan has this in the current model)
