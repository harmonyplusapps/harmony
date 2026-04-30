# Harmony — Fitness & Health App Design

**Date:** 2026-04-29
**Status:** Approved

---

## Overview

Harmony is a web-based fitness and health app for 2–5 users. It generates personalized weekly fitness and nutrition plans using Claude AI, tracks daily progress, and adapts plans week-over-week based on logged data. Users receive a daily email summary each evening.

---

## Section 1: Architecture

```
Browser (HTMX + Alpine.js)
        ↕
Django Web App
  ├── Auth (built-in)
  ├── Async Views (Claude API calls)
  ├── HTMX endpoints (progress logging, plan updates)
  └── Celery Tasks (daily email scheduling, weekly plan adaptation)
        ↕                    ↕                   ↕
  PostgreSQL DB         Claude API           wger API
                                          (cached in DB)
        ↕
  Redis (Celery broker)
        ↕
  Gmail SMTP (daily summary emails)
```

**Stack:**
- **Backend:** Django (Python) with async views
- **Frontend:** HTMX + Alpine.js (no separate JS framework)
- **Database:** PostgreSQL
- **AI:** Claude API (Anthropic)
- **Exercise data:** wger API (open source, no rate limits), cached locally in DB
- **Background jobs:** Celery + Redis
- **Email:** Gmail SMTP
- **Deployment:** Railway (web + worker + beat + postgres + redis)

---

## Section 2: Data Models

### User & Profile

**`UserProfile`** (OneToOne → Django User)
| Field | Type | Notes |
|---|---|---|
| `height_cm` | Decimal | |
| `weight_kg` | Decimal | |
| `gender` | CharField | male/female/other |
| `date_of_birth` | Date | stored as DOB, not age |
| `fitness_experience` | CharField | beginner/intermediate/advanced |
| `primary_goal` | TextField | freeform — user describes their goal in their own words |
| `diet_type` | CharField | omnivore/vegetarian/vegan/keto/paleo/other |
| `food_allergies` | JSON | list of allergies |
| `food_preferences` | Text | freeform |
| `daily_routine` | Text | freeform description of typical day |
| `wake_time` | Time | |
| `sleep_time` | Time | |
| `work_schedule` | CharField | 9-5/shift/flexible |
| `workout_days_per_week` | Int | |
| `preferred_workout_days` | JSON | e.g. `["Monday","Wednesday","Friday"]` |
| `running_days_per_week` | Int | |
| `workout_location` | CharField | gym/home/outdoor |
| `available_equipment` | JSON | list |
| `injury_history` | Text | |
| `medical_conditions` | Text | |
| `notification_email` | Email | where daily summaries are sent |
| `onboarding_completed` | Bool | |
| `additional_comments` | Text | nullable |

---

### Fitness

**`FitnessPlan`**
| Field | Type | Notes |
|---|---|---|
| `user` | FK → User | |
| `week_number` | Int | |
| `start_date` | Date | |
| `end_date` | Date | |
| `is_active` | Bool | only one active plan per user at a time |
| `total_workout_days` | Int | |
| `total_running_days` | Int | |
| `weekly_goal_summary` | Text | Claude's summary of the week's intent |
| `claude_reasoning` | Text | stored for adaptation context |
| `additional_comments` | Text | nullable |

**`WorkoutDay`**
| Field | Type | Notes |
|---|---|---|
| `fitness_plan` | FK | |
| `date` | Date | |
| `day_of_week` | CharField | Mon–Sun |
| `day_type` | CharField | strength/running/yoga/active_recovery/rest |
| `focus_area` | CharField | upper_body/lower_body/full_body/core/cardio |
| `estimated_duration_minutes` | Int | |
| `warmup_description` | Text | |
| `cooldown_description` | Text | |
| `notes` | Text | Claude-generated coaching notes for this day |
| `additional_comments` | Text | nullable — user-entered |

**`WorkoutExercise`**
| Field | Type | Notes |
|---|---|---|
| `workout_day` | FK | |
| `exercise_cache` | FK → ExerciseCache | nullable |
| `custom_name` | CharField | fallback if not in wger |
| `section` | CharField | warmup/main/cooldown/pre_run/post_run |
| `sets` | Int | nullable |
| `reps` | Int | nullable |
| `duration_seconds` | Int | nullable — for timed exercises |
| `distance_km` | Decimal | nullable — for running segments |
| `rest_seconds` | Int | |
| `intensity` | CharField | low/moderate/high |
| `notes` | Text | Claude-generated form tips, modifications |
| `order` | Int | sequence within the day |
| `additional_comments` | Text | nullable — user-entered |

**`RunningStrategy`** (OneToOne → WorkoutDay, only for running days)
| Field | Type | Notes |
|---|---|---|
| `run_type` | CharField | easy/interval/tempo/long_run/fartlek |
| `total_distance_km` | Decimal | |
| `total_duration_minutes` | Int | |
| `pace_target` | CharField | e.g. "5:30–6:00 min/km" |
| `structure` | JSON | e.g. `[{"phase": "warmup_walk", "duration_min": 5}, {"phase": "run", "distance_km": 3}]` |
| `heart_rate_zone` | CharField | nullable |
| `notes` | Text | Claude-generated |
| `additional_comments` | Text | nullable — user-entered |

**`WorkoutLog`** — did the user complete the day's workout?
| Field | Type | Notes |
|---|---|---|
| `user` | FK | |
| `workout_day` | FK | |
| `date` | Date | |
| `completed` | Bool | |
| `completion_percentage` | Int | 0–100 |
| `perceived_exertion` | Int | 1–10 (RPE scale) |
| `actual_duration_minutes` | Int | |
| `notes` | Text | Claude-generated, if any |
| `additional_comments` | Text | nullable — user-entered |

**`ExerciseLog`** — per-exercise detail within a workout log
| Field | Type | Notes |
|---|---|---|
| `workout_log` | FK | |
| `workout_exercise` | FK | |
| `sets_completed` | Int | |
| `reps_completed` | JSON | e.g. `[10, 10, 8]` per set |
| `weight_kg` | JSON | nullable — weight per set |
| `duration_seconds` | Int | nullable |
| `distance_km` | Decimal | nullable |
| `skipped` | Bool | |
| `skip_reason` | Text | |
| `notes` | Text | |
| `additional_comments` | Text | nullable — user-entered |

---

### Health & Nutrition

**`HealthPlan`**
| Field | Type | Notes |
|---|---|---|
| `user` | FK | |
| `week_number` | Int | |
| `start_date` | Date | |
| `end_date` | Date | |
| `is_active` | Bool | |
| `daily_calorie_target` | Int | |
| `daily_protein_g` | Int | |
| `daily_carbs_g` | Int | |
| `daily_fat_g` | Int | |
| `daily_fiber_g` | Int | |
| `daily_water_ml` | Int | |
| `claude_reasoning` | Text | |
| `additional_comments` | Text | nullable |

**`MealPlan`**
| Field | Type | Notes |
|---|---|---|
| `health_plan` | FK | |
| `day_of_week` | CharField | |
| `meal_type` | CharField | breakfast/lunch/dinner/snack_am/snack_pm |
| `meal_name` | CharField | |
| `description` | Text | |
| `calories` | Int | |
| `protein_g` | Decimal | |
| `carbs_g` | Decimal | |
| `fat_g` | Decimal | |
| `fiber_g` | Decimal | |
| `ingredients` | JSON | list |
| `preparation_notes` | Text | |
| `order` | Int | |
| `additional_comments` | Text | nullable |

**`NutritionLog`** — what the user actually ate
| Field | Type | Notes |
|---|---|---|
| `user` | FK | |
| `date` | Date | |
| `meal_type` | CharField | |
| `description` | Text | freeform — what they ate |
| `estimated_calories` | Int | nullable |
| `estimated_protein_g` | Decimal | nullable |
| `estimated_carbs_g` | Decimal | nullable |
| `estimated_fat_g` | Decimal | nullable |
| `water_ml` | Int | nullable |
| `notes` | Text | |
| `additional_comments` | Text | nullable |

**`WellnessLog`**
| Field | Type | Notes |
|---|---|---|
| `user` | FK | |
| `date` | Date | |
| `sleep_hours` | Decimal | |
| `sleep_quality` | Int | 1–5 |
| `bedtime` | Time | nullable |
| `wake_time` | Time | nullable |
| `mood_score` | Int | 1–10 |
| `stress_level` | Int | 1–10 |
| `energy_level` | Int | 1–10 |
| `mindfulness_done` | Bool | |
| `mindfulness_duration_minutes` | Int | nullable |
| `mindfulness_type` | CharField | meditation/breathing/journaling/yoga — nullable |
| `notes` | Text | |
| `additional_comments` | Text | nullable |

---

### Supporting

**`ExerciseCache`** — local copy of wger data
| Field | Type | Notes |
|---|---|---|
| `wger_id` | Int | unique |
| `name` | CharField | |
| `category` | CharField | e.g. Legs, Chest, Back |
| `primary_muscles` | JSON | |
| `secondary_muscles` | JSON | |
| `equipment` | CharField | |
| `description` | Text | |
| `gif_url` | URL | nullable |
| `video_url` | URL | nullable |
| `last_fetched` | DateTime | |

**`EmailLog`**
| Field | Type | Notes |
|---|---|---|
| `user` | FK | |
| `date` | Date | |
| `sent_at` | DateTime | |
| `status` | CharField | sent/failed |
| `fitness_status` | CharField | on_track/overshooting/underachieving/no_data |
| `health_status` | CharField | on_track/overshooting/underachieving/no_data |
| `body_preview` | Text | first 500 chars |
| `error_message` | Text | nullable |

**`PlanAdaptationLog`** — audit trail of plan changes
| Field | Type | Notes |
|---|---|---|
| `user` | FK | |
| `adaptation_type` | CharField | fitness/health |
| `previous_plan` | FK | |
| `new_plan` | FK | |
| `trigger_reason` | Text | e.g. "user consistently underperforming on leg days" |
| `claude_analysis` | Text | full Claude reasoning |
| `created_at` | DateTime | |
| `additional_comments` | Text | nullable |

---

## Section 3: Application Flow

### Onboarding
New users complete a multi-step form collecting all `UserProfile` fields. On completion, a single async Claude API call fires — sending the full user profile and returning one JSON object with two top-level keys: `fitness_plan` and `health_plan`. Django parses and writes both in a single DB transaction. If the call fails, the user sees a clear error and can retry. Neither plan is partially written.

The combined call allows Claude to align the two plans — e.g. scheduling higher carbs on heavy workout days, more protein after strength sessions, and lighter meals on rest days.

### Dashboard
Single page showing the current week at a glance:
- Today's workout (exercises, running strategy if applicable, exercise GIFs from `ExerciseCache`)
- Today's meal plan
- Wellness check-in status (sleep, mood, mindfulness)
- Weekly progress ring (days completed vs. planned)

### Logging Progress
HTMX-powered — no page reloads. User ticks off exercises, enters sets/reps/weight per exercise into `ExerciseLog`, marks the day done in `WorkoutLog`. Same for nutrition (`NutritionLog`) and wellness (`WellnessLog`). All inputs save on blur/change.

### Plan Adaptation
Runs at end of each week via a Celery task. Collects all logs for the week and sends them to Claude with the current plan. Claude analyzes patterns — missed days, low perceived exertion, skipped exercises, nutrition gaps — and generates a revised plan for the following week. Reasoning and trigger stored in `PlanAdaptationLog`. Old plans are never deleted — full history preserved in DB.

### Daily Email
Celery Beat fires every evening at a configured time (`EMAIL_SEND_TIME` env var). Pulls the day's `WorkoutLog`, `NutritionLog`, and `WellnessLog` for each user. Compares actuals against plan targets. Claude generates a short 3–4 sentence summary: what went well, what was missed, one actionable tip for tomorrow. Logged in `EmailLog` regardless of success or failure.

---

## Section 4: Claude API Integration

Claude is used in four distinct ways:

### 1. Initial Plan Generation (Onboarding)
Single async call with the full `UserProfile`. Claude returns one JSON object:
```json
{
  "fitness_plan": { ... },
  "health_plan": { ... }
}
```
Django parses and writes both plans in one transaction. System prompt and JSON schema are prompt-cached — only user profile data counts as fresh input tokens.

### 2. Weekly Plan Adaptation
Celery task sends: current plan + all logs for the week + user's original goals. Claude returns revised plan JSON for week N+1, plus `trigger_reason` and `claude_analysis` strings. Uses the same JSON schema as initial generation — same parser handles both.

### 3. Daily Email Summary
Sends Claude the day's planned vs. actual data per user. Returns plain text (3–4 sentences). Email formatting instructions are prompt-cached.

### 4. On-demand Q&A (low priority, post-launch)
Chat input on the dashboard. User can ask questions like "why did you schedule leg day twice?" or "what can I substitute for squats?". Claude has the user's current plan as context. Built after core features are stable.

**Caching strategy:** System prompts and JSON schemas use `cache_control` for prompt caching. User-specific data (profile, logs, plans) always sent fresh.

---

## Section 5: Deployment

**Platform: Railway**

| Service | Role |
|---|---|
| `web` | Django app served via Gunicorn |
| `worker` | Celery worker (same image, different start command) |
| `beat` | Celery Beat scheduler (nightly emails, weekly adaptation) |
| `postgres` | Railway-managed PostgreSQL |
| `redis` | Railway-managed Redis |

**Environment variables:**
| Variable | Description |
|---|---|
| `DJANGO_SECRET_KEY` | Generate with `python -c "from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())"` |
| `DATABASE_URL` | Auto-injected by Railway |
| `REDIS_URL` | Auto-injected by Railway |
| `ANTHROPIC_API_KEY` | From Anthropic console |
| `GMAIL_USER` | Gmail address for sending emails |
| `GMAIL_APP_PASSWORD` | Gmail app password (not account password) |
| `WGER_API_BASE_URL` | wger API base URL |
| `EMAIL_SEND_TIME` | Hour (24h) for nightly email, e.g. `21` for 9pm |

**Static files:** Served via WhiteNoise — no separate CDN needed for 2–5 users.

---

## Section 6: Error Handling & Testing

### Error Handling

- **Claude API failures (onboarding):** Show clear error, allow retry. DB transaction ensures no partial plan writes.
- **Claude API failures (adaptation):** Keep current plan active, log error. User continues on last week's plan without interruption.
- **wger API failures:** Cached exercises still shown with GIFs. New uncached exercises fall back to `custom_name`, no GIF shown.
- **Email failures:** Logged in `EmailLog` with `status=failed` and `error_message`. No automatic retry (avoids duplicate emails). Non-critical — user can check app directly.
- **Celery task failures:** Retry with exponential backoff, max 3 attempts. After 3 failures, error surfaced in Django admin.

### Testing

- **Unit tests:** Claude prompt builders (assert correct JSON schema), plan parsers (assert DB records written correctly from mock Claude responses), email content generation
- **Integration tests:** Full onboarding flow, weekly adaptation cycle, daily email task — all against a real PostgreSQL test database
- **No DB mocking:** Tests run against real PostgreSQL to catch schema and query issues early
- **External APIs mocked:** wger and Claude APIs use fixture JSON responses in tests — no real API calls, no cost
