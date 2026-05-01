from django.contrib import admin
from .models import HealthPlan, MealPlan, NutritionLog, WellnessLog
admin.site.register(HealthPlan)
admin.site.register(MealPlan)
admin.site.register(NutritionLog)
admin.site.register(WellnessLog)
