from django.contrib import admin
from .models import FitnessPlan, WorkoutDay, WorkoutExercise, RunningStrategy, WorkoutLog, ExerciseLog

@admin.register(FitnessPlan)
class FitnessPlanAdmin(admin.ModelAdmin):
    list_display = ["user", "week_number", "start_date", "is_active"]
    list_filter = ["is_active"]

admin.site.register(WorkoutDay)
admin.site.register(WorkoutExercise)
admin.site.register(RunningStrategy)
admin.site.register(WorkoutLog)
admin.site.register(ExerciseLog)
