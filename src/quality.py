"""Data quality — IQR outlier detection, cleaning summaries, and analytics-ready row filtering."""

import pandas as pd

from ingestion import MeasurementColumn, REQUIRED_COLUMNS

OUTLIER_FIELDS = (MeasurementColumn.SPEED, MeasurementColumn.WHEEL_ANGLE)
SENSOR_ERROR_MARKER = "ERROR_TIMEOUT"


def detect_outliers(series):
    q1 = series.quantile(0.25)
    q3 = series.quantile(0.75)

    iqr = q3 - q1

    lower_bound = q1 - (1.5 * iqr)
    upper_bound = q3 + (1.5 * iqr)

    return (
        (series < lower_bound)
        | (series > upper_bound)
    )


def build_quality_dataframe(dataframe):
    quality_dataframe = dataframe.copy()
    quality_dataframe[f"{MeasurementColumn.SPEED}_outlier"] = False
    quality_dataframe[f"{MeasurementColumn.WHEEL_ANGLE}_outlier"] = False

    for reverse_state in (0, 1):
        driving_context_mask = (
            quality_dataframe[MeasurementColumn.REVERSE_STATE] == reverse_state
        )
        driving_context_dataframe = quality_dataframe.loc[driving_context_mask]

        for field_name in OUTLIER_FIELDS:
            outlier_mask = detect_outliers(
                driving_context_dataframe[field_name]
            )
            quality_dataframe.loc[
                driving_context_mask,
                f"{field_name}_outlier",
            ] = outlier_mask.to_numpy()

    quality_dataframe["is_outlier"] = (
        quality_dataframe[f"{MeasurementColumn.SPEED}_outlier"]
        | quality_dataframe[f"{MeasurementColumn.WHEEL_ANGLE}_outlier"]
    )

    return quality_dataframe


def build_analytics_dataframe(cleaned_dataframe, quality_dataframe):
    return cleaned_dataframe.loc[
        ~quality_dataframe["is_outlier"]
    ].reset_index(drop=True)


def count_sensor_error_rows(raw_dataframe):
    sensor_error_mask = pd.Series(False, index=raw_dataframe.index)

    for column_name in REQUIRED_COLUMNS:
        if column_name not in raw_dataframe.columns:
            continue

        sensor_error_mask |= (
            raw_dataframe[column_name]
            .astype(str)
            .str.strip()
            == SENSOR_ERROR_MARKER
        )

    return int(sensor_error_mask.sum())


def count_invalid_rows_by_column(normalized_dataframe):
    return {
        column_name: int(normalized_dataframe[column_name].isna().sum())
        for column_name in REQUIRED_COLUMNS
    }


def generate_quality_report(
    raw_dataframe,
    normalized_dataframe,
    cleaned_dataframe,
    quality_dataframe,
):
    total_rows = len(raw_dataframe)
    cleaned_rows = len(cleaned_dataframe)
    invalid_rows = total_rows - cleaned_rows
    outlier_rows = int(quality_dataframe["is_outlier"].sum())
    analytics_rows = cleaned_rows - outlier_rows

    invalid_rows_by_column = count_invalid_rows_by_column(normalized_dataframe)
    sensor_error_rows = count_sensor_error_rows(raw_dataframe)

    return {
        "total_rows": total_rows,
        "invalid_rows": invalid_rows,
        "invalid_rows_by_column": invalid_rows_by_column,
        "sensor_error_rows": sensor_error_rows,
        "cleaned_rows": cleaned_rows,
        "outlier_rows": outlier_rows,
        "analytics_rows": analytics_rows,
        "missing_values_by_column": invalid_rows_by_column,
        "missing_values": int(sum(invalid_rows_by_column.values())),
    }


def build_cleaning_summary_dataframe(quality_report):
    return pd.DataFrame(
        [
            {"stage": "Total rows in CSV", "row_count": quality_report["total_rows"]},
            {
                "stage": "Invalid rows removed",
                "row_count": quality_report["invalid_rows"],
            },
            {
                "stage": "Rows stored in database",
                "row_count": quality_report["cleaned_rows"],
            },
            {
                "stage": "Outlier rows excluded from analytics",
                "row_count": quality_report["outlier_rows"],
            },
            {
                "stage": "Rows used for analysis",
                "row_count": quality_report["analytics_rows"],
            },
        ]
    )
