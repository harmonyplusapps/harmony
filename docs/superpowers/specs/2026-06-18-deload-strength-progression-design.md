# Deload + Strength Progression — Design

**Date:** 2026-06-18
**Status:** Approved (brainstorming), pending implementation plan
**Slice:** #4a of the coach-redesign decomposition (first of the Step-4 progression sub-slices)

## Context

Coaching spec Step 4 defines progressive overload and a mandatory 4th-week deload. The
full Step 4 spans five mechanisms (strength weights, weight-loss cardio/steps, running
mileage, general fitness, plus deload) — too large for one spec. It is decomposed into
sequential sub-slices that share a common shape ("given history + week number, suggest
next targets"):

- **#4a (this spec): Deload + strength weight progression** — the cross-cutting deload
  framework plus the flagship weight-progression engine.
- #4b: Weight-loss + running progression (cardio duration / steps / mileage).
- #4c: General-fitness progression.

### Relevant existing code

- `services/coach/engine.py` (slice #3) — pure `decide(snapshot, workout_day)` +
  `decide_today(user, on_date, workout_day=_UNSET)`; intensity path compounds modifiers,
  clamps to `[MIN_INTENSITY=0.4, MAX_INTENSITY=1.1]`, picks a single largest-deviation
  rationale; `DailyDecision(planned_day_type, recommended_day_type, intensity_modifier,
  avoid_focus_areas, rationale, flags, is_override)`.
- `apps/fitness/models.py`:
  - `FitnessPlan.week_number` (the active plan's week; deload keys off `% 4`).
  - `WorkoutExercise` — `exercise_cache` (FK, nullable), `custom_name`, `section`
    (warmup/main/cooldown/…), `sets`, `reps`, `intensity`, `notes`; `display_name`
    property = `exercise_cache.name or custom_name`. **No weight column.**
  - `ExerciseLog` — `workout_log` (→ user, date), `workout_exercise`, `sets_completed`,
    `reps_completed` (JSON list), `weight_kg` (JSON list per set), `skipped`.
- `templates/dashboard/partials/workout_today.html` — lists each exercise for logging
  (keyed by `display_name`); posts to `log_exercise` (`apps/fitness/views.py`).
- Dashboard already renders `decision.rationale` in a coach banner on override.

## Decisions (from brainstorming)

- **Scope:** strength weight progression + deload only. Other goal types are #4b/#4c.
- **Deload representation:** single `intensity_modifier` reduction + a `"deload"` flag and
  an explicit banner ("trim your sets ~40%, ~20% off your weights"). No new `DailyDecision`
  field; the prescribed sets are never mutated (advisory overlay).
- **Compute on read**, consistent with slices #2/#3 — no stored suggestions, no migration.

## Architecture

### Part A — Deload (in `services/coach/engine.py`)

- `is_deload_week(week_number) -> bool`: pure; `week_number > 0 and week_number %
  DELOAD_CYCLE_WEEKS == 0`. Constant `DELOAD_CYCLE_WEEKS = 4`.
- `decide(snapshot, workout_day, is_deload=False)`:
  - Hard stops are unchanged and still take precedence (a sore/recovery day on a deload
    week still becomes active recovery).
  - On the intensity path, when `is_deload`: multiply the running modifier by
    `DELOAD_MULTIPLIER = 0.8`, append `"deload"` to flags, and **force the rationale** to
    the deload headline: `"Deload week — lighter loads, trim your sets ~40% to recover."`
    (deload owns the rationale regardless of other candidates). Other modifiers still
    compound into `intensity_modifier`; final value clamped to `[0.4, 1.1]`. `is_override`
    is True whenever `is_deload` (intensity always shifts from 1.0).
- `decide_today(user, on_date, workout_day=_UNSET)`: resolve the active `FitnessPlan` once
  (cheap, indexed) for `week_number`; compute `is_deload = is_deload_week(plan.week_number)`
  when a plan exists (else `False`); still reuse a passed-in `workout_day` to avoid the
  prefetch re-query; pass `is_deload` to `decide`. **No dashboard view change needed** —
  the coach banner already renders `decision.rationale`.

### Part B — Strength weight progression (`services/coach/progression.py`)

Pure rules split from I/O, like `calculations.py` / `snapshot.py`.

**`WeightSuggestion`** (frozen dataclass):
`exercise_id: int`, `suggested_weight_kg: float | None`, `reason: str`
(`new | progress | hold | backoff | deload`), `note: str` (short coach line).

**Pure rule** — `suggest_next_weight(sessions, increment_kg, is_deload) -> tuple[float|None, str, str]`
returning `(suggested_weight_kg, reason, note)`. `sessions` is one exercise's history,
oldest→newest, each `(working_weight_kg: float, met_target: bool)`:
- empty → `(None, "new", "Log a few sessions and I'll start suggesting loads.")`.
- `working_weight` = most recent session's weight.
- **deload override** (checked first): `is_deload` → `(round_to_increment(working_weight *
  0.8), "deload", "Deload week — back off to ~80%.")`.
- **progress:** last two sessions both `met_target` → `(working_weight + increment_kg,
  "progress", "Hit it twice — go up {increment} kg.")`.
- **back-off:** two most recent both not `met_target` → `(round_to_increment(working_weight
  * 0.9), "backoff", "Two tough sessions — drop 10% and rebuild.")`.
- **hold** (single recent miss, or only one session): `(working_weight, "hold", "Stay
  here and nail all your sets.")`.

`round_to_increment(w)` rounds to the nearest `increment_kg` (default `INCREMENT_KG = 2.5`,
metric; tunable). Increment is configurable so #4b/#4c or future per-lift tuning can reuse it.

**Per-session derivation** (helpers, pure):
- `working_weight(exercise_log) -> float | None` = `max(weight_kg)` if the list is
  non-empty else `None` (the top working set).
- `met_target(exercise_log, prescribed_sets, prescribed_reps) -> bool` = not `skipped` and
  `sets_completed >= prescribed_sets` and `reps_completed` is non-empty and every entry
  `>= prescribed_reps`.

**I/O service** — `suggest_strength_progression(user, workout_day, is_deload) ->
dict[int, WeightSuggestion]`:
- For each `WorkoutExercise` in `workout_day` with `section == "main"` and non-null
  `sets`/`reps`:
  - Gather this user's prior `ExerciseLog`s for the **same exercise identity** —
    `exercise_cache_id == ex.exercise_cache_id` when set, else
    `custom_name == ex.custom_name` — via
    `ExerciseLog.objects.filter(workout_log__user=user, workout_exercise__<identity>)`
    `.select_related("workout_exercise").order_by("workout_log__date")`.
  - Build `sessions` from logs that have a `working_weight` (skip weightless/empty rows),
    using each log's own prescribed sets/reps for `met_target`.
  - Call `suggest_next_weight(sessions, INCREMENT_KG, is_deload)`; store a
    `WeightSuggestion` keyed by `ex.id`.
- Exercises with no weighted history yield `reason == "new"` (suggested weight `None`).

### Part C — Surfacing

- The view that renders the exercise-logging list (the one rendering
  `templates/dashboard/partials/workout_today.html`) calls
  `suggest_strength_progression(request.user, today_workout, is_deload)` and passes
  `weight_suggestions` (dict keyed by exercise id) plus `is_deload` to the template.
  `is_deload` is computed via `is_deload_week` on the active plan's `week_number`.
- `workout_today.html`: beside each main exercise, when a suggestion exists for `exercise.id`
  with a non-null weight, render `Suggested: {{ s.suggested_weight_kg }} kg — {{ s.note }}`.
- `templates/dashboard/weekly_plan.html`: show a "Deload week" badge when
  `is_deload_week(fitness_plan.week_number)` (the weekly view exposes `week_number`); the
  view passes an `is_deload` flag.

## Error handling & edge cases

- No active plan / no `week_number` → `is_deload = False`; engine unaffected.
- Exercise with no logged weight ever → `reason "new"`, `suggested_weight_kg None`; the
  template falls back to the plan's existing display (no suggestion line).
- `weight_kg` / `reps_completed` JSON may be empty or ragged → `working_weight` returns
  `None` (row skipped from `sessions`); `met_target` treats missing reps as not met.
- Deload precedence: deload never overrides a hard stop (active recovery still wins); on
  the intensity path it owns the rationale and applies its multiplier.
- Engine and progression perform **no writes**.

## Testing

- **`is_deload_week`** — weeks 1/2/3 false, 4/8/12 true, week 0 false.
- **`decide` deload** — on intensity path, `is_deload` applies ×0.8, adds `"deload"` flag,
  rationale is the deload headline, compounds with low energy and clamps; deload does NOT
  fire on a hard-stop day (soreness still → active recovery).
- **`decide_today` deload** — a user on an active week-4 plan with a clean workout gets the
  deload decision; a week-3 plan does not.
- **`suggest_next_weight`** (pure) — new/empty; progress after two met sessions; hold on a
  single miss and on a lone session; back-off after two misses; deload override beats
  progress; `round_to_increment` rounds 0.9/0.8 results to the nearest 2.5 kg.
- **`working_weight` / `met_target`** — top-set selection; skipped → not met; short
  `reps_completed` → not met; meeting sets and reps → met.
- **`suggest_strength_progression`** (integration, DB) — two prior weeks of met sessions on
  a barbell lift → "progress" with +2.5 kg; identity matching across weeks via
  `exercise_cache` and via `custom_name`; a main exercise with no history → "new"; a deload
  week trims the suggestion.
- **Surfacing view test** — the logging view passes `weight_suggestions` and `is_deload`;
  the rendered page shows a suggested weight for a lift with history; the weekly-plan view
  shows the deload badge on a week-4 plan.

## Out of scope

- Weight-loss / running / general-fitness progression (#4b, #4c).
- Persisting suggestions or a structured suggested-weight field on `WorkoutExercise`.
- Regenerating workouts or auto-applying suggested weights (advisory only).
- Per-lift custom increments / 1RM estimation / plate math.
- Any Claude call.
