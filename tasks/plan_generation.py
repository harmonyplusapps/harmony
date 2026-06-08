import asyncio
from celery import shared_task
from django.contrib.auth.models import User
from services.claude.plan_generator import generate_initial_plans


@shared_task(bind=True)
def generate_plan_task(self, user_id):
    user = User.objects.get(id=user_id)
    asyncio.run(generate_initial_plans(user))
    profile = user.profile
    profile.onboarding_completed = True
    profile.save()
