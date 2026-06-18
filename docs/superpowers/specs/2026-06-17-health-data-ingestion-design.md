# Health Data Ingestion — Design

**Date:** 2026-06-17
**Status:** Approved (brainstorming), pending implementation plan
**Slice:** #2 of the coach-redesign decomposition (health-data ingestion)

## Context

The coach redesign reframes Harmony from a **weekly batch plan generator** into a
**daily, data-driven decision engine**. Before each workout the coach is supposed to
read the user's recent health data — soreness, sleep, energy, momentum, menstrual
cycle phase, steps, resting HR — and plan accordingly (see redesign spec Steps 2–3).

The current app collects only some of this. This slice builds the **data layer and a
clean read interface** so the future decision engine (slice #3) has real data to read.
It does **not** build the decision engine itself.

### What already exists (verified in code)

- `apps/health/models.py::WellnessLog` — daily, `unique_together (user, date)`:
  `sleep_hours`, `sleep_quality`, `mood_score`, `stress_level`, `energy_level`,
  mindfulness fields. **Sleep and subjective energy are already captured.**
- `apps/fitness/models.py::WorkoutLog` — `completed`, `completion_percentage`,
  `perceived_exertion`, `actual_duration_minutes`, `date`. **Momentum/streak derives
  from this — no new data needed.**
- `apps/fitness/models.py::ExerciseLog` — `sets_completed`, `reps_completed`,
  `weight_kg`. Source for progressive overload (slice #4, out of scope here).
- `apps/accounts/models.py::UserProfile` — onboarding profile; home for cycle config.

### What is missing (this slice adds it)

- **Soreness** by muscle group + severity — the hardest gate in the decision tree
  ("specific soreness → do NOT train that muscle group").
- **Menstrual cycle** tracking → phase computation.
- **Resting HR** — referenced for overtraining checks and progress celebration.
- **Steps** — referenced for weight-loss step targets.

## Decisions

- **Data entry:** manual daily check-in. No wearable/HealthKit integration (large lift,
  not feasible inside a Django web app alone). Fields are optional; the engine degrades
  gracefully when a field is blank. Models are designed so a sync source could populate
  the same fields later.
- **Cycle tracking:** log period start dates + average cycle length; **auto-compute**
  the phase each day. Lowest daily friction, most accurate.
- **Soreness granularity:** muscle group **+ severity** (mild / moderate / severe).
  Engine intent: severe = don't train it, mild = train with caution.
- **Model placement:** extend existing models for daily scalars; dedicated models for
  multi-valued (soreness) and event-based (period) data. Rejected alternatives: a new
  unified `DailyCheckin` model (duplicates `WellnessLog`'s daily role, fragments sleep
  data); a JSON soreness blob on `WellnessLog` (makes per-group queries and severity
  logic awkward).

## Architecture

### 1. Data models

**`WellnessLog`** (extend, `apps/health`):
- `steps` — `IntegerField(null=True, blank=True)`
- `resting_hr_bpm` — `IntegerField(null=True, blank=True)`

**`SorenessLog`** (new, `apps/health`):
- `user` — FK User
- `date` — DateField
- `muscle_group` — choices: `chest, back, shoulders, arms, core, glutes, quads,
  hamstrings, calves`
- `severity` — choices: `mild, moderate, severe`
- `unique_together = (user, date, muscle_group)`
- Each muscle group maps to a `WorkoutDay.focus_area`
  (`upper_body, lower_body, full_body, core, cardio`) so the engine can match soreness
  to a planned focus. Mapping lives as a constant dict in the model module.

**`PeriodLog`** (new, `apps/health`):
- `user` — FK User
- `start_date` — DateField (the day a period started)
- `unique_together = (user, start_date)`
- One row per period start. Phase is computed from these rows, never stored.

**`UserProfile`** (extend, `apps/accounts`):
- `tracks_cycle` — `BooleanField(default=False)` — gates all cycle UI
- `average_cycle_length` — `IntegerField(default=28)`

### 2. Daily check-in UI

- Route: `GET/POST /health/checkin/` (defaults to today). Built with existing
  HTMX + dark-UI patterns.
- One form, **all fields optional** — target ~15-second interaction.
  - **Soreness:** tappable muscle-group chips; tapping reveals mild/moderate/severe
    selector. On submit, today's `SorenessLog` rows are replaced with the current set.
  - **Steps / Resting HR:** two optional number inputs → written to today's
    `WellnessLog` (created if absent; merges with sleep/energy already logged there).
  - **Cycle** (only if `profile.tracks_cycle`): "Period started today" button creates a
    `PeriodLog`; current computed phase shown read-only as confirmation.
- **Idempotent:** reopening shows what's already logged today and allows editing.
- Entry points: a dashboard card/link; also the deep-link target for the nightly email
  and the future decision engine.

### 3. Snapshot service (primary deliverable)

`services/health/snapshot.py`:

```
get_health_snapshot(user, date) -> HealthSnapshot
```

The clean interface the slice-#3 decision engine will read so it never touches raw
models. Returns a dataclass with typed, gracefully-degrading fields:

- `sleep`, `energy`, `stress` — from `WellnessLog` (None if no log that day)
- `soreness` — list of `{muscle_group, severity}` for the date (empty if none)
- `cycle_phase` — `follicular | ovulation | luteal | period | None`
- `momentum` — derived from `WorkoutLog`: current streak, consecutive days,
  days-since-last-workout (drives missed-day reset logic)
- `steps`, `resting_hr` — from `WellnessLog`, may be None
- `recent_workouts` — last few completed `WorkoutLog`s (for "hard workout yesterday")

Supporting pure functions (independently testable):
- `compute_cycle_phase(last_period_start, cycle_length, date) -> phase | None`
  - period: days 1–5; follicular: days 1–14; ovulation: ~day 14;
    luteal: days 15–end. (Period overlaps early follicular; period takes precedence
    for days 1–5.)
- `compute_momentum(workout_logs, date) -> Momentum` — streak / consecutive-days /
  days-since-last, bucketed per the decision tree (1 / 2–3 / 4–7 / 14+ missed days).

## Error handling & edge cases

- All check-in fields optional; absent data → `None`/empty in the snapshot, never an
  error. The engine is responsible for handling missing signals.
- No `PeriodLog` rows or `tracks_cycle = False` → `cycle_phase = None`.
- No `WorkoutLog` history → momentum reports zero streak / large days-since.
- Re-submitting the check-in for a day replaces that day's soreness set rather than
  appending duplicates.

## Testing

- **Model tests:** `SorenessLog` uniqueness per (user, date, group); `PeriodLog`
  uniqueness; `WellnessLog` new fields nullable.
- **`compute_cycle_phase`:** all four phases + boundary days (day 1, 5, 14, 15, last
  day); not-tracked → None.
- **`compute_momentum`:** active streak, each missed-day bucket (1 / 2–3 / 4–7 / 14+),
  empty history.
- **`get_health_snapshot` integration:** partial data (e.g. sleep logged, soreness and
  steps absent) proves graceful degradation; full data returns all fields.
- **Check-in view:** GET renders today's existing data; POST creates/updates the right
  rows; cycle controls hidden when `tracks_cycle = False`.

## Out of scope

- The daily decision engine that consumes the snapshot (slice #3).
- Progressive overload / deload tracking (slice #4).
- Wearable / Apple Health sync.
- Backfilling historical data.
