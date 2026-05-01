from django.db import models
from django.contrib.auth.models import User


class UserProfile(models.Model):
    GENDER_CHOICES = [("male", "Male"), ("female", "Female"), ("other", "Other")]
    EXPERIENCE_CHOICES = [
        ("beginner", "Beginner"),
        ("intermediate", "Intermediate"),
        ("advanced", "Advanced"),
    ]
    DIET_CHOICES = [
        ("omnivore", "Omnivore"),
        ("vegetarian", "Vegetarian"),
        ("vegan", "Vegan"),
        ("keto", "Keto"),
        ("paleo", "Paleo"),
        ("other", "Other"),
    ]
    WORK_SCHEDULE_CHOICES = [
        ("9-5", "9–5"),
        ("shift", "Shift work"),
        ("flexible", "Flexible"),
    ]
    LOCATION_CHOICES = [("gym", "Gym"), ("home", "Home"), ("outdoor", "Outdoor")]

    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name="profile")
    height_cm = models.DecimalField(max_digits=5, decimal_places=1)
    weight_kg = models.DecimalField(max_digits=5, decimal_places=1)
    gender = models.CharField(max_length=10, choices=GENDER_CHOICES)
    date_of_birth = models.DateField()
    fitness_experience = models.CharField(max_length=20, choices=EXPERIENCE_CHOICES)
    primary_goal = models.TextField()
    diet_type = models.CharField(max_length=20, choices=DIET_CHOICES)
    food_allergies = models.JSONField(default=list)
    food_preferences = models.TextField(blank=True)
    daily_routine = models.TextField(blank=True)
    wake_time = models.TimeField()
    sleep_time = models.TimeField()
    work_schedule = models.CharField(max_length=20, choices=WORK_SCHEDULE_CHOICES)
    workout_days_per_week = models.IntegerField()
    preferred_workout_days = models.JSONField(default=list)
    running_days_per_week = models.IntegerField(default=0)
    workout_location = models.CharField(max_length=20, choices=LOCATION_CHOICES)
    available_equipment = models.JSONField(default=list)
    injury_history = models.TextField(blank=True)
    medical_conditions = models.TextField(blank=True)
    notification_email = models.EmailField()
    onboarding_completed = models.BooleanField(default=False)
    additional_comments = models.TextField(blank=True)

    def __str__(self):
        return f"{self.user.username} profile"
