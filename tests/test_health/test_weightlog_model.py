import pytest
from datetime import date
from decimal import Decimal
from django.db import IntegrityError
from django.contrib.auth.models import User
from apps.health.models import WeightLog


@pytest.fixture
def user(db):
    return User.objects.create_user(username="w", password="x", email="w@e.com")


@pytest.mark.django_db
def test_weightlog_persists(user):
    log = WeightLog.objects.create(user=user, date=date(2026, 6, 18), weight_kg=Decimal("64.5"))
    log.refresh_from_db()
    assert log.weight_kg == Decimal("64.5")


@pytest.mark.django_db
def test_weightlog_unique_per_user_date(user):
    WeightLog.objects.create(user=user, date=date(2026, 6, 18), weight_kg=Decimal("64.5"))
    with pytest.raises(IntegrityError):
        WeightLog.objects.create(user=user, date=date(2026, 6, 18), weight_kg=Decimal("65.0"))
