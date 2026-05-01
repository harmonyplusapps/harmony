from django.db import models
from django.contrib.auth.models import User


class EmailLog(models.Model):
    STATUS_CHOICES = [("sent", "Sent"), ("failed", "Failed")]
    ASSESSMENT_CHOICES = [
        ("on_track", "On Track"),
        ("overshooting", "Overshooting"),
        ("underachieving", "Underachieving"),
        ("no_data", "No Data"),
    ]

    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="email_logs")
    date = models.DateField()
    sent_at = models.DateTimeField(auto_now_add=True)
    status = models.CharField(max_length=10, choices=STATUS_CHOICES)
    fitness_status = models.CharField(max_length=20, choices=ASSESSMENT_CHOICES, default="no_data")
    health_status = models.CharField(max_length=20, choices=ASSESSMENT_CHOICES, default="no_data")
    body_preview = models.TextField()
    error_message = models.TextField(blank=True)

    class Meta:
        unique_together = ["user", "date"]
