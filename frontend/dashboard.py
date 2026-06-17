"""
Streamlit dashboard entrypoint.

This file orchestrates data loading and delegates section rendering so the page
flow stays easy to scan during review.
"""

import requests
import streamlit as st

import api_client
from dashboard.helpers import get_json_object, get_json_objects
from dashboard.sections import (
    render_analytics_statistics,
    render_data_quality_breakdown,
    render_driving_behavior,
    render_executive_summary,
    render_measurements_table,
    render_problem_rows,
    render_quality_metrics,
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
selected_session_id = st.selectbox(
    "Select Session",
    options=list(session_labels.keys()),
    format_func=lambda session_id: session_labels[session_id],
)

try:
    dashboard_response = api_client.get_session_dashboard(selected_session_id)
except requests.exceptions.RequestException:
    st.error("Failed to load dashboard data.")
    st.stop()

session = get_json_object(dashboard_response, "session")
quality_report = get_json_object(dashboard_response, "qualityReport")
analytics = get_json_object(dashboard_response, "analytics")
speed_statistics = get_json_object(analytics, "speed")
wheel_angle_statistics = get_json_object(analytics, "wheelAngle")
measurements = get_json_objects(dashboard_response, "measurements")

# Session overview
render_session_information(session)
render_problem_rows(measurements)
render_measurements_table(measurements)
render_executive_summary(quality_report, analytics)

# Data quality summary and validation details
render_quality_metrics(quality_report, analytics)
render_data_quality_breakdown(quality_report)
render_validation_breakdown(quality_report)

# Speed, steering, and reverse-driving behavior
render_analytics_statistics(speed_statistics, wheel_angle_statistics)
render_driving_behavior(
    analytics,
    speed_statistics,
    wheel_angle_statistics,
    measurements,
)
