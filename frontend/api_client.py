"""
Small HTTP client for the Streamlit dashboard.

The dashboard reads already-prepared API responses and keeps request handling
isolated from rendering code.
"""

import os
from typing import cast

import requests

from dashboard.helpers import JsonObject


API_BASE_URL = os.getenv("API_BASE_URL", "http://localhost:8000")
REQUEST_TIMEOUT_SECONDS = 10


def get_sessions() -> list[JsonObject]:
    response = requests.get(
        f"{API_BASE_URL}/api/v1/sessions",
        timeout=REQUEST_TIMEOUT_SECONDS,
    )
    response.raise_for_status()

    return cast(list[JsonObject], response.json())


def get_session_dashboard(session_id: str) -> JsonObject:
    response = requests.get(
        f"{API_BASE_URL}/api/v1/sessions/{session_id}/dashboard",
        timeout=REQUEST_TIMEOUT_SECONDS,
    )
    response.raise_for_status()

    return cast(JsonObject, response.json())
