from .base import *
import os
from celery.schedules import crontab

DEBUG = False
_hosts = os.environ.get("ALLOWED_HOSTS", "")
_railway_domain = os.environ.get("RAILWAY_PUBLIC_DOMAIN", "")
ALLOWED_HOSTS = [h.strip() for h in _hosts.split(",") if h.strip()]
if _railway_domain and _railway_domain not in ALLOWED_HOSTS:
    ALLOWED_HOSTS.append(_railway_domain)
CSRF_TRUSTED_ORIGINS = [f"https://{h}" for h in ALLOWED_HOSTS if h]

CELERY_BEAT_SCHEDULE = {
    "nightly-email": {
        "task": "tasks.email.send_daily_emails",
        "schedule": crontab(hour=EMAIL_SEND_TIME, minute=0),
    },
    "weekly-adaptation": {
        "task": "tasks.adaptation.adapt_plans",
        "schedule": crontab(hour=6, minute=0, day_of_week="monday"),
    },
}
