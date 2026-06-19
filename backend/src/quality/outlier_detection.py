"""
Statistical outlier detection for validated measurement rows.

Invalid measurements are excluded from outlier detection because they should not
influence the distribution used to judge valid sensor values.
"""

import pandas as pd

from quality.models import IQR_MINIMUM_SAMPLE_SIZE, IQR_MULTIPLIER, QualityAnalysisEntry
from validation.models import ValidationResult


class DataQualityAnalyzer:
    def analyze_quality(self, validation_results: list[ValidationResult]) -> list[QualityAnalysisEntry]:
        quality_entries = [
            QualityAnalysisEntry(
                row_index=validation_result.measurement.row_index,
                is_outlier=False,
            )
            for validation_result in validation_results
        ]

        valid_validation_results = [
            validation_result
            for validation_result in validation_results
            if validation_result.is_valid
        ]

        # IQR adapts to each session's distribution instead of relying on fixed thresholds.
        self._mark_iqr_outliers("speed", valid_validation_results, quality_entries)
        self._mark_iqr_outliers("wheel_angle", valid_validation_results, quality_entries)

        return quality_entries

    def _mark_iqr_outliers(
        self,
        field_name: str,
        valid_validation_results: list[ValidationResult],
        quality_entries: list[QualityAnalysisEntry],
    ) -> None:
        # Forward and reverse driving have different normal speed ranges, so each
        # driving context gets its own IQR bounds.
        for grouped_validation_results in self._group_by_reverse_state(valid_validation_results):
            self._mark_group_iqr_outliers(field_name, grouped_validation_results, quality_entries)

    def _group_by_reverse_state(
        self,
        valid_validation_results: list[ValidationResult],
    ) -> list[list[ValidationResult]]:
        return [
            [
                validation_result
                for validation_result in valid_validation_results
                if validation_result.measurement.reverse_state is reverse_state
            ]
            for reverse_state in (False, True)
        ]

    def _mark_group_iqr_outliers(
        self,
        field_name: str,
        valid_validation_results: list[ValidationResult],
        quality_entries: list[QualityAnalysisEntry],
    ) -> None:
        numeric_samples = [
            self._get_numeric_field(validation_result, field_name)
            for validation_result in valid_validation_results
            if self._get_numeric_field(validation_result, field_name) is not None
        ]

        # Small groups produce unstable quartiles, so they are not outlier-scored.
        if len(numeric_samples) < IQR_MINIMUM_SAMPLE_SIZE:
            return

        numeric_series = pd.Series(numeric_samples)
        first_quartile = float(numeric_series.quantile(0.25))
        third_quartile = float(numeric_series.quantile(0.75))
        interquartile_range = third_quartile - first_quartile
        lower_bound = first_quartile - IQR_MULTIPLIER * interquartile_range
        upper_bound = third_quartile + IQR_MULTIPLIER * interquartile_range

        entries_by_row_index = {
            quality_entry.row_index: quality_entry
            for quality_entry in quality_entries
        }

        for validation_result in valid_validation_results:
            numeric_value = self._get_numeric_field(validation_result, field_name)
            if numeric_value is None:
                continue

            if numeric_value < lower_bound or numeric_value > upper_bound:
                quality_entry = entries_by_row_index[validation_result.measurement.row_index]
                quality_entry.is_outlier = True

    def _get_numeric_field(
        self,
        validation_result: ValidationResult,
        field_name: str,
    ) -> float | None:
        numeric_value = getattr(validation_result.measurement, field_name)
        if numeric_value is None:
            return None

        return float(numeric_value)
