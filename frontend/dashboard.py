"""
Streamlit dashboard entrypoint.

This file orchestrates data loading and delegates section rendering so the page
flow stays easy to scan during review.
"""

import requests
import streamlit as st
from typing import cast

import api_client
from dashboard.helpers import JsonObject
from dashboard.sections import (
    render_data_quality_breakdown,
    render_driving_behavior,
    render_driving_analytics_home,
    render_measurements_table,
    render_problem_rows,
    render_session_information,
    render_validation_breakdown,
)


st.set_page_config(page_title="Field Test Analytics Dashboard", layout="wide")
st.title("Field Test Analytics Dashboard")

try:
    sessions = api_client.get_sessions()
except requests.exceptions.RequestException:
    st.error("Failed to load sessions.")
    st.stop()

if not sessions:
    st.info("No sessions exist.")
    st.stop()

session_labels = {
    str(session["id"]): str(session["sessionId"])
    for session in sessions
}

with st.sidebar:
    st.header("Session")
    selected_session_id = st.selectbox(
        "Select Session",
        options=list(session_labels.keys()),
        format_func=lambda session_id: session_labels[session_id],
        label_visibility="collapsed",
    )

try:
    dashboard_response = api_client.get_session_dashboard(selected_session_id)
except requests.exceptions.RequestException:
    st.error("Failed to load dashboard data.")
    st.stop()

session = cast(JsonObject, dashboard_response["session"])
quality_report = cast(JsonObject, dashboard_response["qualityReport"])
analytics = cast(JsonObject, dashboard_response["analytics"])
measurements = cast(list[JsonObject], dashboard_response["measurements"])

render_session_information(session)

st.divider()

render_driving_analytics_home(analytics)

st.divider()

render_data_quality_breakdown(quality_report)
render_validation_breakdown(quality_report)

st.divider()

render_driving_behavior(
    analytics,
    measurements,
)

st.divider()

render_problem_rows(measurements)
render_measurements_table(measurements)
