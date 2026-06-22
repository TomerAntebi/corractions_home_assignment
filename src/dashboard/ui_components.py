"""Dashboard UI components — Streamlit metric/chart/table display and dataframe formatters."""

import matplotlib.pyplot as plt
import pandas as pd
import streamlit as st

from ingestion import MeasurementColumn


def display_metric(label, value, format_string="{:.2f}", help_text=None):
    if value is None or (isinstance(value, float) and value != value):
        st.metric(label, "N/A", help=help_text)
        return

    if isinstance(value, float):
        st.metric(label, format_string.format(value), help=help_text)
        return

    st.metric(label, str(value), help=help_text)


def render_driving_kpi_cards(context_metrics, title_prefix):
    context_label = title_prefix.lower()
    metric_specs = [
        (f"{title_prefix} Measurements", "measurement_count", "{}", f"Number of measurements during {context_label} driving."),
        ("Average Speed", "average_speed", "{:.2f}", f"Mean speed during {context_label} driving (km/h)."),
        (
            "Speed Variability",
            "speed_variability",
            "{:.2f}",
            "Standard deviation of speed. Higher values mean more fluctuation.",
        ),
        (
            "Steering Variability",
            "steering_variability",
            "{:.2f}",
            "Standard deviation of steering angle.",
        ),
    ]

    for column, (label, key, format_string, help_text) in zip(st.columns(4), metric_specs):
        with column:
            display_metric(
                label, context_metrics[key],
                format_string=format_string, help_text=help_text,
            )


def display_chart(title, caption, chart):
    st.subheader(title)
    st.caption(caption)
    st.pyplot(chart, use_container_width=True)
    plt.close(chart)


def display_table(title, caption, dataframe):
    st.subheader(title)
    st.caption(caption)
    st.dataframe(dataframe, use_container_width=True, hide_index=True)


def build_forward_reverse_display_table(forward_metrics, reverse_metrics):
    def format_threshold(value):
        if value is None or (isinstance(value, float) and value != value):
            return "N/A"
        return f"{value:.1f}"

    def format_mean_delta(value):
        if value is None or (isinstance(value, float) and value != value):
            return "N/A"
        return f"{value:.2f}"

    return pd.DataFrame(
        [
            {"Metric": "Steering Threshold (deg)", "Forward": format_threshold(forward_metrics["steering_threshold"]), "Reverse": format_threshold(reverse_metrics["steering_threshold"])},
            {
                "Metric": "Sudden Steering Events",
                "Forward": int(forward_metrics["sudden_steering_events"]),
                "Reverse": int(reverse_metrics["sudden_steering_events"]),
            },
            {"Metric": "Mean Steering Delta (deg)", "Forward": format_mean_delta(forward_metrics["steering_jerkiness"]), "Reverse": format_mean_delta(reverse_metrics["steering_jerkiness"])},
            {"Metric": "Avg Speed Change (km/h)", "Forward": format_mean_delta(forward_metrics["speed_instability"]), "Reverse": format_mean_delta(reverse_metrics["speed_instability"])},
        ]
    )


def _format_metadata_value(value):
    if isinstance(value, list):
        return ", ".join(str(item) for item in value)

    return str(value)


def build_session_metadata_table(metadata):
    return pd.DataFrame(
        [
            {"Field": field_name, "Value": _format_metadata_value(field_value)}
            for field_name, field_value in metadata.items()
        ]
    )


def build_measurements_display_table(dataframe):
    formatted = dataframe.copy()
    formatted[MeasurementColumn.DISPLAY_TIME] = formatted[
        MeasurementColumn.DISPLAY_TIME
    ].dt.strftime("%Y-%m-%d %H:%M:%S")
    formatted[MeasurementColumn.REVERSE_STATE] = formatted[
        MeasurementColumn.REVERSE_STATE
    ].map({0: "Forward", 1: "Reverse"})

    return formatted.rename(
        columns={
            MeasurementColumn.ELAPSED_SECONDS: "Elapsed (s)",
            MeasurementColumn.DISPLAY_TIME: "Display Time",
            MeasurementColumn.WHEEL_ANGLE: "Wheel Angle (deg)",
            MeasurementColumn.SPEED: "Speed (km/h)",
            MeasurementColumn.REVERSE_STATE: "Gear",
        }
    )[
        [
            "Elapsed (s)",
            "Display Time",
            "Wheel Angle (deg)",
            "Speed (km/h)",
            "Gear",
        ]
    ]


def build_invalid_values_table(missing_values_by_column):
    return pd.DataFrame(
        [
            {"Data column": column_name, "Missing or invalid values": invalid_count}
            for column_name, invalid_count in missing_values_by_column.items()
        ]
    )


def build_outlier_summary_table(quality_dataframe):
    summary_rows = []

    for reverse_state, driving_context in ((0, "Forward"), (1, "Reverse")):
        context_mask = quality_dataframe[MeasurementColumn.REVERSE_STATE] == reverse_state

        for label, field_name in (("speed", MeasurementColumn.SPEED), ("steering", MeasurementColumn.WHEEL_ANGLE)):
            summary_rows.append(
                {
                    "Category": f"{driving_context} {label} outliers",
                    "Outlier count": int(quality_dataframe.loc[context_mask, f"{field_name}_outlier"].sum()),
                }
            )

    return pd.DataFrame(summary_rows)
