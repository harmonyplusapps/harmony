import asyncio
from celery import shared_task
from django.contrib.auth.models import User
from services.claude.plan_adapter import adapt_plans_for_user


@shared_task(bind=True, max_retries=3, default_retry_delay=600)
def adapt_plans(self):
    users = User.objects.filter(is_active=True).select_related("profile")
    for user in users:
        if not hasattr(user, "profile") or not user.profile.onboarding_completed:
            continue
        try:
            asyncio.run(adapt_plans_for_user(user))
        except Exception as exc:
            self.retry(exc=exc)
