from django.db import models
from django.contrib.auth.models import User
from apps.exercises.models import ExerciseCache


class FitnessPlan(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="fitness_plans")
    week_number = models.IntegerField()
    start_date = models.DateField()
    end_date = models.DateField()
    is_active = models.BooleanField(default=True)
    total_workout_days = models.IntegerField()
    total_running_days = models.IntegerField(default=0)
    weekly_goal_summary = models.TextField()
    claude_reasoning = models.TextField()
    additional_comments = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-week_number"]

    def __str__(self):
        return f"{self.user.username} – Week {self.week_number}"


class WorkoutDay(models.Model):
    DAY_TYPE_CHOICES = [
        ("strength", "Strength"),
        ("running", "Running"),
        ("yoga", "Yoga"),
        ("active_recovery", "Active Recovery"),
        ("rest", "Rest"),
    ]
    FOCUS_CHOICES = [
        ("upper_body", "Upper Body"),
        ("lower_body", "Lower Body"),
        ("full_body", "Full Body"),
        ("core", "Core"),
        ("cardio", "Cardio"),
    ]

    fitness_plan = models.ForeignKey(FitnessPlan, on_delete=models.CASCADE, related_name="workout_days")
    date = models.DateField()
    day_of_week = models.CharField(max_length=10)
    day_type = models.CharField(max_length=20, choices=DAY_TYPE_CHOICES)
    focus_area = models.CharField(max_length=20, choices=FOCUS_CHOICES)
    estimated_duration_minutes = models.IntegerField()
    warmup_description = models.TextField(blank=True)
    cooldown_description = models.TextField(blank=True)
    notes = models.TextField(blank=True)
    additional_comments = models.TextField(blank=True)

    class Meta:
        ordering = ["date"]

    def __str__(self):
        return f"{self.day_of_week} – {self.day_type}"


class RunningStrategy(models.Model):
    RUN_TYPE_CHOICES = [
        ("easy", "Easy"),
        ("interval", "Interval"),
        ("tempo", "Tempo"),
        ("long_run", "Long Run"),
        ("fartlek", "Fartlek"),
    ]

    workout_day = models.OneToOneField(WorkoutDay, on_delete=models.CASCADE, related_name="running_strategy")
    run_type = models.CharField(max_length=20, choices=RUN_TYPE_CHOICES)
    total_distance_km = models.DecimalField(max_digits=5, decimal_places=2)
    total_duration_minutes = models.IntegerField()
    pace_target = models.CharField(max_length=50)
    structure = models.JSONField(default=list)
    heart_rate_zone = models.CharField(max_length=20, blank=True)
    notes = models.TextField(blank=True)
    additional_comments = models.TextField(blank=True)


class WorkoutExercise(models.Model):
    SECTION_CHOICES = [
        ("warmup", "Warmup"),
        ("main", "Main"),
        ("cooldown", "Cooldown"),
        ("pre_run", "Pre-Run"),
        ("post_run", "Post-Run"),
    ]
    INTENSITY_CHOICES = [("low", "Low"), ("moderate", "Moderate"), ("high", "High")]

    workout_day = models.ForeignKey(WorkoutDay, on_delete=models.CASCADE, related_name="exercises")
    exercise_cache = models.ForeignKey(ExerciseCache, on_delete=models.SET_NULL, null=True, blank=True)
    custom_name = models.CharField(max_length=200, blank=True)
    section = models.CharField(max_length=20, choices=SECTION_CHOICES)
    sets = models.IntegerField(null=True, blank=True)
    reps = models.IntegerField(null=True, blank=True)
    duration_seconds = models.IntegerField(null=True, blank=True)
    distance_km = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True)
    rest_seconds = models.IntegerField(default=60)
    intensity = models.CharField(max_length=10, choices=INTENSITY_CHOICES)
    notes = models.TextField(blank=True)
    order = models.IntegerField(default=0)
    additional_comments = models.TextField(blank=True)

    class Meta:
        ordering = ["order"]

    @property
    def display_name(self):
        if self.exercise_cache:
            return self.exercise_cache.name
        return self.custom_name


class WorkoutLog(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="workout_logs")
    workout_day = models.ForeignKey(WorkoutDay, on_delete=models.CASCADE, related_name="logs")
    date = models.DateField()
    completed = models.BooleanField(default=False)
    completion_percentage = models.IntegerField(default=0)
    perceived_exertion = models.IntegerField(null=True, blank=True)
    actual_duration_minutes = models.IntegerField(null=True, blank=True)
    notes = models.TextField(blank=True)
    additional_comments = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ["user", "workout_day"]


class ExerciseLog(models.Model):
    workout_log = models.ForeignKey(WorkoutLog, on_delete=models.CASCADE, related_name="exercise_logs")
    workout_exercise = models.ForeignKey(WorkoutExercise, on_delete=models.CASCADE)
    sets_completed = models.IntegerField(default=0)
    reps_completed = models.JSONField(default=list)
    weight_kg = models.JSONField(default=list)
    duration_seconds = models.IntegerField(null=True, blank=True)
    distance_km = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True)
    skipped = models.BooleanField(default=False)
    skip_reason = models.TextField(blank=True)
    notes = models.TextField(blank=True)
    additional_comments = models.TextField(blank=True)
