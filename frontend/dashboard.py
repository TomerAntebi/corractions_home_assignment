"""
Streamlit dashboard entrypoint.

This file orchestrates data loading and delegates section rendering so the page
flow stays easy to scan during review.
"""

import requests
import streamlit as st
from concurrent.futures import ThreadPoolExecutor
from typing import cast

import api_client
from dashboard.helpers import JsonObject
from dashboard.sections import (
    render_data_quality_breakdown,
    render_driving_visualization,
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
    str(session["id"]): str(session["metadata"]["session_id"])
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
    with ThreadPoolExecutor(max_workers=2) as executor:
        dashboard_future = executor.submit(
            api_client.get_session_dashboard,
            selected_session_id,
        )
        measurements_future = executor.submit(
            api_client.get_session_measurements,
            selected_session_id,
        )
        dashboard_response = dashboard_future.result()
        measurements = measurements_future.result()
except requests.exceptions.RequestException:
    st.error("Failed to load dashboard data.")
    st.stop()

session = cast(JsonObject, dashboard_response["session"])
quality_report = cast(JsonObject, dashboard_response["qualityReport"])
analytics = cast(JsonObject, dashboard_response["analytics"])

render_session_information(session)

st.divider()

render_driving_analytics_home(analytics)

st.divider()

render_driving_visualization(analytics)

st.divider()

render_data_quality_breakdown(quality_report)
render_validation_breakdown(quality_report)

st.divider()

render_problem_rows(measurements)
render_measurements_table(measurements)
