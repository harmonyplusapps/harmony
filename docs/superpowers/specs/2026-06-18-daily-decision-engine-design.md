# Daily Decision Engine — Design

**Date:** 2026-06-18
**Status:** Approved (brainstorming), pending implementation plan
**Slice:** #3 of the coach-redesign decomposition (daily decision engine)

## Context

The coach redesign turns Harmony from a *weekly batch plan generator* into a *daily,
data-driven decision engine*. Slice #2 built the data layer and `get_health_snapshot`.
This slice builds the engine that reads that snapshot and **adjusts today's planned
workout**, explaining its choice in one line (coaching spec Steps 3–5).

### Decisions (from brainstorming)

- **Daily override layer on the weekly skeleton.** Keep the existing weekly
  `FitnessPlan` / `WorkoutDay` baseline. The engine produces a per-day `DailyDecision`
  overlay that adjusts today's workout; it never regenerates the week and never mutates
  the `WorkoutDay`.
- **Rule-based and deterministic.** Pure functions implement the spec's decision tree
  over the typed snapshot — no Claude call on the daily path. Fast, free, deterministic,
  fully unit-testable; mirrors how `calculations.py` / `snapshot.py` were built.
- **Compute on read.** `decide_today(user, date)` recomputes whenever the dashboard (or
  email) needs it, always reflecting the latest snapshot. No new DB model, no migration.

### Relevant existing code

- `services/health/snapshot.py::get_health_snapshot(user, date) -> HealthSnapshot`
  (fields: sleep_hours, sleep_quality, energy, stress, soreness[list[SorenessItem]],
  cycle_phase, momentum[Momentum], steps, resting_hr, recent_workouts[list[WorkoutLog]]).
- `services/health/calculations.py::Momentum` (current_streak, days_since_last, bucket:
  no_history | current | missed_2_3 | missed_4_7 | missed_long | full_reset).
- `apps/health/models.py::MUSCLE_GROUP_TO_FOCUS` maps muscle group → `WorkoutDay.focus_area`.
- `apps/fitness/models.py::WorkoutDay` (day_type, focus_area, exercises, …) and
  `WorkoutLog` (date, completed, perceived_exertion).
- `apps/dashboard/views.py::dashboard` already resolves today's `WorkoutDay` and renders
  `dashboard/index.html`.

## Architecture

Pure logic is split from I/O, exactly like slice #2.

### 1. Module layout & output

- `services/coach/__init__.py` — new package.
- `services/coach/engine.py`:
  - `decide(snapshot, workout_day) -> DailyDecision` — **pure**. Takes the
    `HealthSnapshot` and today's planned `WorkoutDay` (or `None` for a rest/no-plan day),
    returns the decision. No DB access.
  - `decide_today(user, on_date) -> DailyDecision` — thin entry: calls
    `get_health_snapshot(user, on_date)`, fetches today's active `WorkoutDay`
    (by `day_of_week`), then calls `decide(...)`. This is what the dashboard calls.
  - Named threshold constants (see §3) live at module top, tunable.

**`DailyDecision`** (frozen dataclass):

```python
@dataclass(frozen=True)
class DailyDecision:
    planned_day_type: str | None      # what the weekly plan prescribed (None if no plan)
    recommended_day_type: str         # possibly overridden, e.g. "active_recovery"
    intensity_modifier: float         # 1.0 = as planned; clamped to [0.4, 1.1]
    avoid_focus_areas: tuple[str, ...] # focus areas not to train today (from soreness)
    rationale: str                    # one-line "why"
    flags: tuple[str, ...]            # advisory notes, e.g. "overtraining_watch", "push"
    is_override: bool                 # did anything change vs the plan?
```

Tuples (not lists) so the dataclass is genuinely immutable/frozen.

### 2. Slice-#2 follow-up folded in

The engine matches soreness to a workout's `focus_area`, so add `focus_area` to
`SorenessItem` (in `services/health/snapshot.py`), populated in `get_health_snapshot`
from `MUSCLE_GROUP_TO_FOCUS`. This is the tracked follow-up from the slice-#2 spec.
`SorenessItem` becomes `(muscle_group, severity, focus_area)`. Existing snapshot tests
that build `SorenessItem("quads", "severe")` by position must be updated to include the
focus area (or assert on `.muscle_group`/`.severity` fields).

### 3. Decision tree

Rules evaluated in precedence order. A **hard stop** sets
`recommended_day_type = "active_recovery"`, `is_override = True`, owns the rationale, and
short-circuits the intensity math (intensity set to `RECOVERY_INTENSITY = 0.4`).
Otherwise **intensity modifiers compound multiplicatively** and the result is clamped to
`[MIN_INTENSITY = 0.4, MAX_INTENSITY = 1.1]`.

`avoid_focus_areas` is always computed (independent of hard stops): the set of
`focus_area`s for soreness items with severity in {moderate, severe}.

**Hard stops** (first match wins):

1. **Planned rest / no workout** — `workout_day is None` or `day_type == "rest"`:
   no override. `recommended_day_type = planned_day_type or "rest"`,
   `intensity_modifier = 1.0`, `is_override = False`, rationale = "Rest day — recover well."
2. **Recovery needed** — *hard session yesterday* AND *poor sleep*:
   - hard yesterday = a `recent_workouts` entry dated `on_date - 1` with
     `perceived_exertion >= HARD_RPE (8)`, or (if RPE is null) its `workout_day.day_type`
     in {"strength", "running"}.
   - poor sleep = `sleep_quality is not None and sleep_quality <= POOR_SLEEP_QUALITY (2)`
     OR `sleep_hours is not None and sleep_hours < POOR_SLEEP_HOURS (6)`.
   - Rationale: "Hard session yesterday plus short sleep — active recovery today."
3. **Soreness conflict** — `workout_day.focus_area` in `avoid_focus_areas`:
   - Rationale names a sore group, e.g. "Quads still sore — keeping today to active recovery."

**Intensity modifiers** (compound; only if no hard stop fired):

4. **Low energy** — `energy is not None and energy <= LOW_ENERGY (3)` → ×0.7.
   Rationale candidate: "Energy's low today — lighter session."
5. **Missed-days reset** (from `momentum.bucket`):
   `current` ×1.0 · `missed_2_3` ×0.85 · `missed_4_7` ×0.6 · `missed_long` ×0.6 ·
   `full_reset` ×0.5 · `no_history` ×1.0. Guilt-free phrasing
   ("Welcome back — easing in." for the larger gaps).
6. **Cycle phase**: `luteal`/`period` ×0.85 · `follicular`/`ovulation` ×1.1 · else ×1.0.
   Candidate: "Luteal phase — favoring a steadier effort."
7. **Positive momentum**: `current_streak >= PUSH_STREAK (3)` → ×1.05 and add `"push"`
   flag. `current_streak >= OVERTRAIN_STREAK (5)` → add `"overtraining_watch"` flag
   (no intensity change).

**Rationale selection:** a hard stop owns the rationale. Otherwise the rationale is the
single intensity rule whose multiplier deviates most from 1.0 (ties broken by precedence
order 4→7), so the user gets one clear reason. If no rule fired and intensity is 1.0:
`is_override = False`, rationale = "On plan — go for it."

`is_override` is set per branch: `False` for the rest / no-plan and on-plan cases;
`True` for the recovery and soreness hard stops and whenever the final
`intensity_modifier` differs from 1.0. `avoid_focus_areas` is informational (shown in
the UI when non-empty) and does **not** by itself flip `is_override` — a sore but
non-conflicting focus area on an otherwise on-plan day leaves `is_override = False`.

### 4. Dashboard integration

`apps/dashboard/views.py::dashboard` calls `decide_today(request.user, today)` and passes
the `DailyDecision` to the template (context key `decision`).

`templates/dashboard/index.html` renders, near the today's-workout card:

- A **rationale banner** ("Today's call: {{ decision.rationale }}") whenever
  `decision.is_override`.
- When `recommended_day_type == "active_recovery"` and the plan was something else: show a
  static **active-recovery card** (a module-level constant `ACTIVE_RECOVERY_SUGGESTION`:
  e.g. "20–30 min easy walk + full-body mobility / light stretching") in place of the
  planned exercise list, with the planned workout noted as deferred. No Claude, no
  generated content.
- Otherwise (intensity adjustment only): show the planned workout as-is plus an
  intensity note ("Aim for about {{ decision.intensity_modifier|percent }} of the usual
  load today.").

Styling reuses the existing dark-UI patterns / CSS variables; add minimal classes
(`.coach-banner`, `.active-recovery-card`) consistent with the current stylesheet.

The decision is advisory display only — it does not alter `WorkoutLog` or the stored plan.

## Error handling & edge cases

- No active `FitnessPlan` / no `WorkoutDay` today → `workout_day = None` → hard stop #1
  path (rest), `is_override = False`. Dashboard shows its existing "no plan" state plus,
  at most, a neutral rationale.
- Missing snapshot fields (None sleep/energy/cycle) → those rules simply don't fire;
  never an error (snapshot already degrades gracefully).
- `intensity_modifier` always within `[0.4, 1.1]` after clamping.
- Engine performs no writes.

## Testing

- **`decide` (pure) unit tests** — one per rule and key combinations:
  - planned rest → no override.
  - recovery hard-stop fires on hard-yesterday + poor sleep; does NOT fire if only one
    condition holds.
  - soreness conflict: today's focus_area sore (severe) → active recovery; mild soreness
    does NOT hard-stop; soreness in a different focus area → no day-type override but
    appears in `avoid_focus_areas`.
  - low energy ×0.7; each momentum bucket multiplier; cycle-phase multipliers; positive
    streak ×1.05 + flags; overtraining_watch flag at streak ≥ 5.
  - compounding + clamp (e.g. luteal × low-energy stays ≥ 0.4; follicular × push clamps
    at 1.1).
  - rationale selection picks the largest-deviation rule; "on plan" when nothing fires.
  - precedence: a hard stop wins over intensity rules that would also apply.
- **`SorenessItem.focus_area`** — snapshot populates it from `MUSCLE_GROUP_TO_FOCUS`;
  update existing slice-#2 snapshot tests accordingly.
- **`decide_today` integration test** — builds a user with a `WorkoutDay`, snapshot data
  (soreness/sleep/workout history) in the DB, asserts the resulting `DailyDecision`.
- **Dashboard view test** — `decision` is in context; rationale banner renders on
  override; active-recovery card renders when the day is downgraded; intensity note
  renders otherwise.

## Out of scope

- Deload weeks / progressive overload (slice #4).
- Step-10 special situations ("I'm sick/traveling") — need a user-declared status input
  the snapshot doesn't carry.
- Regenerating or restructuring the workout's exercises (the weekly generator owns that).
- Persisting decisions / decision history.
- Any Claude call on the daily path.
