from .base import *
import os
from celery.schedules import crontab

DEBUG = False
ALLOWED_HOSTS = os.environ.get("ALLOWED_HOSTS", "").split(",")

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
