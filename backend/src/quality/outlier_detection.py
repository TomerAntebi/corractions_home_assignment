"""
Statistical outlier detection for validated measurement rows.

Callers must pass only validation-passing rows. Invalid measurements are excluded
upstream because they should not influence the distribution used to judge valid
sensor values.
"""

import pandas as pd

from quality.models import IQR_MINIMUM_SAMPLE_SIZE, IQR_MULTIPLIER
from validation.models import MeasurementRow


class DataQualityAnalyzer:
    def detect_outliers(self, validated_measurements: list[MeasurementRow]) -> set[int]:
        outlier_row_indices: set[int] = set()

        # Forward and reverse driving have different normal speed ranges, so each
        # driving context gets its own IQR bounds.
        for reverse_state in (False, True):
            grouped_valid_rows = [
                measurement_row
                for measurement_row in validated_measurements
                if measurement_row.reverse_state is reverse_state
            ]
            self._mark_group_iqr_outliers("speed", grouped_valid_rows, outlier_row_indices)
            self._mark_group_iqr_outliers("wheel_angle", grouped_valid_rows, outlier_row_indices)

        return outlier_row_indices

    def _mark_group_iqr_outliers(
        self,
        field_name: str,
        valid_rows: list[MeasurementRow],
        outlier_row_indices: set[int],
    ) -> None:
        field_values = [
            (measurement_row, numeric_value)
            for measurement_row in valid_rows
            if (numeric_value := self._get_numeric_field(measurement_row, field_name))
            is not None
        ]

        # Small groups produce unstable quartiles, so they are not outlier-scored.
        if len(field_values) < IQR_MINIMUM_SAMPLE_SIZE:
            return

        lower_bound, upper_bound = self._calculate_iqr_bounds(
            [numeric_value for _, numeric_value in field_values]
        )

        for measurement_row, numeric_value in field_values:
            if numeric_value < lower_bound or numeric_value > upper_bound:
                outlier_row_indices.add(measurement_row.row_index)

    def _calculate_iqr_bounds(self, numeric_samples: list[float]) -> tuple[float, float]:
        numeric_series = pd.Series(numeric_samples)
        first_quartile = float(numeric_series.quantile(0.25))
        third_quartile = float(numeric_series.quantile(0.75))
        interquartile_range = third_quartile - first_quartile
        lower_bound = first_quartile - IQR_MULTIPLIER * interquartile_range
        upper_bound = third_quartile + IQR_MULTIPLIER * interquartile_range
        return lower_bound, upper_bound

    def _get_numeric_field(
        self,
        measurement_row: MeasurementRow,
        field_name: str,
    ) -> float | None:
        numeric_value = getattr(measurement_row, field_name)
        if numeric_value is None:
            return None

        return float(numeric_value)
