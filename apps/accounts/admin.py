from django.contrib import admin
from .models import UserProfile


@admin.register(UserProfile)
class UserProfileAdmin(admin.ModelAdmin):
    list_display = ["user", "fitness_experience", "onboarding_completed"]
    list_filter = ["onboarding_completed", "fitness_experience"]
