# Harmony

A Django web app that generates personalized weekly fitness and nutrition plans using Claude AI, tracks daily progress, and adapts plans week-over-week based on logged data. Users receive a nightly email summary.

## Features

- **AI-generated plans** — Claude generates a personalized weekly workout and nutrition plan based on your goals, fitness level, diet preferences, schedule, and equipment
- **3-step onboarding** — collects personal, fitness, and health info to tailor the plan
- **Daily progress logging** — log workouts, meals, and wellness check-ins via HTMX-powered dashboard (no page reloads)
- **Weekly plan adaptation** — Celery task re-evaluates your progress each Monday and generates an updated plan
- **Nightly email summary** — daily digest of your progress sent each evening via Gmail SMTP
- **Exercise data** — exercise info sourced from the wger API, cached locally in the database

## Tech Stack

| Layer | Technology |
|---|---|
| Backend | Django 5.1 (Python 3.13) |
| Frontend | HTMX + Alpine.js |
| Database | PostgreSQL |
| AI | Anthropic Claude API |
| Exercise data | wger API (cached in DB) |
| Background jobs | Celery 5 + Redis |
| Email | Gmail SMTP |
| Deployment | Railway |

## Getting Started

### Prerequisites

- Python 3.12+
- PostgreSQL
- Redis
- An [Anthropic API key](https://console.anthropic.com/)
- A Gmail account with an [App Password](https://support.google.com/accounts/answer/185833)

### Local setup

```bash
git clone https://github.com/lekhasameer/harmony.git
cd harmony

python -m venv .venv
source .venv/bin/activate

pip install -r requirements.txt

cp .env.example .env
# Fill in your values in .env

python manage.py migrate
python manage.py createsuperuser
python manage.py runserver
```

### Environment variables

| Variable | Description |
|---|---|
| `DJANGO_SECRET_KEY` | Django secret key |
| `DATABASE_URL` | PostgreSQL connection URL |
| `REDIS_URL` | Redis connection URL |
| `ANTHROPIC_API_KEY` | Anthropic API key |
| `GMAIL_USER` | Gmail address for sending emails |
| `GMAIL_APP_PASSWORD` | Gmail app password |
| `WGER_API_BASE_URL` | wger API base URL (default: `https://wger.de/api/v2`) |
| `EMAIL_SEND_TIME` | Hour (UTC) to send nightly emails (default: `21`) |

### Running background workers (development)

```bash
# In separate terminals:
celery -A harmony worker --loglevel=info
celery -A harmony beat --loglevel=info
```

### Running tests

```bash
pytest -v
```

Tests require a running PostgreSQL instance (no mocking — real DB).

## Deployment (Railway)

1. Push repo to GitHub
2. Create a new Railway project → Deploy from GitHub repo
3. Add **PostgreSQL** and **Redis** services, copy their URLs to env vars
4. Set all environment variables listed above, plus:
   - `DJANGO_SETTINGS_MODULE=harmony.settings.production`
   - `ALLOWED_HOSTS=<your-railway-domain>`
5. Run post-deploy commands via Railway shell:
   ```bash
   python manage.py migrate
   python manage.py createsuperuser
   ```

## Project Structure

```
harmony/
├── apps/
│   ├── accounts/       # UserProfile, auth, onboarding
│   ├── exercises/      # ExerciseCache (wger data)
│   ├── fitness/        # FitnessPlan, WorkoutDay, WorkoutLog
│   ├── health/         # HealthPlan, MealPlan, NutritionLog, WellnessLog
│   ├── plans/          # PlanAdaptationLog
│   └── notifications/  # EmailLog
├── services/
│   ├── claude/         # Claude API client, plan generator, parser, adapter
│   └── wger/           # wger API client
├── tasks/              # Celery tasks (email, plan adaptation)
├── templates/          # Django templates
└── tests/              # pytest test suite
```
