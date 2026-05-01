import logging

from django.contrib.auth import login, logout, authenticate
from django.contrib.auth.decorators import login_required
from django.shortcuts import render, redirect, get_object_or_404
from django.views.decorators.http import require_POST
from .forms import RegisterForm, OnboardingStep1Form, OnboardingStep2Form, OnboardingStep3Form
from .models import UserProfile
import asyncio
from services.claude.plan_generator import generate_initial_plans

logger = logging.getLogger(__name__)


def register_view(request):
    if request.method == "POST":
        form = RegisterForm(request.POST)
        if form.is_valid():
            user = form.save(commit=False)
            user.set_password(form.cleaned_data["password"])
            user.save()
            login(request, user)
            return redirect("onboarding_step1")
    else:
        form = RegisterForm()
    return render(request, "accounts/register.html", {"form": form})


def login_view(request):
    error = None
    if request.method == "POST":
        user = authenticate(
            request,
            username=request.POST.get("username"),
            password=request.POST.get("password"),
        )
        if user:
            login(request, user)
            return redirect("dashboard")
        error = "Invalid username or password."
    return render(request, "accounts/login.html", {"error": error})


@require_POST
def logout_view(request):
    logout(request)
    return redirect("login")


@login_required
def onboarding_step1(request):
    profile, _ = UserProfile.objects.get_or_create(
        user=request.user,
        defaults={"height_cm": 0, "weight_kg": 0, "gender": "other",
                  "date_of_birth": "2000-01-01", "fitness_experience": "beginner",
                  "primary_goal": "", "diet_type": "omnivore", "wake_time": "07:00",
                  "sleep_time": "23:00", "work_schedule": "9-5",
                  "workout_days_per_week": 3, "preferred_workout_days": [],
                  "workout_location": "home", "notification_email": request.user.email or ""}
    )
    if request.method == "POST":
        form = OnboardingStep1Form(request.POST, instance=profile)
        if form.is_valid():
            form.save()
            return redirect("onboarding_step2")
    else:
        form = OnboardingStep1Form(instance=profile)
    return render(request, "accounts/onboarding/step1_personal.html", {"form": form, "step": 1})


@login_required
def onboarding_step2(request):
    profile = get_object_or_404(UserProfile, user=request.user)
    if request.method == "POST":
        form = OnboardingStep2Form(request.POST, instance=profile)
        if form.is_valid():
            obj = form.save(commit=False)
            obj.preferred_workout_days = form.cleaned_data["preferred_workout_days"]
            obj.save()
            return redirect("onboarding_step3")
    else:
        form = OnboardingStep2Form(instance=profile)
    return render(request, "accounts/onboarding/step2_fitness.html", {"form": form, "step": 2})


@login_required
def onboarding_step3(request):
    profile = get_object_or_404(UserProfile, user=request.user)
    if request.method == "POST":
        form = OnboardingStep3Form(request.POST, instance=profile)
        if form.is_valid():
            form.save()
            return redirect("onboarding_generating")
    else:
        form = OnboardingStep3Form(instance=profile)
    return render(request, "accounts/onboarding/step3_health.html", {"form": form, "step": 3})


@login_required
def onboarding_generating(request):
    profile = get_object_or_404(UserProfile, user=request.user)
    if request.method == "POST":
        try:
            asyncio.run(generate_initial_plans(request.user))
            profile.onboarding_completed = True
            profile.save()
            return redirect("dashboard")
        except Exception as e:
            logger.exception("Plan generation failed for user %s", request.user.id)
            return render(request, "accounts/onboarding/generating.html",
                          {"error": "Plan generation failed. Please try again."})
    return render(request, "accounts/onboarding/generating.html", {})
