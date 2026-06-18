"""
Streamlit section renderers for the dashboard.

Each function owns one visible dashboard section and delegates data preparation
and chart creation to helper modules.
"""

from collections.abc import Callable
from typing import cast

import matplotlib.pyplot as plt
from matplotlib.figure import Figure
import pandas as pd
import streamlit as st

from dashboard.charts import (
    create_horizontal_bar_chart,
    create_line_chart,
    create_scatter_chart,
    create_vertical_bar_chart,
)
from dashboard.data import (
    create_chart_dataframe,
    create_data_quality_rows,
    create_driving_behavior_metric_groups,
    create_missing_fields_dataframe,
    create_problem_rows_display_dataframe,
    create_session_information_rows,
    create_speed_steering_dataframe,
    create_turn_speed_dataframe,
    create_valid_measurements_dataframe,
    create_validation_error_dataframe,
)
from dashboard.helpers import JsonObject


def _center_table(table_dataframe: pd.DataFrame) -> object:
    return table_dataframe.style.set_properties(
        **{"text-align": "center"}
    ).set_table_styles(
        [
            {"selector": "th", "props": [("text-align", "center")]},
            {"selector": "td", "props": [("text-align", "center")]},
        ]
    )


def _render_chart_block(
    title: str,
    caption: str,
    dataframe: pd.DataFrame,
    empty_message: str,
    build_chart: Callable[[], Figure],
) -> None:
    st.subheader(title)
    st.caption(caption)
    if dataframe.empty:
        st.info(empty_message)
        return

    chart = build_chart()
    st.pyplot(chart)
    plt.close(chart)


def _render_line_chart_block(
    title: str,
    caption: str,
    measurements: list[JsonObject],
    field_name: str,
    mean_value: float | None,
    y_label: str,
    empty_message: str,
) -> None:
    chart_dataframe = create_chart_dataframe(measurements, field_name)

    _render_chart_block(
        title,
        caption,
        chart_dataframe,
        empty_message,
        lambda: create_line_chart(
            chart_dataframe,
            "rowIndex",
            field_name,
            "Measurement Row Index",
            y_label,
            mean_value,
            f"Mean {mean_value:.1f}" if mean_value is not None else None,
        ),
    )


def _render_horizontal_bar_block(
    title: str,
    dataframe: pd.DataFrame,
    empty_message: str,
    category_column: str,
    value_column: str,
    x_label: str,
) -> None:
    st.write(title)
    if dataframe.empty:
        st.info(empty_message)
        return

    chart = create_horizontal_bar_chart(
        dataframe,
        category_column,
        value_column,
        x_label,
    )
    st.pyplot(chart)
    plt.close(chart)


METRIC_COLUMN_COUNT = 4


def _render_metric_group(metric_group: dict[str, object]) -> None:
    with st.container(border=True):
        st.markdown(f"#### {cast(str, metric_group['title'])}")
        metrics = cast(list[dict[str, str]], metric_group["metrics"])
        columns = st.columns(METRIC_COLUMN_COUNT)
        for index, metric in enumerate(metrics):
            if index >= METRIC_COLUMN_COUNT:
                break
            columns[index].metric(metric["label"], metric["value"], help=metric["help"])

        caption = metric_group.get("caption")
        if caption:
            st.caption(cast(str, caption))


def _render_driving_insights_card(analytics: JsonObject) -> None:
    driving_insights = cast(list[str], analytics["drivingInsights"])
    with st.container(border=True):
        st.markdown("#### Key Observations")
        st.caption("Automatically generated observations based on measured driving behavior.")
        for insight in driving_insights:
            st.markdown(f"> {insight}")


def render_session_information(session: JsonObject) -> None:
    st.subheader("Session Information")
    st.caption(
        "This section describes the source and configuration of the recorded driving session."
    )
    with st.container(border=True):
        st.table(
            _center_table(pd.DataFrame(create_session_information_rows(session)))
        )


def render_driving_analytics_home(analytics: JsonObject) -> None:
    st.subheader("Driver Behavior")
    st.caption(
        "Steering, speed, turning, and reverse behavior summarized from usable measurements."
    )
    for metric_group in create_driving_behavior_metric_groups(analytics):
        _render_metric_group(metric_group)

    _render_driving_insights_card(analytics)


# Data quality section: valid, invalid, and outlier row counts.
def render_data_quality_breakdown(quality_report: JsonObject) -> None:
    st.subheader("Data Quality")
    st.caption(
        "These metrics summarize the overall quality of the recorded sensor data."
    )
    with st.container(border=True):
        data_quality_columns = st.columns(4)
        for column, data_quality_row in zip(
            data_quality_columns,
            create_data_quality_rows(quality_report),
        ):
            column.metric(
                data_quality_row["label"],
                data_quality_row["value"],
                help=data_quality_row["detail"],
            )

        sensor_errors = cast(list[str], quality_report.get("sensorErrors", []))
        if sensor_errors:
            st.markdown("**Detected Sensor Error Markers**")
            for sensor_error in sensor_errors:
                st.markdown(f"- {sensor_error}")


# Validation section: why rows failed validation.
def render_validation_breakdown(quality_report: JsonObject) -> None:
    st.subheader("Validation Breakdown")
    st.caption("Shows why measurements failed validation.")
    with st.container(border=True):
        validation_columns = st.columns(2)
        with validation_columns[0]:
            _render_horizontal_bar_block(
                "Validation Rules",
                create_validation_error_dataframe(quality_report),
                "No validation errors found.",
                "Issue Type",
                "Count",
                "Error Count",
            )
        with validation_columns[1]:
            _render_horizontal_bar_block(
                "Missing Fields",
                create_missing_fields_dataframe(quality_report),
                "No missing required fields found.",
                "Field",
                "Count",
                "Missing Row Count",
            )


# Driving visualization section: meaningful charts for reviewer interpretation.
def render_driving_behavior(
    analytics: JsonObject,
    measurements: list[JsonObject],
) -> None:
    st.subheader("Driving Visualization")
    st.caption("These charts visualize speed, steering behavior, and their relationship.")

    _render_line_chart_block(
        "Speed Across Session",
        "Shows how vehicle speed changes across analyzed measurements in session order.",
        measurements,
        "speed",
        cast(float | None, analytics.get("speedMean")),
        "Speed",
        "No speed measurements available.",
    )
    _render_line_chart_block(
        "Wheel Angle Across Session",
        "Shows how steering angle changes across analyzed measurements in session order.",
        measurements,
        "wheelAngle",
        cast(float | None, analytics.get("wheelAngleMean")),
        "Wheel Angle",
        "No wheel angle measurements available.",
    )

    speed_steering_dataframe = create_speed_steering_dataframe(measurements)
    _render_chart_block(
        "Speed vs Steering Angle",
        "Helps visualize the relationship between steering intensity and vehicle speed.",
        speed_steering_dataframe,
        "No forward-driving speed and steering-angle measurements are available.",
        lambda: create_scatter_chart(
            speed_steering_dataframe,
            "absoluteWheelAngle",
            "speed",
            "Absolute Steering Wheel Angle",
            "Vehicle Speed",
        ),
    )

    turn_speed_dataframe = create_turn_speed_dataframe(analytics)
    _render_chart_block(
        "Turning vs Straight Driving Speed",
        "Compares driving speed during turning and straight-driving situations.",
        turn_speed_dataframe,
        "No turn and straight-driving speed comparison is available.",
        lambda: create_vertical_bar_chart(
            turn_speed_dataframe,
            "Driving Mode",
            "Average Speed",
            "Driving Mode",
            "Average Speed",
        ),
    )


# Bottom diagnostics section: invalid and outlier rows for investigation.
def render_problem_rows(measurements: list[JsonObject]) -> None:
    st.subheader("Problem Rows")
    st.caption(
        "Rows that failed validation or were identified as statistical outliers."
    )
    problem_rows_dataframe = create_problem_rows_display_dataframe(measurements)
    with st.container(border=True):
        if problem_rows_dataframe.empty:
            st.info("No invalid or outlier rows found.")
        else:
            st.dataframe(
                _center_table(problem_rows_dataframe.head(20)),
                use_container_width=True,
            )


# Bottom raw data section: valid measurements used for analysis.
def render_measurements_table(measurements: list[JsonObject]) -> None:
    st.subheader("Raw Measurements")
    st.caption(
        "Valid, non-outlier measurements used for analysis. Invalid and outlier rows are shown above in Problem Rows."
    )
    valid_measurements_dataframe = create_valid_measurements_dataframe(measurements)
    with st.container(border=True):
        if valid_measurements_dataframe.empty:
            st.info("No valid measurements available.")
            return

        st.dataframe(
            _center_table(valid_measurements_dataframe),
            use_container_width=True,
        )
