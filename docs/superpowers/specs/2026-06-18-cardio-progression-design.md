# Weight-loss + Running Progression — Design

**Date:** 2026-06-18
**Status:** Approved (brainstorming), pending implementation plan
**Slice:** #4b of the coach-redesign decomposition (second Step-4 progression sub-slice)

## Context

Step 4 of the coaching spec defines goal-specific progression. Slice #4a delivered the
deload framework + strength weight progression. This slice (#4b) adds the **weight-loss**
and **running** progressions: body-weight trend, daily step target, and weekly running
mileage. #4c (general-fitness) follows.

### Decisions (from brainstorming)

- **Include body-weight now** — add a `WeightLog` model + check-in logging + a weekly-
  average trend (the only data-model/UI work in this slice).
- **Gate suggestions by data presence**, not a goal label (`primary_goal` is free text):
  a suggestion appears only where its underlying data exists.
- **Compute on read** for all progressions — no stored targets, consistent with #4a.
- **Dropped from scope:** standalone "cardio duration +5 min/week" (no distinct cardio-
  session marker beyond running; overlaps mileage for runners). Also out: "add a strength
  session every 3-4 weeks" and run-type rotation (general-fitness / plan-generation
  concerns → #4c or later).

### Relevant existing code

- `apps/health/models.py` — `WellnessLog.steps` (slice #2, daily, nullable);
  `SorenessLog`/`PeriodLog` patterns for the new `WeightLog`.
- `apps/health/views.py` — `checkin` view + `_checkin_context` render today's check-in
  (`/health/checkin/`) capturing steps/resting-HR/soreness/cycle; uses `_parse_optional_int`,
  a `transaction.atomic()` block, and Post/Redirect/Get.
- `apps/fitness/models.py` — `RunningStrategy` (OneToOne `WorkoutDay`, `run_type`,
  `total_distance_km`, `total_duration_minutes`); `WorkoutDay.date`; `WorkoutLog`
  (`completed`, `date`).
- `services/coach/engine.py::is_deload_week(week_number)` — reused for the running deload.
- `apps/dashboard/views.py::dashboard` + `templates/dashboard/index.html`,
  `apps/dashboard/views.py::weekly_plan` + `templates/dashboard/weekly_plan.html` — surfaces.

## Architecture

### Part A — Body-weight: model, logging, trend

**`WeightLog`** (new, `apps/health/models.py`):
- `user` FK, `date` DateField, `weight_kg` DecimalField(max_digits=5, decimal_places=1),
  `created_at`. `unique_together = (user, date)`, `ordering = ["-date"]`.

**Check-in logging** (`apps/health/views.py`):
- Add an optional "Weight (kg)" number input to `templates/health/checkin.html`.
- In `checkin` POST (inside the existing `transaction.atomic()` block): parse
  `weight_kg`; when present, upsert today's `WeightLog` (`update_or_create` on
  `user`+`date`). A blank value leaves any existing log untouched.
- `_checkin_context` passes today's logged weight (prefill) and today's step target
  (Part B) to the template.

**Trend** (`services/coach/cardio.py`):
- Pure `weekly_average(samples: list[float]) -> float | None` — mean, or None if empty.
- Pure `weight_trend(current_avg, prior_avg, epsilon=0.2) -> str` — `down | up | flat`
  (flat when `abs(current-prior) <= epsilon`).
- I/O `body_weight_trend(user, on_date) -> WeightTrend | None` (frozen dataclass
  `current_avg, prior_avg, delta_kg, direction`): current window = `WeightLog`s in
  `(on_date-7, on_date]`; prior window = the 7 days before that. Returns `None` unless the
  current window has ≥2 logs (not enough signal otherwise). `delta_kg = current_avg -
  prior_avg` (rounded 1 dp); `direction` from `weight_trend`. Weekly averages, not daily.

### Part B — Step-target and running-mileage progressions (`services/coach/cardio.py`)

Pure rules:
- `suggest_step_target(recent_avg_steps: int | None) -> int | None`:
  `None` if no data; `10000` if `recent_avg_steps >= 10000` (maintain); else
  `min(10000, round_to_500(recent_avg_steps) + 500)` where `round_to_500` rounds to the
  nearest 500.
- `suggest_weekly_mileage_km(prior_week_km: float | None, is_deload: bool) -> float | None`:
  `None` if `prior_week_km` is falsy (None/0); deload → `round(prior_week_km * 0.7, 1)`
  (the −30% running deload); else `round(prior_week_km * 1.10, 1)` (the 10% cap).

I/O services (lazy model imports):
- `suggest_step_target_for(user, on_date) -> int | None`: recent average of
  `WellnessLog.steps` (non-null) over `(on_date-7, on_date]`; pass the int mean (or None)
  to `suggest_step_target`.
- `suggest_weekly_mileage_for(user, on_date, is_deload) -> float | None`:
  `prior_week_km` = sum of `RunningStrategy.total_distance_km` for the user's running days
  whose `WorkoutDay.date` is in `(on_date-7, on_date]` **and** whose day has a completed
  `WorkoutLog`; pass to `suggest_weekly_mileage_km`.

### Part C — Surfacing

- **Dashboard** (`dashboard` view + `index.html`): pass `weight_trend` and `step_target`;
  render a body-weight trend readout ("Weight 64.7 kg · ▼0.3 vs last week") and a step-goal
  line ("Today's step goal: 8,500"), each only when its value is non-None.
- **Check-in** (`checkin` page): show the step target beside the steps input when present.
- **Weekly plan** (`weekly_plan` view + `weekly_plan.html`): pass `weekly_mileage_km`
  (computed via `suggest_weekly_mileage_for` with the plan's deload flag) and render a
  running-mileage line ("This week: aim ≤ 14.3 km") when the plan has running days and a
  value exists.

## Error handling & edge cases

- All suggestions return `None` when their data is absent → templates render nothing
  (data-presence gating). No errors on empty/partial data.
- `WeightLog.weight_kg` blank in the check-in → no upsert; existing log preserved.
- Step target caps at 10,000 and never decreases a strong walker below their average.
- Mileage uses **completed** runs only (actual mileage), so an unlogged plan yields `None`.
- `body_weight_trend` needs ≥2 current-window logs; otherwise `None`.
- All new code performs reads only except the check-in `WeightLog` upsert.

## Testing

- **`WeightLog` model** — uniqueness per (user, date); nullable-free fields persist.
- **Pure functions:**
  - `round_to_500` / `suggest_step_target` — None on no data; nearest-500 + 500; maintain
    at ≥10k; cap at 10k (e.g. 9,800 → 10,000).
  - `suggest_weekly_mileage_km` — None on 0/None; ×1.10 normal; ×0.7 deload; rounding.
  - `weekly_average` (empty→None, mean), `weight_trend` (down/up/flat with epsilon).
- **I/O services (DB):**
  - `suggest_step_target_for` — averages trailing-7-day steps, ignores nulls/old days,
    None when no steps.
  - `suggest_weekly_mileage_for` — sums completed running days in window; excludes
    uncompleted and out-of-window; applies deload; None when no runs.
  - `body_weight_trend` — current vs prior weekly average, direction + delta; None with
    <2 current logs; excludes other users.
- **Check-in view** — POST with `weight_kg` upserts today's `WeightLog`; blank leaves it;
  GET prefills the logged weight and shows the step target.
- **Surfacing views** — dashboard context carries `weight_trend`/`step_target` and renders
  them when present (and omits when absent); weekly-plan shows the mileage line on a plan
  with completed running history.

## Module layout

- `apps/health/models.py` — `WeightLog` (+ migration).
- `apps/health/views.py`, `templates/health/checkin.html` — weight logging + step-target display.
- `services/coach/cardio.py` — pure rules + I/O services + `WeightTrend` dataclass.
- `apps/dashboard/views.py`, `templates/dashboard/index.html`, `weekly_plan.html`,
  `static/css/app.css` — surfacing.
- Tests under `tests/test_coach/` (cardio rules/services) and `tests/test_health/` /
  `tests/test_dashboard/` (model, check-in, surfacing).

## Out of scope

- General-fitness progression and run-type rotation / "add a 4th day" (#4c).
- Standalone cardio-duration progression (dropped — see Decisions).
- A structured goal field on `UserProfile` (gating is by data presence).
- Auto-applying targets to the plan; persisting suggested targets; any Claude call.
