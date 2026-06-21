"""Dashboard tabs — renders session, forward/reverse driving, behavior, and data quality views."""

import streamlit as st

from dashboard.config import ANALYTICS_NOTE, METADATA_FILE_NAME, SOURCE_FILE_NAME
from dashboard.ui import (
    build_forward_reverse_display_table,
    build_invalid_values_table,
    build_measurements_display_table,
    build_outlier_summary_table,
    build_session_metadata_table,
    display_chart,
    display_metric,
    display_table,
)
from ingestion import MeasurementColumn
from visualizations import (
    plot_distribution,
    plot_steering_buckets,
    plot_steering_correction_timeline,
    plot_timeline,
)

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
    cleaned_dataframe = application_data["cleaned_dataframe"]

    st.caption(
        "Session information from the metadata file and cleaned measurements "
        "stored in the database."
    )

    st.subheader("Session Metadata")
    st.dataframe(
        build_session_metadata_table(metadata),
        use_container_width=True,
        hide_index=True,
    )

    st.write(f"Source CSV: `{SOURCE_FILE_NAME}`")
    st.write(f"Source metadata: `{METADATA_FILE_NAME}`")

    st.subheader("Measurements")
    st.caption(f"{len(cleaned_dataframe)} cleaned rows stored in the database.")
    st.dataframe(
        build_measurements_display_table(cleaned_dataframe),
        use_container_width=True,
        hide_index=True,
    )


def _render_measurement_count(context_metrics, title_prefix):
    count_column, _ = st.columns([1, 4])
    with count_column:
        display_metric(
            f"{title_prefix} Measurements",
            context_metrics["measurement_count"],
            format_string="{}",
            help_text=(
                f"Number of cleaned, non-outlier measurements during "
                f"{title_prefix.lower()} driving."
            ),
        )


def _render_driving_metrics(context_metrics):
    metric_columns = st.columns(5)
    with metric_columns[0]:
        display_metric(
            "Average Speed",
            context_metrics["average_speed"],
            help_text="Mean speed during this driving direction (km/h).",
        )
    with metric_columns[1]:
        display_metric(
            "Speed Variability",
            context_metrics["speed_variability"],
            help_text="Standard deviation of speed. Higher values mean more fluctuation.",
        )
    with metric_columns[2]:
        display_metric(
            "Steering Variability",
            context_metrics["steering_variability"],
            help_text="Standard deviation of steering angle. Higher values mean more steering movement.",
        )
    with metric_columns[3]:
        display_metric(
            "Total Turns",
            context_metrics["total_turns"],
            format_string="{}",
            help_text="Measurements where steering angle is at least 20 degrees.",
        )
    with metric_columns[4]:
        display_metric(
            "Sharp Turns",
            context_metrics["sharp_turns"],
            format_string="{}",
            help_text="Measurements where steering angle is at least 25 degrees.",
        )


def _iter_driving_charts(analytics, analytics_dataframe, reverse_state):
    gear_config = GEAR_TAB_CONFIG[reverse_state]
    title_prefix = gear_config["title_prefix"]
    buckets_key = gear_config["buckets_key"]

    yield (
        f"{title_prefix} Speed Profile",
        f"Shows how speed changes sample-by-sample during {title_prefix.lower()} driving. "
        "Each point is one measurement taken about one second apart.",
        plot_timeline(
            analytics_dataframe,
            MeasurementColumn.SPEED,
            reverse_state=reverse_state,
            y_label="Speed (km/h)",
        ),
    )
    yield (
        f"{title_prefix} Steering Timeline",
        f"Shows steering angle over time during {title_prefix.lower()} driving. "
        "Positive and negative values indicate direction of turn.",
        plot_timeline(
            analytics_dataframe,
            MeasurementColumn.WHEEL_ANGLE,
            reverse_state=reverse_state,
            y_label="Steering angle (degrees)",
        ),
    )
    yield (
        f"{title_prefix} Speed Distribution",
        f"Shows how frequently each speed value appears during {title_prefix.lower()} driving.",
        plot_distribution(
            analytics_dataframe,
            MeasurementColumn.SPEED,
            reverse_state=reverse_state,
            xlabel="Speed (km/h)",
        ),
    )
    yield (
        f"{title_prefix} Steering Distribution",
        f"Shows how often the driver used light vs heavy steering during {title_prefix.lower()} driving.",
        plot_distribution(
            analytics_dataframe,
            MeasurementColumn.WHEEL_ANGLE,
            reverse_state=reverse_state,
            xlabel="Steering angle (degrees)",
        ),
    )
    yield (
        f"{title_prefix} Average Speed by Steering Angle",
        "Average speed in each steering range. Darker bars = sharper steering. "
        "Y-axis zoomed to show differences.",
        plot_steering_buckets(analytics[buckets_key], reverse_state),
    )


def render_driving_tab(application_data, reverse_state):
    analytics = application_data["analytics"]
    gear_config = GEAR_TAB_CONFIG[reverse_state]
    context_metrics = analytics[gear_config["metrics_key"]]
    analytics_dataframe = application_data["analytics_dataframe"]

    st.caption(ANALYTICS_NOTE)
    _render_measurement_count(context_metrics, gear_config["title_prefix"])
    _render_driving_metrics(context_metrics)

    for title, caption, chart in _iter_driving_charts(
        analytics,
        analytics_dataframe,
        reverse_state,
    ):
        display_chart(title, caption, chart)


def render_forward_driving_tab(application_data):
    render_driving_tab(application_data, reverse_state=0)


def render_reverse_driving_tab(application_data):
    render_driving_tab(application_data, reverse_state=1)


def render_driver_behavior_tab(application_data):
    analytics = application_data["analytics"]
    behavior_metrics = analytics["behavior_metrics"]
    comparison = analytics["comparison"]
    analytics_dataframe = application_data["analytics_dataframe"]
    sample_rate_hz = application_data["metadata"].get("sample_rate_hz", 1)

    st.caption(ANALYTICS_NOTE)

    metric_columns = st.columns(2)
    with metric_columns[0]:
        display_metric(
            "Steering Jerkiness",
            behavior_metrics["steering_jerkiness"],
            help_text="Average steering angle change between consecutive samples (degrees). Higher values mean jerkier steering.",
        )
    with metric_columns[1]:
        display_metric(
            "Speed Instability",
            behavior_metrics["speed_instability"],
            help_text="Average speed change between consecutive samples (km/h). Higher values mean less stable speed control.",
        )

    alert_metric_columns = st.columns(2)
    with alert_metric_columns[0]:
        display_metric(
            "Forward Sudden Corrections",
            behavior_metrics["forward_sudden_steering_events"],
            format_string="{}",
            help_text=(
                f"Threshold: {behavior_metrics['forward_sudden_steering_threshold']:.1f}° "
                "(forward mean + 1.5 standard deviations)."
            ),
        )
    with alert_metric_columns[1]:
        display_metric(
            "Reverse Sudden Corrections",
            behavior_metrics["reverse_sudden_steering_events"],
            format_string="{}",
            help_text=(
                f"Threshold: {behavior_metrics['reverse_sudden_steering_threshold']:.1f}° "
                "(reverse mean + 1.5 standard deviations)."
            ),
        )

    correction_chart_config = {
        0: (
            "Forward Control Stability Timeline",
            "Steering change during forward driving. Threshold uses forward-only mean + 1.5 standard deviations.",
        ),
        1: (
            "Reverse Control Stability Timeline",
            "Steering change during reverse driving. Threshold uses reverse-only mean + 1.5 standard deviations.",
        ),
    }
    for reverse_state, (title, caption) in correction_chart_config.items():
        display_chart(
            title,
            caption,
            plot_steering_correction_timeline(
                analytics_dataframe,
                behavior_metrics,
                reverse_state=reverse_state,
                sample_rate_hz=sample_rate_hz,
            ),
        )

    st.subheader("Forward vs Reverse Summary")
    st.caption(
        "Average steering change and speed change for each driving direction."
    )
    st.dataframe(
        build_forward_reverse_display_table(comparison),
        use_container_width=True,
        hide_index=True,
    )


def render_data_quality_tab(application_data):
    quality_report = application_data["quality_report"]
    quality_dataframe = application_data["quality_dataframe"]
    cleaning_summary = application_data["cleaning_summary"]

    st.caption(
        "Summarizes how raw CSV rows were cleaned before analysis. "
        "Invalid rows are removed before storage. Outlier rows remain in the database "
        "but are excluded from driving behavior calculations."
    )

    st.subheader("Cleaning Summary")
    st.dataframe(
        cleaning_summary,
        use_container_width=True,
        hide_index=True,
    )

    st.caption(
        f"Sensor error rows (ERROR_TIMEOUT): {quality_report['sensor_error_rows']}"
    )
    display_table(
        "Invalid Values by Column",
        "Counts missing or non-numeric values found in the raw CSV before rows were removed.",
        build_invalid_values_table(quality_report["invalid_rows_by_column"]),
    )
    display_table(
        "Outlier Summary",
        "Counts statistical outliers detected with the IQR method, analyzed separately for forward and reverse driving.",
        build_outlier_summary_table(quality_dataframe),
    )
