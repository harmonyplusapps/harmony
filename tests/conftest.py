import pytest
from django.contrib.auth.models import User
from datetime import date


@pytest.fixture
def base_user(db):
    return User.objects.create_user(username="base", password="testpass123", email="base@example.com")
