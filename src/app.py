from pathlib import Path

import matplotlib.pyplot as plt
import pandas as pd
import streamlit as st

from analytics import build_analytics_bundle
from database import initialize_database, save_session_with_measurements
from ingestion import (
    MeasurementColumn,
    clean_measurement_data,
    load_dataset,
    load_session_metadata,
    normalize_types,
    validate_metadata_file,
    validate_required_columns,
)
from quality import (
    build_analytics_dataframe,
    build_cleaning_summary_dataframe,
    build_quality_dataframe,
    generate_quality_report,
)
from visualizations import (
    plot_distribution,
    plot_steering_buckets,
    plot_steering_correction_timeline,
    plot_timeline,
)

PROJECT_ROOT = Path(__file__).resolve().parent.parent
CSV_PATH = PROJECT_ROOT / "sample-data" / "field_session_042.csv"
METADATA_PATH = PROJECT_ROOT / "sample-data" / "metadata_session_042.json"
DB_PATH = PROJECT_ROOT / "driving_analysis.db"
SOURCE_FILE_NAME = "field_session_042.csv"
METADATA_FILE_NAME = "metadata_session_042.json"
ANALYTICS_NOTE = (
    "Metrics and charts use cleaned data with outlier rows excluded. "
    "Outliers are reported in the Data Quality tab and are not stored in the database."
)


@st.cache_data
def load_application_data():
    raw_dataframe = load_dataset(CSV_PATH)
    metadata = load_session_metadata(METADATA_PATH)

    validate_required_columns(raw_dataframe)
    validate_metadata_file(metadata)

    normalized_dataframe = normalize_types(raw_dataframe)
    cleaned_dataframe = clean_measurement_data(normalized_dataframe)

    initialize_database(DB_PATH)
    save_session_with_measurements(
        DB_PATH,
        metadata,
        cleaned_dataframe,
        SOURCE_FILE_NAME,
        METADATA_FILE_NAME,
    )

    quality_dataframe = build_quality_dataframe(cleaned_dataframe)
    analytics_dataframe = build_analytics_dataframe(
        cleaned_dataframe,
        quality_dataframe,
    )
    quality_report = generate_quality_report(
        raw_dataframe,
        normalized_dataframe,
        cleaned_dataframe,
        quality_dataframe,
    )

    return {
        "metadata": metadata,
        "cleaned_dataframe": cleaned_dataframe,
        "analytics_dataframe": analytics_dataframe,
        "quality_dataframe": quality_dataframe,
        "quality_report": quality_report,
        "cleaning_summary": build_cleaning_summary_dataframe(quality_report),
        "analytics": build_analytics_bundle(analytics_dataframe),
    }


def _display_metric(label, value, format_string="{:.2f}", help_text=None):
    if value is None or (isinstance(value, float) and value != value):
        st.metric(label, "N/A", help=help_text)
        return

    if isinstance(value, float):
        st.metric(label, format_string.format(value), help=help_text)
        return

    st.metric(label, str(value), help=help_text)


def _display_chart(title, caption, chart):
    st.subheader(title)
    st.caption(caption)
    st.pyplot(chart, use_container_width=True)
    plt.close(chart)


def _display_table(title, caption, dataframe):
    st.subheader(title)
    st.caption(caption)
    st.dataframe(dataframe, use_container_width=True, hide_index=True)


def _build_forward_reverse_display_table(comparison_dataframe):
    return comparison_dataframe.rename(
        columns={
            "driving_context": "Driving Direction",
            "wheel_delta_mean": "Avg Steering Change (deg)",
            "speed_instability_mean": "Avg Speed Change (km/h)",
        }
    )


def _build_session_metadata_table(metadata):
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


def _build_measurements_display_table(dataframe):
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


def _build_invalid_values_table(invalid_rows_by_column):
    return pd.DataFrame(
        [
            {
                "Data column": column_name,
                "Invalid or missing values": invalid_count,
            }
            for column_name, invalid_count in invalid_rows_by_column.items()
        ]
    )


def _build_outlier_summary_table(quality_dataframe):
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


def render_session_data_tab(application_data):
    metadata = application_data["metadata"]
    cleaned_dataframe = application_data["cleaned_dataframe"]

    st.caption(
        "Session information from the metadata file and cleaned measurements "
        "stored in the database."
    )

    st.subheader("Session Metadata")
    st.dataframe(
        _build_session_metadata_table(metadata),
        use_container_width=True,
        hide_index=True,
    )

    st.write(f"Source CSV: `{SOURCE_FILE_NAME}`")
    st.write(f"Source metadata: `{METADATA_FILE_NAME}`")

    st.subheader("Measurements")
    st.caption(f"{len(cleaned_dataframe)} cleaned rows stored in the database.")
    st.dataframe(
        _build_measurements_display_table(cleaned_dataframe),
        use_container_width=True,
        hide_index=True,
    )


def render_forward_driving_tab(application_data):
    analytics = application_data["analytics"]
    forward_metrics = analytics["forward_metrics"]
    analytics_dataframe = application_data["analytics_dataframe"]

    st.caption(ANALYTICS_NOTE)

    metric_columns = st.columns(5)
    with metric_columns[0]:
        _display_metric(
            "Average Speed",
            forward_metrics["average_speed"],
            help_text="Mean speed during forward driving (km/h).",
        )
    with metric_columns[1]:
        _display_metric(
            "Speed Variability",
            forward_metrics["speed_variability"],
            help_text="Standard deviation of speed. Higher values mean more fluctuation.",
        )
    with metric_columns[2]:
        _display_metric(
            "Steering Variability",
            forward_metrics["steering_variability"],
            help_text="Standard deviation of steering angle. Higher values mean more steering movement.",
        )
    with metric_columns[3]:
        _display_metric(
            "Total Turns",
            forward_metrics["total_turns"],
            format_string="{}",
            help_text="Measurements where steering angle is at least 20 degrees.",
        )
    with metric_columns[4]:
        _display_metric(
            "Sharp Turns",
            forward_metrics["sharp_turns"],
            format_string="{}",
            help_text="Measurements where steering angle is at least 25 degrees.",
        )

    _display_chart(
        "Forward Speed Profile",
        "Shows how speed changes sample-by-sample during forward driving. Each point is one measurement taken about one second apart.",
        plot_timeline(
            analytics_dataframe,
            MeasurementColumn.SPEED,
            reverse_state=0,
            y_label="Speed (km/h)",
        ),
    )
    _display_chart(
        "Steering Timeline",
        "Shows steering angle over time during forward driving. Positive and negative values indicate direction of turn.",
        plot_timeline(
            analytics_dataframe,
            MeasurementColumn.WHEEL_ANGLE,
            reverse_state=0,
            y_label="Steering angle (degrees)",
        ),
    )
    _display_chart(
        "Forward Speed Distribution",
        "Shows how frequently each speed value appears during forward driving.",
        plot_distribution(
            analytics_dataframe,
            MeasurementColumn.SPEED,
            reverse_state=0,
            xlabel="Speed (km/h)",
        ),
    )
    _display_chart(
        "Forward Steering Distribution",
        "Shows how often the driver used light vs heavy steering during forward driving.",
        plot_distribution(
            analytics_dataframe,
            MeasurementColumn.WHEEL_ANGLE,
            reverse_state=0,
            xlabel="Steering angle (degrees)",
        ),
    )
    _display_chart(
        "Average Speed by Steering Angle",
        "Average speed in each steering range. Darker bars = sharper steering. Y-axis zoomed to show differences.",
        plot_steering_buckets(analytics["steering_buckets"]),
    )


def render_reverse_driving_tab(application_data):
    analytics = application_data["analytics"]
    reverse_metrics = analytics["reverse_metrics"]
    analytics_dataframe = application_data["analytics_dataframe"]

    st.caption(ANALYTICS_NOTE)

    metric_columns = st.columns(3)
    with metric_columns[0]:
        _display_metric(
            "Reverse Percentage",
            reverse_metrics["reverse_percentage"],
            help_text="Share of all measurements recorded while driving in reverse.",
        )
    with metric_columns[1]:
        _display_metric(
            "Reverse Average Speed",
            reverse_metrics["reverse_average_speed"],
            help_text="Mean speed during reverse driving (km/h).",
        )
    with metric_columns[2]:
        _display_metric(
            "Reverse Steering Variability",
            reverse_metrics["reverse_steering_variability"],
            help_text="Standard deviation of steering angle during reverse driving.",
        )

    _display_chart(
        "Reverse Speed Distribution",
        "Shows how frequently each speed value appears while driving in reverse.",
        plot_distribution(
            analytics_dataframe,
            MeasurementColumn.SPEED,
            reverse_state=1,
            xlabel="Speed (km/h)",
        ),
    )
    _display_chart(
        "Reverse Steering Distribution",
        "Shows how steering angle is distributed while driving in reverse.",
        plot_distribution(
            analytics_dataframe,
            MeasurementColumn.WHEEL_ANGLE,
            reverse_state=1,
            xlabel="Steering angle (degrees)",
        ),
    )


def render_driver_behavior_tab(application_data):
    analytics = application_data["analytics"]
    behavior_metrics = analytics["behavior_metrics"]
    comparison = analytics["comparison"]
    analytics_dataframe = application_data["analytics_dataframe"]
    sample_rate_hz = application_data["metadata"].get("sample_rate_hz", 1)

    st.caption(ANALYTICS_NOTE)

    metric_columns = st.columns(2)
    with metric_columns[0]:
        _display_metric(
            "Steering Jerkiness",
            behavior_metrics["steering_jerkiness"],
            help_text="Average steering angle change between consecutive samples (degrees). Higher values mean jerkier steering.",
        )
    with metric_columns[1]:
        _display_metric(
            "Speed Instability",
            behavior_metrics["speed_instability"],
            help_text="Average speed change between consecutive samples (km/h). Higher values mean less stable speed control.",
        )

    alert_metric_columns = st.columns(2)
    with alert_metric_columns[0]:
        _display_metric(
            "Forward Sudden Corrections",
            behavior_metrics["forward_sudden_steering_events"],
            format_string="{}",
            help_text=(
                f"Threshold: {behavior_metrics['forward_sudden_steering_threshold']:.1f}° "
                "(forward mean + 1.5 standard deviations)."
            ),
        )
    with alert_metric_columns[1]:
        _display_metric(
            "Reverse Sudden Corrections",
            behavior_metrics["reverse_sudden_steering_events"],
            format_string="{}",
            help_text=(
                f"Threshold: {behavior_metrics['reverse_sudden_steering_threshold']:.1f}° "
                "(reverse mean + 1.5 standard deviations)."
            ),
        )

    _display_chart(
        "Forward Control Stability Timeline",
        "Steering change during forward driving. Threshold uses forward-only mean + 1.5 standard deviations.",
        plot_steering_correction_timeline(
            analytics_dataframe,
            behavior_metrics,
            reverse_state=0,
            sample_rate_hz=sample_rate_hz,
        ),
    )
    _display_chart(
        "Reverse Control Stability Timeline",
        "Steering change during reverse driving. Threshold uses reverse-only mean + 1.5 standard deviations.",
        plot_steering_correction_timeline(
            analytics_dataframe,
            behavior_metrics,
            reverse_state=1,
            sample_rate_hz=sample_rate_hz,
        ),
    )

    st.subheader("Forward vs Reverse Summary")
    st.caption(
        "Average steering change and speed change for each driving direction."
    )
    st.dataframe(
        _build_forward_reverse_display_table(comparison),
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
    _display_table(
        "Invalid Values by Column",
        "Counts missing or non-numeric values found in the raw CSV before rows were removed.",
        _build_invalid_values_table(quality_report["invalid_rows_by_column"]),
    )
    _display_table(
        "Outlier Summary",
        "Counts statistical outliers detected with the IQR method, analyzed separately for forward and reverse driving.",
        _build_outlier_summary_table(quality_dataframe),
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
