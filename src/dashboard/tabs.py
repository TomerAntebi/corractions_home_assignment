"""Dashboard tabs — renders session, forward/reverse driving, behavior, and data quality views."""

import streamlit as st

import dashboard.ui as ui
import visualizations as charts
from dashboard.config import ANALYTICS_NOTE, METADATA_FILE_NAME, SOURCE_FILE_NAME
from ingestion import MeasurementColumn

GEAR_TAB_CONFIG = {
    0: {
        "title_prefix": "Forward",
        "metrics_key": "forward_metrics",
        "buckets_key": "forward_steering_buckets",
    },
    1: {
        "title_prefix": "Reverse",
        "metrics_key": "reverse_metrics",
        "buckets_key": "reverse_steering_buckets",
    },
}


def render_session_data_tab(application_data):
    metadata = application_data["metadata"]
    measurement_dataframe = application_data["measurement_dataframe"]

    st.caption(
        "Session information from the metadata file and all measurements "
        "stored in the database."
    )

    st.subheader("Session Metadata")
    st.dataframe(
        ui.build_session_metadata_table(metadata), use_container_width=True, hide_index=True
    )

    st.write(f"Source CSV: `{SOURCE_FILE_NAME}`")
    st.write(f"Source metadata: `{METADATA_FILE_NAME}`")

    st.subheader("Measurements")
    st.caption(
        f"{len(measurement_dataframe)} rows stored in the database "
        "(all rows retained, including missing values)."
    )
    st.dataframe(
        ui.build_measurements_display_table(measurement_dataframe),
        use_container_width=True,
        hide_index=True,
    )


def _iter_driving_charts(analytics, analytics_dataframe, reverse_state):
    gear_config = GEAR_TAB_CONFIG[reverse_state]
    title_prefix = gear_config["title_prefix"]
    forward_gap_note = (
        " The visible gap marks the reverse-driving segment, which is excluded "
        "from forward-only charts."
        if reverse_state == 0
        else ""
    )

    yield _speed_timeline_chart(analytics_dataframe, reverse_state, title_prefix, forward_gap_note)
    yield _steering_timeline_chart(analytics_dataframe, reverse_state, title_prefix, forward_gap_note)
    yield _distribution_chart(analytics_dataframe, reverse_state, title_prefix, MeasurementColumn.SPEED, "Speed")
    yield _distribution_chart(analytics_dataframe, reverse_state, title_prefix, MeasurementColumn.WHEEL_ANGLE, "Steering")
    yield _steering_bucket_chart(analytics, reverse_state, title_prefix, gear_config["buckets_key"])


def _speed_timeline_chart(analytics_dataframe, reverse_state, title_prefix, forward_gap_note):
    title = f"{title_prefix} Speed Timeline"
    caption = (
        f"Shows how speed changes over time during {title_prefix.lower()} driving. "
        f"Each point is one second apart.{forward_gap_note}"
    )
    return title, caption, charts.plot_speed_timeline(analytics_dataframe, reverse_state, title)


def _steering_timeline_chart(analytics_dataframe, reverse_state, title_prefix, forward_gap_note):
    title = f"{title_prefix} Steering Timeline"
    caption = (
        "Shows steering angle over time. Positive and negative values indicate "
        f"turn direction.{forward_gap_note}"
    )
    return title, caption, charts.plot_steering_timeline(analytics_dataframe, reverse_state, title)


def _distribution_chart(analytics_dataframe, reverse_state, title_prefix, column, label):
    title = f"{title_prefix} {label} Distribution"
    caption = (
        "Shows how frequently each speed value appears."
        if column == MeasurementColumn.SPEED
        else "Shows how often the driver used light vs heavy steering."
    )
    xlabel = "Speed (km/h)" if column == MeasurementColumn.SPEED else "Steering angle (degrees)"
    return title, caption, charts.plot_distribution(analytics_dataframe, column, reverse_state, title, xlabel)


def _steering_bucket_chart(analytics, reverse_state, title_prefix, buckets_key):
    title = f"{title_prefix} Steering Bucket Analysis"
    chart_title = f"{title_prefix} Average Speed by Steering Intensity"
    caption = (
        "Average speed by steering intensity. Helps reveal whether the driver "
        "slows down during sharper turns."
    )
    return title, caption, charts.plot_steering_buckets(analytics[buckets_key], reverse_state, chart_title)


def render_driving_tab(application_data, reverse_state):
    analytics = application_data["analytics"]
    gear_config = GEAR_TAB_CONFIG[reverse_state]
    context_metrics = analytics[gear_config["metrics_key"]]
    analytics_dataframe = application_data["analytics_dataframe"]

    st.caption(ANALYTICS_NOTE)
    ui.render_driving_kpi_cards(context_metrics, gear_config["title_prefix"])

    for title, caption, chart in _iter_driving_charts(
        analytics, analytics_dataframe, reverse_state
    ):
        ui.display_chart(title, caption, chart)


def render_forward_driving_tab(application_data):
    render_driving_tab(application_data, reverse_state=0)


def render_reverse_driving_tab(application_data):
    render_driving_tab(application_data, reverse_state=1)


def render_driver_behavior_tab(application_data):
    analytics = application_data["analytics"]
    behavior_metrics = analytics["behavior_metrics"]
    comparison = analytics["comparison"]
    forward_impact_metrics = analytics["forward_impact_metrics"]
    analytics_dataframe = application_data["analytics_dataframe"]
    reverse_segments = analytics["reverse_segments"]

    st.caption(ANALYTICS_NOTE)

    ui.display_chart(
        "Control Profile",
        "Speed Stability Score shows how consistently the driver maintained "
        "speed (higher is better). Mean Steering Jerkiness is the average "
        "second-to-second steering change in degrees (lower is smoother). "
        "Metrics are separated because they use different units.",
        charts.plot_control_profile(behavior_metrics),
    )

    if forward_impact_metrics:
        ui.display_chart(
            "Forward Impact After Reverse",
            "Compares forward-driving speed and steering before vs after the "
            "reverse segment. Lower speed variability and lower steering change "
            "mean the forward driving became smoother after reversing.",
            charts.plot_forward_reverse_impact(forward_impact_metrics),
        )

    ui.display_chart(
        "Attention Mapping",
        "Steering change over time. Dashed lines show context-specific limits; "
        "red markers flag threshold exceedances during reverse driving.",
        charts.plot_attention_mapping(analytics_dataframe, behavior_metrics, reverse_segments),
    )

    st.subheader("Forward vs Reverse Summary")
    st.caption(
        "Compares steering thresholds, sudden steering events, and mean steering "
        "change between forward and reverse driving."
    )
    st.dataframe(
        ui.build_forward_reverse_display_table(comparison),
        use_container_width=True,
        hide_index=True,
    )


def render_data_quality_tab(application_data):
    quality_report = application_data["quality_report"]
    quality_dataframe = application_data["quality_dataframe"]
    cleaning_summary = application_data["cleaning_summary"]

    st.caption(
        "Summarizes data quality for the session. All rows are retained in storage. "
        "Missing values and outlier values are flagged; outlier values are excluded "
        "from metrics and charts."
    )

    st.subheader("Data Quality Summary")
    st.dataframe(cleaning_summary, use_container_width=True, hide_index=True)

    st.caption(f"Sensor error rows (ERROR_TIMEOUT): {quality_report['sensor_error_rows']}")
    ui.display_table(
        "Missing Values by Column",
        "Counts missing or non-numeric values per column. Rows are kept in storage and analysis.",
        ui.build_invalid_values_table(quality_report["missing_values_by_column"]),
    )
    ui.display_table(
        "Outlier Summary",
        "Statistical outliers detected with the IQR method, analyzed separately "
        "for forward and reverse driving. Outlier values are excluded from analytics.",
        ui.build_outlier_summary_table(quality_dataframe),
    )
