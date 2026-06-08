# Dashboard UI Redesign Design

## Goal

Replace the plain white dashboard with a dark, health-app-inspired UI — adding a persistent sidebar, a branded header with logo, and a rich profile hero on the dashboard homepage.

## Architecture

Introduce `base_app.html` as the base template for all authenticated pages (dashboard, weekly plan, profile edit). Login, register, and onboarding pages keep the existing `base.html`. All new styles go in a new `static/css/app.css`; `main.css` is kept intact for unauthenticated pages.

The sidebar and header are rendered once in `base_app.html`. Active nav state is detected via `request.resolver_match.url_name` in the template.

## Color Palette

| Token | Value | Use |
|---|---|---|
| `--bg` | `#090912` | Page background |
| `--surface` | `#0f0f1a` | Main content area |
| `--card` | `#13131e` | Cards, sidebar |
| `--border` | `#1c1c2e` | Card borders |
| `--accent` | `#6c63ff` | Primary purple |
| `--accent-light` | `#a78bfa` | Text accents, gradients |
| `--green` | `#22c55e` | Sleep, success |
| `--green-light` | `#4ade80` | Sleep text |
| `--orange` | `#f97316` | Calories |
| `--text` | `#e0e0f0` | Body text |
| `--muted` | `#555` | Labels, secondary |

## Components

### Header (56px, full-width)

Background `#090912`, border-bottom `#1c1c2e`. Left side: Option C logo SVG + stacked wordmark. Right side: notification bell icon.

**Logo SVG** (36×36): dark tile `#1a1a2e`, rx 10. Two thin outline stems (stroke `url(#grad)`, width 2.5). Horizontal crossbar (stroke `url(#grad)`, width 3, linecap round). Gradient accent dot (r=3, fill `url(#grad)`) at crossbar centre. Gradient: `#a78bfa` → `#6c63ff`.

**Wordmark** (stacked, left of logo):
- Line 1: "Harmony" — 18px, weight 800, letter-spacing -0.03em, gradient `white 50% → #a78bfa` (CSS background-clip text)
- Line 2: "Your fitness companion" — 8px, weight 500, letter-spacing 0.12em, uppercase, color `#444`

### Sidebar (64px wide, full-height)

Background `#0d0d16`, border-right `#1a1a28`. Icon-only nav items (44×44px, border-radius 12px):

| Slot | Icon | URL name |
|---|---|---|
| Dashboard | 🏠 | `dashboard` |
| Weekly Plan | 📅 | `weekly_plan` |
| Profile | 👤 | `profile_edit` |
| *(spacer)* | — | — |
| Logout | 🚪 | POST `logout` |

Active item: background `rgba(108,99,255,0.18)`, color `#a78bfa`, left accent bar 3px wide `#6c63ff` at left edge.

### Dashboard — Profile Hero Card

Full-width card below topbar. Gradient background `135deg, #12082a → #0d1a3f`. Border `rgba(108,99,255,0.15)`. Radial glow overlay (top-right, `rgba(108,99,255,0.12)`).

Contents (flex row):
- Avatar: 48×48px rounded-14, gradient fill `#6c63ff → #a78bfa`, first letter of username, 20px weight 800
- Info block (flex: 1):
  - Name: `request.user.get_full_name|default:request.user.username`, 17px weight 800
  - Goal: `profile.primary_goal`, 11px color `#a78bfa`
  - Stats row: weight_kg, height_cm, workout_location, fitness_experience — each a `pstat` (value 14px weight 800, label 9px uppercase muted)
- "Edit Profile" button (right): links to `profile_edit`

### Dashboard — Daily Progress Rings (3-up grid)

Three equal-width cards, each with a coloured ring (38px, border 3px) + label:

| Ring | Value | Color |
|---|---|---|
| Workouts | `completed_days / planned_days` | `#6c63ff` / `#a78bfa` |
| Calories | `health_plan.daily_calorie_target` (target, not tracked) | `#f97316` / `#fb923c` |
| Sleep | `wellness_log.sleep_hours`h | `#22c55e` / `#4ade80` |

If `planned_days` is 0 or no plan, show `0/0`.

### Dashboard — Today's Cards

Section header "Today" + "View full week →" link to `weekly_plan`.

Two content cards:
1. **Workout card**: icon 🏋️ (purple bg), title from `today_workout.day_type` + focus area, sub `estimated_duration_minutes min`, badge "Pending" or "Done" depending on `workout_log.completed`.
2. **Meals card**: icon 🥗 (green bg), title "Today's Meals", sub `{meal count} meals · {daily_calorie_target} kcal target`, chevron linking to `weekly_plan`.

If no plan: show a single placeholder card "No plan yet — generate your plan."

### Dashboard — Wellness Check-in

Four chips (mood_score, energy_level, stress_level, sleep_hours) pulled from `wellness_log`. Chip: small icon + label (9px uppercase) + value (12px weight 700 green). Container: green-tinted gradient card.

### Dashboard — Weekly Progress Bar

7 equal-width dots (6px height, border-radius 3px). Filled purple `#6c63ff` for completed days, dark `#2a2a3e` for remaining. Days are Mon–Sun; completed days are those where `WorkoutLog.completed=True` within the active fitness plan's date range.

## Files

| Action | Path |
|---|---|
| **Create** | `templates/base_app.html` |
| **Create** | `static/css/app.css` |
| **Modify** | `templates/dashboard/index.html` |
| **Modify** | `templates/dashboard/weekly_plan.html` |
| **Modify** | `templates/accounts/profile_edit.html` |
| **Modify** | `apps/dashboard/views.py` — add `profile` to context |

`templates/base.html` and `static/css/main.css` are **not touched**.

## View Changes

`dashboard` view: add `profile = getattr(request.user, "profile", None)` to context (already fetched implicitly — make it explicit).

`weekly_plan` view: add `profile` to context (same pattern).

`profile_edit` view: already has `profile` via `get_object_or_404`.

## Weekly Plan Page

Extends `base_app.html`. Content stays functionally identical — day tabs, exercise table, running block, meal cards — but restyled with the dark card/border palette. Day tabs become pill buttons with active state `#6c63ff`.

## Profile Edit Page

Extends `base_app.html` instead of `base.html`. Form sections keep their `<h2>` grouping but adopt dark card styling.

## What Doesn't Change

- Login, register, onboarding pages — still extend `base.html`, still use `main.css`
- Logout URL, CSRF handling, form logic — unchanged
- All existing view logic and context variables — unchanged except adding `profile` to dashboard/weekly_plan contexts
