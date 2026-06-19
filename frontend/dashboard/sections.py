"""
Streamlit section renderers for the dashboard.

Each function receives API responses, builds charts via helper modules,
and renders Streamlit components.
"""

from collections.abc import Callable
from typing import cast

import matplotlib.pyplot as plt
from matplotlib.figure import Figure
import pandas as pd
import streamlit as st

from dashboard.chart_data import (
    create_forward_reverse_comparison_dataframe,
    create_scatter_chart_dataframe,
    create_timeline_chart_dataframe,
)
from dashboard.charts import (
    create_grouped_bar_chart,
    create_horizontal_bar_chart,
    create_line_chart,
    create_scatter_chart,
)
from dashboard.data import (
    create_data_quality_rows,
    create_forward_driving_metric_groups,
    create_missing_fields_dataframe,
    create_problem_rows_display_dataframe,
    create_reverse_driving_metric_groups,
    create_session_information_rows,
    create_valid_measurements_dataframe,
    create_validation_error_dataframe,
)
from dashboard.helpers import JsonObject


METRIC_COLUMN_COUNT = 4


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
    footer_content: Callable[[], None] | None = None,
) -> None:
    st.subheader(title)
    st.caption(caption)
    if dataframe.empty:
        st.info(empty_message)
        return

    chart = build_chart()
    st.pyplot(chart)
    plt.close(chart)

    if footer_content is not None:
        footer_content()


def _render_line_chart_block(
    title: str,
    caption: str,
    forward_driving: JsonObject,
    field_name: str,
    mean_value: float | None,
    y_label: str,
    empty_message: str,
) -> None:
    chart_dataframe = create_timeline_chart_dataframe(forward_driving, field_name)

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
        "Forward and reverse driving metrics are computed separately from usable measurements."
    )

    st.markdown("### Forward Driving")
    st.caption("Primary control metrics from forward gear only.")
    with st.container(border=True):
        for metric_group in create_forward_driving_metric_groups(analytics):
            _render_metric_group(metric_group)

    st.markdown("### Reverse Driving")
    st.caption("Context metrics from reverse gear only.")
    with st.container(border=True):
        for metric_group in create_reverse_driving_metric_groups(analytics):
            _render_metric_group(metric_group)

    _render_driving_insights_card(analytics)


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


def render_driving_visualization(analytics: JsonObject) -> None:
    st.subheader("Driving Visualization")
    forward_driving = cast(JsonObject, analytics["forwardDriving"])

    st.markdown("### Forward Driving")
    st.caption("Charts use pre-computed forward-driving series from the backend.")
    with st.container(border=True):
        _render_line_chart_block(
            "Speed Across Session",
            "Shows how forward-driving speed changes across analyzed measurements in session order.",
            forward_driving,
            "speed",
            cast(float | None, forward_driving.get("speedMean")),
            "Speed",
            "No forward speed measurements available.",
        )
        _render_line_chart_block(
            "Wheel Angle Across Session",
            "Shows how forward-driving steering angle changes across analyzed measurements in session order.",
            forward_driving,
            "wheelAngle",
            cast(float | None, forward_driving.get("wheelAngleMean")),
            "Wheel Angle",
            "No forward wheel angle measurements available.",
        )

        scatter_dataframe = create_scatter_chart_dataframe(forward_driving)
        _render_chart_block(
            "Speed vs Steering (Forward Driving)",
            "Each point is one forward measurement. Tight clusters suggest coordinated speed and steering control.",
            scatter_dataframe,
            "No forward speed and steering measurements are available.",
            lambda: create_scatter_chart(
                scatter_dataframe,
                "wheelAngle",
                "speed",
                "Wheel Angle",
                "Speed",
            ),
        )

        turn_speed = forward_driving.get("averageSpeedDuringTurns")
        straight_speed = forward_driving.get("averageSpeedDuringStraightDriving")

        st.subheader("Turning vs Straight Driving Speed")
        st.caption(
            "Compares forward-driving speed during turning and straight-driving situations."
        )
        if turn_speed is None and straight_speed is None:
            st.info("No forward turn and straight-driving speed comparison is available.")
        else:
            turn_col, straight_col = st.columns(2)
            if turn_speed is not None:
                turn_col.metric("During Turns", f"{cast(float, turn_speed):.1f}")
            if straight_speed is not None:
                delta = (
                    f"{cast(float, straight_speed) - cast(float, turn_speed):+.1f}"
                    if turn_speed is not None
                    else None
                )
                straight_col.metric(
                    "Straight Driving",
                    f"{cast(float, straight_speed):.1f}",
                    delta=delta,
                )

    st.markdown("### Reverse & Session Context")
    st.caption(
        "Reverse metrics provide session context. Primary driving analysis remains forward driving."
    )
    with st.container(border=True):
        comparison_dataframe = create_forward_reverse_comparison_dataframe(analytics)
        steering_speed_insight = cast(str, analytics["steeringSpeedInsight"])

        def _render_steering_insight_caption() -> None:
            st.caption(steering_speed_insight)

        _render_chart_block(
            "Forward vs Reverse Comparison",
            (
                "Compares average speed and steering variability between forward and reverse driving. "
                "Use reverse metrics as context, not as the primary control signal."
            ),
            comparison_dataframe,
            "No forward/reverse comparison metrics are available.",
            lambda: create_grouped_bar_chart(
                comparison_dataframe,
                "Metric",
                "Direction",
                "Value",
                "Metric",
                "Value",
            ),
            footer_content=_render_steering_insight_caption,
        )


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
