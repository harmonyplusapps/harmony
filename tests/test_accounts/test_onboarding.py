import pytest
from django.urls import reverse
from django.contrib.auth.models import User

@pytest.mark.django_db
def test_register_creates_user(client):
    resp = client.post(reverse("register"), {
        "username": "newuser",
        "email": "new@example.com",
        "first_name": "New",
        "last_name": "User",
        "password": "securepass123",
        "password_confirm": "securepass123",
    })
    assert resp.status_code == 302
    assert User.objects.filter(username="newuser").exists()
    assert reverse("onboarding_step1") in resp["Location"]


@pytest.mark.django_db
def test_register_password_mismatch_shows_error(client):
    resp = client.post(reverse("register"), {
        "username": "newuser2",
        "email": "new2@example.com",
        "password": "pass1",
        "password_confirm": "pass2",
    })
    assert resp.status_code == 200
    assert "Passwords do not match" in resp.content.decode()


@pytest.mark.django_db
def test_login_valid_credentials(client, base_user):
    resp = client.post(reverse("login"), {
        "username": "base",
        "password": "testpass123",
    })
    assert resp.status_code == 302
    assert reverse("dashboard") in resp["Location"]


@pytest.mark.django_db
def test_login_invalid_credentials(client, base_user):
    resp = client.post(reverse("login"), {
        "username": "base",
        "password": "wrongpass",
    })
    assert resp.status_code == 200
    assert "Invalid username or password" in resp.content.decode()


@pytest.mark.django_db
def test_dashboard_redirects_if_not_onboarded(client, base_user):
    client.login(username="base", password="testpass123")
    resp = client.get(reverse("dashboard"))
    assert resp.status_code == 302
    assert "onboarding" in resp["Location"]


@pytest.mark.django_db
def test_dashboard_loads_if_onboarded(client, base_user, complete_profile):
    client.login(username="base", password="testpass123")
    resp = client.get(reverse("dashboard"))
    assert resp.status_code == 200


@pytest.mark.django_db
def test_dashboard_redirects_unauthenticated(client):
    resp = client.get(reverse("dashboard"))
    assert resp.status_code == 302
    assert "login" in resp["Location"]
