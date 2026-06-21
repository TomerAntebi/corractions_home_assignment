"""Dashboard UI helpers — Streamlit metric/chart/table display and dataframe formatters."""

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


def display_chart(title, caption, chart):
    st.subheader(title)
    st.caption(caption)
    st.pyplot(chart, use_container_width=True)
    plt.close(chart)


def display_table(title, caption, dataframe):
    st.subheader(title)
    st.caption(caption)
    st.dataframe(dataframe, use_container_width=True, hide_index=True)


def build_forward_reverse_display_table(comparison_dataframe):
    return comparison_dataframe.rename(
        columns={
            "driving_context": "Driving Direction",
            "wheel_delta_mean": "Avg Steering Change (deg)",
            "speed_instability_mean": "Avg Speed Change (km/h)",
        }
    )


def build_session_metadata_table(metadata):
    metadata_rows = []

    for field_name, field_value in metadata.items():
        if isinstance(field_value, list):
            display_value = ", ".join(str(item) for item in field_value)
        else:
            display_value = str(field_value)

        metadata_rows.append(
            {
                "Field": field_name,
                "Value": display_value,
            }
        )

    return pd.DataFrame(metadata_rows)


def build_measurements_display_table(dataframe):
    formatted = dataframe.copy()
    formatted[MeasurementColumn.TIMESTAMP] = formatted[
        MeasurementColumn.TIMESTAMP
    ].dt.strftime(
        "%Y-%m-%d %H:%M:%S"
    )
    formatted[MeasurementColumn.REVERSE_STATE] = formatted[
        MeasurementColumn.REVERSE_STATE
    ].map(
        {
            0: "Forward",
            1: "Reverse",
        }
    )

    return formatted.rename(
        columns={
            MeasurementColumn.TIMESTAMP: "Timestamp",
            MeasurementColumn.WHEEL_ANGLE: "Wheel Angle (deg)",
            MeasurementColumn.SPEED: "Speed (km/h)",
            MeasurementColumn.REVERSE_STATE: "Gear",
        }
    )


def build_invalid_values_table(invalid_rows_by_column):
    return pd.DataFrame(
        [
            {
                "Data column": column_name,
                "Invalid or missing values": invalid_count,
            }
            for column_name, invalid_count in invalid_rows_by_column.items()
        ]
    )


def build_outlier_summary_table(quality_dataframe):
    summary_rows = []

    for reverse_state, driving_context in (
        (0, "Forward"),
        (1, "Reverse"),
    ):
        context_mask = (
            quality_dataframe[MeasurementColumn.REVERSE_STATE] == reverse_state
        )

        summary_rows.append(
            {
                "Category": f"{driving_context} speed outliers",
                "Outlier count": int(
                    quality_dataframe.loc[
                        context_mask, f"{MeasurementColumn.SPEED}_outlier"
                    ].sum()
                ),
            }
        )
        summary_rows.append(
            {
                "Category": f"{driving_context} steering outliers",
                "Outlier count": int(
                    quality_dataframe.loc[
                        context_mask, f"{MeasurementColumn.WHEEL_ANGLE}_outlier"
                    ].sum()
                ),
            }
        )

    return pd.DataFrame(summary_rows)
