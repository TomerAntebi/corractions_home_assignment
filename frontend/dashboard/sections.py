"""
Streamlit section renderers for the dashboard.

Each function owns one visible dashboard section and delegates data preparation
and chart creation to helper modules.
"""

import matplotlib.pyplot as plt
import pandas as pd
import streamlit as st

from dashboard.charts import (
    create_horizontal_bar_chart,
    create_line_chart,
)
from dashboard.data import (
    create_chart_dataframe,
    create_executive_summary_rows,
    create_missing_fields_dataframe,
    create_problem_rows_dataframe,
    create_quality_breakdown_dataframe,
    create_reverse_state_dataframe,
    create_statistics_rows,
    create_validation_error_dataframe,
)
from dashboard.helpers import (
    JsonObject,
    format_count,
    format_percentage,
    get_analyzed_measurement_count,
    get_json_object,
    get_number,
)


def _center_table(table_dataframe: pd.DataFrame) -> object:
    return table_dataframe.style.set_properties(
        **{"text-align": "center"}
    ).set_table_styles(
        [
            {"selector": "th", "props": [("text-align", "center")]},
            {"selector": "td", "props": [("text-align", "center")]},
        ]
    )


def render_session_information(session: JsonObject) -> None:
    # Session overview
    st.subheader("Session Information")
    metadata = get_json_object(session, "metadata")
    sensors_active = metadata.get("sensors_active", [])
    sensors_active_text = (
        ", ".join(str(sensor_name) for sensor_name in sensors_active)
        if isinstance(sensors_active, list)
        else ""
    )
    session_information_rows = [
        {"Field": "Session ID", "Value": session.get("sessionId", "")},
        {"Field": "Vehicle ID", "Value": session.get("vehicleId", "")},
        {"Field": "Driver ID", "Value": session.get("driverId", "")},
        {"Field": "Recording Date", "Value": session.get("recordingDate", "")},
        {"Field": "Test Location", "Value": metadata.get("test_location", "")},
        {"Field": "Start Time UTC", "Value": metadata.get("start_time_utc", "")},
        {"Field": "End Time UTC", "Value": metadata.get("end_time_utc", "")},
        {"Field": "Sample Rate Hz", "Value": metadata.get("sample_rate_hz", "")},
        {"Field": "Hardware Version", "Value": metadata.get("hardware_version", "")},
        {"Field": "Firmware Version", "Value": metadata.get("firmware_version", "")},
        {"Field": "Sensors Active", "Value": sensors_active_text},
        {"Field": "Notes", "Value": metadata.get("notes", "")},
    ]
    st.table(_center_table(pd.DataFrame(session_information_rows)))


def render_executive_summary(
    quality_report: JsonObject,
    analytics: JsonObject,
) -> None:
    # High-level reviewer summary
    st.subheader("Executive Summary")
    summary_rows = create_executive_summary_rows(quality_report, analytics)
    for row_index in range(0, len(summary_rows), 3):
        summary_columns = st.columns(3)
        for column, summary_row in zip(summary_columns, summary_rows[row_index : row_index + 3]):
            with column.container(border=True):
                st.metric(summary_row["label"], summary_row["value"])
                st.caption(summary_row["detail"])


def render_quality_metrics(
    quality_report: JsonObject,
    analytics: JsonObject,
) -> None:
    st.subheader("Quality Metrics")
    quality_columns = st.columns(5)
    quality_columns[0].metric(
        "Quality Score",
        format_percentage(get_number(quality_report, "qualityScore")),
        help=(
            "Quality score combines the valid row ratio with a smaller penalty for "
            "outlier rows. Higher is better."
        ),
    )
    quality_columns[1].metric("Total Rows", format_count(get_number(quality_report, "totalRows")))
    quality_columns[2].metric("Valid Rows", format_count(get_number(quality_report, "validRows")))
    quality_columns[3].metric("Invalid Rows", format_count(get_number(quality_report, "invalidRows")))
    quality_columns[4].metric(
        "Analyzed Rows",
        format_count(get_analyzed_measurement_count(analytics)),
        help="Rows used by analytics after removing invalid rows and outliers.",
    )


def render_data_quality_breakdown(quality_report: JsonObject) -> None:
    # Data quality visualization
    st.subheader("Data Quality Breakdown")
    st.info(
        "Outliers are detected after validation using the IQR method. For each sensor value, "
        "the dashboard calculates Q1, Q3, and IQR = Q3 - Q1. Values below Q1 - 1.5 * IQR "
        "or above Q3 + 1.5 * IQR are marked as outliers. Forward and reverse driving rows "
        "are checked separately so normal reverse-driving behavior is not treated as an anomaly."
    )
    quality_breakdown_dataframe = create_quality_breakdown_dataframe(quality_report)
    quality_breakdown_chart = create_horizontal_bar_chart(
        quality_breakdown_dataframe,
        "Status",
        "Count",
        "Row Count",
    )
    st.pyplot(quality_breakdown_chart)
    plt.close(quality_breakdown_chart)


def render_validation_breakdown(quality_report: JsonObject) -> None:
    st.subheader("Validation Error Breakdown")
    validation_error_dataframe = create_validation_error_dataframe(quality_report)
    missing_fields_dataframe = create_missing_fields_dataframe(quality_report)
    validation_columns = st.columns(2)
    with validation_columns[0]:
        st.write("Validation Rules")
        if validation_error_dataframe.empty:
            st.info("No validation errors found.")
        else:
            validation_error_chart = create_horizontal_bar_chart(
                validation_error_dataframe,
                "Rule",
                "Count",
                "Error Count",
            )
            st.pyplot(validation_error_chart)
            plt.close(validation_error_chart)

    with validation_columns[1]:
        st.write("Missing Fields")
        if missing_fields_dataframe.empty:
            st.info("No missing required fields found.")
        else:
            missing_fields_chart = create_horizontal_bar_chart(
                missing_fields_dataframe,
                "Field",
                "Count",
                "Missing Row Count",
            )
            st.pyplot(missing_fields_chart)
            plt.close(missing_fields_chart)


def render_analytics_statistics(
    speed_statistics: JsonObject,
    wheel_angle_statistics: JsonObject,
) -> None:
    st.subheader("Analytics Statistics")
    st.caption(
        "These statistics are calculated from measurements that passed validation and were not "
        "marked as outliers. This keeps invalid rows and unusual sensor spikes from skewing the "
        "summary values."
    )
    statistics_columns = st.columns(2)
    with statistics_columns[0]:
        st.write("Speed Statistics")
        st.table(_center_table(pd.DataFrame(create_statistics_rows(speed_statistics))))

    with statistics_columns[1]:
        st.write("Wheel Angle Statistics")
        st.table(_center_table(pd.DataFrame(create_statistics_rows(wheel_angle_statistics))))


def render_driving_behavior(
    analytics: JsonObject,
    speed_statistics: JsonObject,
    wheel_angle_statistics: JsonObject,
    measurements: list[JsonObject],
) -> None:
    # Speed and steering behavior
    st.subheader("Driving Behavior")
    st.subheader("Speed Over Time")
    speed_chart_dataframe = create_chart_dataframe(measurements, "speed")
    if speed_chart_dataframe.empty:
        st.info("No speed measurements available.")
    else:
        speed_chart = create_line_chart(
            speed_chart_dataframe,
            "rowIndex",
            "speed",
            "Measurement Row Index",
            "Speed",
            get_number(speed_statistics, "mean"),
            f"Mean {get_number(speed_statistics, 'mean'):.1f}",
        )
        st.pyplot(speed_chart)
        plt.close(speed_chart)

    st.subheader("Wheel Angle Over Time")
    wheel_angle_chart_dataframe = create_chart_dataframe(measurements, "wheelAngle")
    if wheel_angle_chart_dataframe.empty:
        st.info("No wheel angle measurements available.")
    else:
        wheel_angle_chart = create_line_chart(
            wheel_angle_chart_dataframe,
            "rowIndex",
            "wheelAngle",
            "Measurement Row Index",
            "Wheel Angle",
            get_number(wheel_angle_statistics, "mean"),
            f"Mean {get_number(wheel_angle_statistics, 'mean'):.1f}",
        )
        st.pyplot(wheel_angle_chart)
        plt.close(wheel_angle_chart)

    st.write("Reverse State Summary")
    reverse_state_dataframe = create_reverse_state_dataframe(analytics)
    reverse_state_chart = create_horizontal_bar_chart(
        reverse_state_dataframe,
        "State",
        "Count",
        "Measurement Count",
    )
    st.pyplot(reverse_state_chart)
    plt.close(reverse_state_chart)


def render_problem_rows(measurements: list[JsonObject]) -> None:
    # Raw measurement inspection
    st.subheader("Problem Rows Preview")
    st.caption(
        "Rows shown here failed validation or were marked as outliers. Use them to investigate "
        "missing values, sensor errors, range problems, and unusual measurements."
    )
    problem_rows_dataframe = create_problem_rows_dataframe(measurements)
    if problem_rows_dataframe.empty:
        st.info("No invalid or outlier rows found.")
    else:
        st.dataframe(
            _center_table(problem_rows_dataframe.head(20)),
            use_container_width=True,
        )


def render_measurements_table(measurements: list[JsonObject]) -> None:
    st.subheader("Measurements Table")
    measurements_dataframe = pd.DataFrame(measurements)
    st.dataframe(_center_table(measurements_dataframe), use_container_width=True)
