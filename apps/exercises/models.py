from django.db import models


class ExerciseCache(models.Model):
    wger_id = models.IntegerField(unique=True)
    name = models.CharField(max_length=200)
    category = models.CharField(max_length=100)
    primary_muscles = models.JSONField(default=list)
    secondary_muscles = models.JSONField(default=list)
    equipment = models.CharField(max_length=100, blank=True)
    description = models.TextField(blank=True)
    gif_url = models.URLField(blank=True)
    video_url = models.URLField(blank=True)
    last_fetched = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.name
