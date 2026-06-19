"""
Statistical outlier detection for validated measurement rows.

Callers must pass only validation-passing rows. Invalid measurements are excluded
upstream because they should not influence the distribution used to judge valid
sensor values.
"""

import pandas as pd

from quality.models import IQR_MINIMUM_SAMPLE_SIZE, IQR_MULTIPLIER
from validation.models import ValidationResult


class DataQualityAnalyzer:
    def detect_outliers(self, valid_rows: list[ValidationResult]) -> set[int]:
        outlier_row_indices: set[int] = set()

        # Forward and reverse driving have different normal speed ranges, so each
        # driving context gets its own IQR bounds.
        for reverse_state in (False, True):
            grouped_valid_rows = [
                validation_result
                for validation_result in valid_rows
                if validation_result.measurement.reverse_state is reverse_state
            ]
            self._mark_group_iqr_outliers("speed", grouped_valid_rows, outlier_row_indices)
            self._mark_group_iqr_outliers("wheel_angle",grouped_valid_rows,outlier_row_indices)

        return outlier_row_indices

    def _mark_group_iqr_outliers(
        self,
        field_name: str,
        valid_rows: list[ValidationResult],
        outlier_row_indices: set[int],
    ) -> None:
        field_values = [
            (validation_result, numeric_value)
            for validation_result in valid_rows
            if (numeric_value := self._get_numeric_field(validation_result, field_name))
            is not None
        ]

        # Small groups produce unstable quartiles, so they are not outlier-scored.
        if len(field_values) < IQR_MINIMUM_SAMPLE_SIZE:
            return

        lower_bound, upper_bound = self._calculate_iqr_bounds(
            [numeric_value for _, numeric_value in field_values]
        )

        for validation_result, numeric_value in field_values:
            if numeric_value < lower_bound or numeric_value > upper_bound:
                outlier_row_indices.add(validation_result.measurement.row_index)

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
        validation_result: ValidationResult,
        field_name: str,
    ) -> float | None:
        numeric_value = getattr(validation_result.measurement, field_name)
        if numeric_value is None:
            return None

        return float(numeric_value)
