# General-Fitness Progression — Design

**Date:** 2026-06-22
**Status:** Approved (brainstorming), pending implementation plan
**Slice:** #4c of the coach-redesign decomposition (third and final Step-4 progression sub-slice)

## Context

Step 4 of the coaching spec defines goal-specific progression. Slice #4a delivered the
deload framework + strength weight progression; #4b added weight-loss (body-weight trend,
step target) and running (weekly mileage) progressions. This slice (#4c) adds the
**general-fitness** progressions that don't belong to a specific goal: gradual **session-
duration** growth, a **training-volume** nudge (add a 4th day), and **run-type rotation**
to keep running varied. With #4c, Step 4 is complete; the redesign continues with #5
(weekly/monthly review) and #6 (coach voice / nutrition).

### Decisions (from brainstorming)

- **Apply to all active users**, not a goal label (`primary_goal` is free text). The
  suggestions are advisory and layer on top of any goal-specific guidance; each renders
  only when there is something to say (presence gating).
- **Compute on read** for everything — no stored progression state, consistent with
  #4a/#4b. No plan mutation, no Claude call.
- **Consistent week = ≥80% of that week's planned (non-rest) workouts completed.** This is
  the shared trigger for the duration bump and the 4th-day nudge.
- **Self-contained module (Approach A):** all rules + services live in a new
  `services/coach/general_fitness.py`, including the `consistent_week_streak` helper.
  Written as a clean pure-plus-I/O pair so it is trivially extractable when slice #5
  (weekly review) needs it — but no shared module is built on spec.
- **Duration bump scope:** strength/yoga sessions only (`DURATION_BUMP_DAY_TYPES`). Running
  is owned by #4b (mileage); rest/active-recovery are intentionally easy. Suppressed during
  a deload week.
- **Run rotation = anti-monotony nudge** (not polarized 80/20, not a fixed template):
  trigger only when the recent run window is all one type.

### Relevant existing code

- `apps/fitness/models.py` — `FitnessPlan` (`week_number`, `start_date`, `end_date`,
  `is_active`, `total_workout_days`); each plan is one week. `WorkoutDay` (`date`,
  `day_type`, `focus_area`, `estimated_duration_minutes`). `RunningStrategy` (OneToOne
  `WorkoutDay`, `run_type` ∈ easy/interval/tempo/long_run/fartlek). `WorkoutLog`
  (`completed`, `date`, FK `workout_day`).
- `services/coach/engine.py::is_deload_week(week_number)` — reused to suppress the
  duration bump on deload weeks.
- `services/coach/cardio.py` — pattern reference (pure rules + `_for`/`get_` I/O services +
  frozen dataclass; lazy model imports inside services).
- `apps/dashboard/views.py::dashboard` + `templates/dashboard/index.html`,
  `apps/dashboard/views.py::weekly_plan` + `templates/dashboard/weekly_plan.html` — surfaces.

## Architecture

All new logic lives in `services/coach/general_fitness.py`.

### Constants

`CONSISTENCY_THRESHOLD = 0.8`, `DURATION_INCREMENT_MIN = 5`,
`BUMP_EVERY_CONSISTENT_WEEKS = 2`, `DURATION_CAP_MIN = 30`, `FOURTH_DAY_STREAK = 3`,
`MAX_TRAINING_DAYS = 4`, `RUN_MONOTONY_WINDOW = 3`,
`DURATION_BUMP_DAY_TYPES = ("strength", "yoga")`,
`ROTATION_PREFERENCE = ["easy", "interval", "tempo", "long_run", "fartlek"]`.

### Pure rules

- `consistent_week(planned: int, completed: int, threshold=0.8) -> bool` —
  `planned > 0 and completed / planned >= threshold`. A week with 0 planned (non-rest)
  workouts is not consistent (breaks the streak).
- `duration_bump(streak_weeks: int) -> tuple[int, bool]` — `bumps = streak // 2`;
  `bump = min(bumps * 5, 30)`; returns `(bump, capped)` where `capped = bumps * 5 >= 30`.
  Streak < 2 → `(0, False)`.
- `should_add_training_day(streak_weeks: int, current_days: int) -> bool` —
  `streak_weeks >= 3 and current_days < 4`.
- `suggest_run_rotation(recent_run_types: list[str]) -> tuple[str | None, str]` — only
  fires when `len(recent) >= RUN_MONOTONY_WINDOW` **and** all entries are the same type;
  then suggests the first `ROTATION_PREFERENCE` type not in the recent set, returning
  `(suggested_type, note)`. Otherwise `(None, "")`.

### I/O services (compute on read, lazy model imports)

- `consistent_week_streak(user, on_date) -> int` — iterate the user's `FitnessPlan`s by
  descending `week_number`, considering **only fully-elapsed weeks** (`end_date < on_date`)
  so an in-progress week never penalizes the streak. For each plan: `planned` = count of
  non-rest `WorkoutDay`s; `completed` = count of those days with a `completed=True`
  `WorkoutLog` for this user. Stop at the first week where `consistent_week(...)` is false;
  return the count of consecutive consistent weeks.
- `get_suggestions(user, on_date) -> GeneralFitnessSuggestions` — assembles the full
  advisory bundle:
  - `streak = consistent_week_streak(user, on_date)`.
  - `duration_bump_min, duration_capped = duration_bump(streak)`, **forced to `(0, False)`
    when the active plan is a deload week** (`is_deload_week(plan.week_number)`).
  - `current_training_days` = count of non-rest `WorkoutDay`s in the active plan (0 if no
    active plan); `add_training_day = should_add_training_day(streak, current_training_days)`.
  - `run_rotation` from the last `RUN_MONOTONY_WINDOW` completed runs' `run_type`
    (`RunningStrategy` on `WorkoutDay`s with a `completed` `WorkoutLog`, ordered by date
    desc); `None` when the rule does not fire.

### Data types (frozen dataclasses)

- `RunRotation`: `recent_type: str`, `suggested_type: str`, `note: str`.
- `GeneralFitnessSuggestions`: `consistent_week_streak: int`, `duration_bump_min: int`,
  `duration_capped: bool`, `add_training_day: bool`, `current_training_days: int`,
  `run_rotation: RunRotation | None`.

### Surfacing (advisory; render only when present)

- **Dashboard** (`dashboard` view + `index.html`): pass `general_fitness =
  get_suggestions(user, today)` and render a coach block:
  - 4th-day nudge when `add_training_day` ("You've trained consistently 3+ weeks — consider
    adding a 4th training day.").
  - run-rotation nudge when `run_rotation` ("Your last few runs were all easy — try an
    interval run.").
  - duration-bump summary line when `duration_bump_min > 0` ("Add ~10 min to your
    strength/yoga sessions this week.").
  The block renders nothing when all three are empty.
- **Weekly plan** (`weekly_plan` view + `weekly_plan.html`): when `duration_bump_min > 0`,
  show "+{bump} min suggested" beside each strength/yoga session's estimated duration; show
  the run-rotation note on the running day when present.

## Error handling & edge cases

- New user / no fully-elapsed weeks → `streak = 0`; all suggestions empty; nothing renders.
- Deload week (active plan) → duration bump suppressed; 4th-day and rotation still allowed.
- Already training ≥4 non-rest days → no 4th-day nudge.
- Runs varied, or fewer than 3 recent completed runs → no rotation nudge.
- Duration bump caps at +30 min (`duration_capped` exposes this for copy if desired).
- All services read-only; no writes anywhere in this slice.
- Other users' plans/logs are excluded by the `user` filter on every query.

## Testing

- **Pure functions:**
  - `consistent_week` — threshold boundary (80% exactly counts), 0 planned → False.
  - `duration_bump` — `<2` → `(0, False)`; cadence (2 wks → 5, 4 → 10); cap at 30 with
    `capped=True`.
  - `should_add_training_day` — fires at streak 3 with <4 days; not at 4 days; not below 3.
  - `suggest_run_rotation` — all-same window fires with a sensible underused type; varied
    window → None; window too short → None; all types recently used → None.
- **I/O services (DB):**
  - `consistent_week_streak` — counts consecutive consistent elapsed weeks; stops at a
    sub-80% week; excludes the in-progress (current) week; rest days excluded from the
    denominator; ignores other users.
  - `get_suggestions` — integration: derives bump/4th-day/rotation together; suppresses the
    bump on a deload week; `current_training_days` counts non-rest days; empty bundle for a
    new user.
- **Surfacing views** — dashboard context carries `general_fitness` and renders each nudge
  when present and omits the whole block when empty; weekly-plan shows the duration hint on
  strength/yoga sessions and the rotation note on the running day.
- Full suite stays green.

## Module layout

- `services/coach/general_fitness.py` — pure rules + I/O services + `RunRotation` /
  `GeneralFitnessSuggestions` dataclasses (new).
- `apps/dashboard/views.py`, `templates/dashboard/index.html`,
  `templates/dashboard/weekly_plan.html` (+ `static/css/app.css` if needed) — surfacing.
- Tests under `tests/test_coach/` (general-fitness rules + services) and
  `tests/test_dashboard/` (surfacing).

## Out of scope

- A structured goal field on `UserProfile` (suggestions apply to everyone; gating is by
  presence of something to say).
- Auto-applying any suggestion to the plan; persisting progression state; any Claude call.
- Polarized 80/20 or fixed-template run programming (chose anti-monotony only).
- Duration progression for running/rest/active-recovery days (#4b owns running; the others
  are intentionally easy).
- Slice #5 (weekly/monthly review) and #6 (coach voice / nutrition) — later slices. The
  `consistent_week_streak` helper is written to be extractable when #5 needs it.
