from .base import *
import os
from celery.schedules import crontab

DEBUG = False
_hosts = os.environ.get("ALLOWED_HOSTS", "")
ALLOWED_HOSTS = [h for h in _hosts.split(",") if h]

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
