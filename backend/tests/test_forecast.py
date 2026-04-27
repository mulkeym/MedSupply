"""Tests for the forecast engine."""

from backend.app.services.forecast import run_forecast
from backend.app.schemas import ForecastRequest
from backend.app.database import initialize_database


def setup_module():
    initialize_database()
