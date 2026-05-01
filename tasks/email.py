from datetime import date
from celery import shared_task
from django.contrib.auth.models import User
from django.core.mail import send_mail
from apps.notifications.models import EmailLog
from services.claude.email_summarizer import generate_email_summary


@shared_task
def send_daily_emails():
    today = date.today()
    users = User.objects.filter(is_active=True).select_related("profile")

    for user in users:
        if not hasattr(user, "profile") or not user.profile.onboarding_completed:
            continue
        if EmailLog.objects.filter(user=user, date=today).exists():
            continue
        _send_for_user(user, today)


def _send_for_user(user, today):
    try:
        summary, fitness_status, health_status = generate_email_summary(user, today)
        send_mail(
            subject=f"Harmony Daily Check-in — {today.strftime('%A, %b %d')}",
            message=summary,
            from_email=None,
            recipient_list=[user.profile.notification_email],
        )
        EmailLog.objects.create(
            user=user,
            date=today,
            status="sent",
            fitness_status=fitness_status,
            health_status=health_status,
            body_preview=summary[:500],
        )
    except Exception as exc:
        EmailLog.objects.update_or_create(
            user=user,
            date=today,
            defaults={
                "status": "failed",
                "fitness_status": "no_data",
                "health_status": "no_data",
                "body_preview": "",
                "error_message": str(exc),
            },
        )
