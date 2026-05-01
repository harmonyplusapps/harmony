from django.db import models
from django.contrib.auth.models import User


class PlanAdaptationLog(models.Model):
    ADAPTATION_TYPE_CHOICES = [("fitness", "Fitness"), ("health", "Health")]

    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="adaptation_logs")
    adaptation_type = models.CharField(max_length=10, choices=ADAPTATION_TYPE_CHOICES)
    previous_plan_id = models.IntegerField()
    new_plan_id = models.IntegerField()
    trigger_reason = models.TextField()
    claude_analysis = models.TextField()
    additional_comments = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]
