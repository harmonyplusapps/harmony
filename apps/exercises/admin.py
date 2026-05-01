from django.contrib import admin
from .models import ExerciseCache


@admin.register(ExerciseCache)
class ExerciseCacheAdmin(admin.ModelAdmin):
    list_display = ["name", "category", "equipment", "last_fetched"]
    search_fields = ["name"]
