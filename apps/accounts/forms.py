from django import forms
from django.contrib.auth.models import User
from .models import UserProfile


class RegisterForm(forms.ModelForm):
    password = forms.CharField(widget=forms.PasswordInput)
    password_confirm = forms.CharField(widget=forms.PasswordInput, label="Confirm password")

    class Meta:
        model = User
        fields = ["username", "email", "first_name", "last_name"]

    def clean(self):
        cleaned = super().clean()
        if cleaned.get("password") != cleaned.get("password_confirm"):
            raise forms.ValidationError("Passwords do not match.")
        return cleaned


class OnboardingStep1Form(forms.ModelForm):
    class Meta:
        model = UserProfile
        fields = ["height_cm", "weight_kg", "gender", "date_of_birth",
                  "fitness_experience", "primary_goal", "additional_comments"]
        widgets = {"date_of_birth": forms.DateInput(attrs={"type": "date"})}


class OnboardingStep2Form(forms.ModelForm):
    preferred_workout_days = forms.MultipleChoiceField(
        choices=[(d, d) for d in ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]],
        widget=forms.CheckboxSelectMultiple,
    )

    available_equipment = forms.CharField(
        required=False,
        help_text="Comma-separated, e.g. dumbbells, resistance bands",
        widget=forms.TextInput,
    )

    def clean_available_equipment(self):
        val = self.cleaned_data.get("available_equipment", "")
        return [v.strip() for v in val.split(",") if v.strip()]

    class Meta:
        model = UserProfile
        fields = ["workout_days_per_week", "preferred_workout_days", "running_days_per_week",
                  "workout_location", "available_equipment", "injury_history",
                  "medical_conditions", "wake_time", "sleep_time", "work_schedule",
                  "daily_routine"]
        widgets = {
            "wake_time": forms.TimeInput(attrs={"type": "time"}),
            "sleep_time": forms.TimeInput(attrs={"type": "time"}),
        }


class OnboardingStep3Form(forms.ModelForm):
    food_allergies = forms.CharField(
        required=False,
        help_text="Comma-separated, e.g. gluten, dairy",
        widget=forms.TextInput,
    )

    def clean_food_allergies(self):
        val = self.cleaned_data.get("food_allergies", "")
        return [v.strip() for v in val.split(",") if v.strip()]

    class Meta:
        model = UserProfile
        fields = ["diet_type", "food_allergies", "food_preferences", "notification_email"]


class ProfileEditForm(forms.ModelForm):
    preferred_workout_days = forms.MultipleChoiceField(
        choices=[(d, d) for d in ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]],
        widget=forms.CheckboxSelectMultiple,
    )
    available_equipment = forms.CharField(
        required=False,
        help_text="Comma-separated, e.g. dumbbells, resistance bands",
        widget=forms.TextInput,
    )
    food_allergies = forms.CharField(
        required=False,
        help_text="Comma-separated, e.g. gluten, dairy",
        widget=forms.TextInput,
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if self.instance.pk:
            self.initial["preferred_workout_days"] = self.instance.preferred_workout_days
            self.initial["available_equipment"] = ", ".join(self.instance.available_equipment or [])
            self.initial["food_allergies"] = ", ".join(self.instance.food_allergies or [])

    def clean_available_equipment(self):
        val = self.cleaned_data.get("available_equipment", "")
        return [v.strip() for v in val.split(",") if v.strip()]

    def clean_food_allergies(self):
        val = self.cleaned_data.get("food_allergies", "")
        return [v.strip() for v in val.split(",") if v.strip()]

    # additional_comments excluded per spec — users cannot edit it here
    class Meta:
        model = UserProfile
        fields = [
            "height_cm", "weight_kg", "gender", "date_of_birth",
            "fitness_experience", "primary_goal",
            "diet_type", "food_allergies", "food_preferences",
            "daily_routine", "wake_time", "sleep_time", "work_schedule",
            "workout_days_per_week", "preferred_workout_days", "running_days_per_week",
            "workout_location", "available_equipment",
            "injury_history", "medical_conditions",
            "notification_email",
        ]
        widgets = {
            "date_of_birth": forms.DateInput(attrs={"type": "date"}),
            "wake_time": forms.TimeInput(attrs={"type": "time"}),
            "sleep_time": forms.TimeInput(attrs={"type": "time"}),
        }
