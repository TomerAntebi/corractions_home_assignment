"""Streamlit entry point — configures the page and wires dashboard tabs to loaded data."""

import streamlit as st

from dashboard.application_data import load_application_data
from dashboard.tab_views import (
    render_data_quality_tab,
    render_driver_behavior_tab,
    render_forward_driving_tab,
    render_reverse_driving_tab,
    render_session_data_tab,
)


def main():
    st.set_page_config(
        page_title="Field Test Analytics",
        layout="wide",
    )
    st.title("Field Test Analytics")

    application_data = load_application_data()

    tab1, tab2, tab3, tab4, tab5 = st.tabs(
        [
            "Session Data",
            "Forward Driving",
            "Reverse Driving",
            "Driver Behavior",
            "Data Quality",
        ]
    )

    with tab1:
        render_session_data_tab(application_data)

    with tab2:
        render_forward_driving_tab(application_data)

    with tab3:
        render_reverse_driving_tab(application_data)

    with tab4:
        render_driver_behavior_tab(application_data)

    with tab5:
        render_data_quality_tab(application_data)


if __name__ == "__main__":
    main()
