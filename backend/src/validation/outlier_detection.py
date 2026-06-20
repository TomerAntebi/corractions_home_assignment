"""
IQR outlier detection for validated measurement rows during import.

Callers pass the full validated measurement list. Invalid rows are skipped for IQR
scoring but remain in the returned list with is_outlier=False.
"""

import pandas as pd

from validation.models import (
    IQR_MINIMUM_SAMPLE_SIZE,
    IQR_MULTIPLIER,
    MeasurementRow,
)


def detect_outliers(validated_measurements: list[MeasurementRow]) -> list[MeasurementRow]:
    valid_rows = [
        measurement_row
        for measurement_row in validated_measurements
        if measurement_row.is_valid
    ]

    # Forward and reverse driving have different normal speed ranges, so each
    # driving context gets its own IQR bounds.
    for reverse_state in (False, True):
        grouped_valid_rows = [
            measurement_row
            for measurement_row in valid_rows
            if measurement_row.reverse_state is reverse_state
        ]
        mark_group_iqr_outliers("speed", grouped_valid_rows)
        mark_group_iqr_outliers("wheel_angle", grouped_valid_rows)

    return validated_measurements


def mark_group_iqr_outliers(
    field_name: str,
    valid_rows: list[MeasurementRow],
) -> None:
    field_values = [
        (measurement_row, numeric_value)
        for measurement_row in valid_rows
        if (numeric_value := get_numeric_field(measurement_row, field_name)) is not None
    ]

    # Small groups produce unstable quartiles, so they are not outlier-scored.
    if len(field_values) < IQR_MINIMUM_SAMPLE_SIZE:
        return

    lower_bound, upper_bound = calculate_iqr_bounds(
        [numeric_value for _, numeric_value in field_values]
    )

    for measurement_row, numeric_value in field_values:
        if numeric_value < lower_bound or numeric_value > upper_bound:
            measurement_row.is_outlier = True


def calculate_iqr_bounds(numeric_samples: list[float]) -> tuple[float, float]:
    numeric_series = pd.Series(numeric_samples)
    first_quartile = float(numeric_series.quantile(0.25))
    third_quartile = float(numeric_series.quantile(0.75))
    interquartile_range = third_quartile - first_quartile
    lower_bound = first_quartile - IQR_MULTIPLIER * interquartile_range
    upper_bound = third_quartile + IQR_MULTIPLIER * interquartile_range
    return lower_bound, upper_bound


def get_numeric_field(
    measurement_row: MeasurementRow,
    field_name: str,
) -> float | None:
    numeric_value = getattr(measurement_row, field_name)
    if numeric_value is None:
        return None

    return float(numeric_value)
