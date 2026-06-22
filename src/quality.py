"""Data quality — IQR outlier detection and missing-value reporting."""

import pandas as pd

from ingestion import MeasurementColumn, REQUIRED_COLUMNS

OUTLIER_FIELDS = (MeasurementColumn.SPEED, MeasurementColumn.WHEEL_ANGLE)
SENSOR_ERROR_MARKER = "ERROR_TIMEOUT"


def detect_outliers(series):
    valid_series = series.dropna()
    if valid_series.empty:
        return pd.Series(False, index=series.index)

    q1 = valid_series.quantile(0.25)
    q3 = valid_series.quantile(0.75)
    iqr = q3 - q1

    lower_bound = q1 - (1.5 * iqr)
    upper_bound = q3 + (1.5 * iqr)

    return (series < lower_bound) | (series > upper_bound)


def build_quality_dataframe(dataframe):
    quality_dataframe = dataframe.copy()
    for field_name in OUTLIER_FIELDS:
        quality_dataframe[f"{field_name}_outlier"] = False

    for reverse_state in (0, 1):
        driving_context_mask = quality_dataframe[MeasurementColumn.REVERSE_STATE] == reverse_state
        driving_context_dataframe = quality_dataframe.loc[driving_context_mask]

        for field_name in OUTLIER_FIELDS:
            outlier_mask = detect_outliers(driving_context_dataframe[field_name])
            quality_dataframe.loc[
                driving_context_mask,
                f"{field_name}_outlier",
            ] = outlier_mask.to_numpy()

    quality_dataframe["is_outlier"] = False
    for field_name in OUTLIER_FIELDS:
        quality_dataframe["is_outlier"] |= quality_dataframe[f"{field_name}_outlier"]

    return quality_dataframe


def build_analytics_dataframe(measurement_dataframe, quality_dataframe):
    """Keep all rows; set outlier sensor values to NaN for analytics and charts."""
    analytics_dataframe = measurement_dataframe.copy()

    for field_name in OUTLIER_FIELDS:
        outlier_mask = quality_dataframe[f"{field_name}_outlier"]
        analytics_dataframe.loc[outlier_mask, field_name] = float("nan")

    return analytics_dataframe


def count_sensor_error_rows(raw_dataframe):
    sensor_error_mask = pd.Series(False, index=raw_dataframe.index)

    for column_name in REQUIRED_COLUMNS:
        if column_name not in raw_dataframe.columns:
            continue

        sensor_error_mask |= raw_dataframe[column_name].astype(str).str.strip() == SENSOR_ERROR_MARKER

    return int(sensor_error_mask.sum())


def count_missing_values_by_column(dataframe):
    return {
        column_name: int(dataframe[column_name].isna().sum())
        for column_name in REQUIRED_COLUMNS
    }


def generate_quality_report(raw_dataframe, measurement_dataframe, quality_dataframe):
    missing_values_by_column = count_missing_values_by_column(measurement_dataframe)
    outlier_rows = int(quality_dataframe["is_outlier"].sum())
    sensor_error_rows = count_sensor_error_rows(raw_dataframe)

    return {
        "total_rows": len(raw_dataframe),
        "stored_rows": len(measurement_dataframe),
        "missing_values_by_column": missing_values_by_column,
        "missing_values": int(sum(missing_values_by_column.values())),
        "outlier_rows": outlier_rows,
        "sensor_error_rows": sensor_error_rows,
    }


def build_cleaning_summary_dataframe(quality_report):
    return pd.DataFrame(
        [
            {"stage": "Total rows in CSV", "row_count": quality_report["total_rows"]},
            {"stage": "Rows stored in database", "row_count": quality_report["stored_rows"]},
            {"stage": "Rows with missing values", "row_count": quality_report["missing_values"]},
            {"stage": "Outlier values excluded from analytics", "row_count": quality_report["outlier_rows"]},
        ]
    )
