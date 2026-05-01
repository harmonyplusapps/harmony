from django.db import models
from django.contrib.auth.models import User


class HealthPlan(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="health_plans")
    week_number = models.IntegerField()
    start_date = models.DateField()
    end_date = models.DateField()
    is_active = models.BooleanField(default=True)
    daily_calorie_target = models.IntegerField()
    daily_protein_g = models.IntegerField()
    daily_carbs_g = models.IntegerField()
    daily_fat_g = models.IntegerField()
    daily_fiber_g = models.IntegerField()
    daily_water_ml = models.IntegerField()
    claude_reasoning = models.TextField()
    additional_comments = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-week_number"]


class MealPlan(models.Model):
    MEAL_TYPE_CHOICES = [
        ("breakfast", "Breakfast"),
        ("lunch", "Lunch"),
        ("dinner", "Dinner"),
        ("snack_am", "AM Snack"),
        ("snack_pm", "PM Snack"),
    ]

    health_plan = models.ForeignKey(HealthPlan, on_delete=models.CASCADE, related_name="meal_plans")
    day_of_week = models.CharField(max_length=10)
    meal_type = models.CharField(max_length=20, choices=MEAL_TYPE_CHOICES)
    meal_name = models.CharField(max_length=200)
    description = models.TextField()
    calories = models.IntegerField()
    protein_g = models.DecimalField(max_digits=6, decimal_places=1)
    carbs_g = models.DecimalField(max_digits=6, decimal_places=1)
    fat_g = models.DecimalField(max_digits=6, decimal_places=1)
    fiber_g = models.DecimalField(max_digits=6, decimal_places=1)
    ingredients = models.JSONField(default=list)
    preparation_notes = models.TextField(blank=True)
    order = models.IntegerField(default=0)
    additional_comments = models.TextField(blank=True)

    class Meta:
        ordering = ["day_of_week", "order"]


class NutritionLog(models.Model):
    MEAL_TYPE_CHOICES = MealPlan.MEAL_TYPE_CHOICES

    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="nutrition_logs")
    date = models.DateField()
    meal_type = models.CharField(max_length=20, choices=MEAL_TYPE_CHOICES)
    description = models.TextField()
    estimated_calories = models.IntegerField(null=True, blank=True)
    estimated_protein_g = models.DecimalField(max_digits=6, decimal_places=1, null=True, blank=True)
    estimated_carbs_g = models.DecimalField(max_digits=6, decimal_places=1, null=True, blank=True)
    estimated_fat_g = models.DecimalField(max_digits=6, decimal_places=1, null=True, blank=True)
    water_ml = models.IntegerField(null=True, blank=True)
    notes = models.TextField(blank=True)
    additional_comments = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)


class WellnessLog(models.Model):
    MINDFULNESS_TYPE_CHOICES = [
        ("meditation", "Meditation"),
        ("breathing", "Breathing"),
        ("journaling", "Journaling"),
        ("yoga", "Yoga"),
    ]

    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="wellness_logs")
    date = models.DateField()
    sleep_hours = models.DecimalField(max_digits=4, decimal_places=1)
    sleep_quality = models.IntegerField()
    bedtime = models.TimeField(null=True, blank=True)
    wake_time = models.TimeField(null=True, blank=True)
    mood_score = models.IntegerField()
    stress_level = models.IntegerField()
    energy_level = models.IntegerField()
    mindfulness_done = models.BooleanField(default=False)
    mindfulness_duration_minutes = models.IntegerField(null=True, blank=True)
    mindfulness_type = models.CharField(max_length=20, choices=MINDFULNESS_TYPE_CHOICES, blank=True)
    notes = models.TextField(blank=True)
    additional_comments = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ["user", "date"]
