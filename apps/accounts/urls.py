from django.urls import path
from . import views

urlpatterns = [
    path("login/", views.login_view, name="login"),
    path("logout/", views.logout_view, name="logout"),
    path("register/", views.register_view, name="register"),
    path("onboarding/1/", views.onboarding_step1, name="onboarding_step1"),
    path("onboarding/2/", views.onboarding_step2, name="onboarding_step2"),
    path("onboarding/3/", views.onboarding_step3, name="onboarding_step3"),
    path("onboarding/generating/", views.onboarding_generating, name="onboarding_generating"),
]
