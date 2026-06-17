"""
Data quality analysis for validated measurement rows.

Quality analysis detects statistical outliers and summarizes validation issues.
Invalid measurements are excluded from outlier detection because they should not
influence the distribution used to judge valid sensor values.
"""

import pandas as pd
from pydantic import BaseModel

from validation.models import ValidationResult


IQR_MINIMUM_SAMPLE_SIZE = 5
IQR_MULTIPLIER = 1.5


class QualityAnalysisEntry(BaseModel):
    row_index: int
    is_outlier: bool


class DataQualityReport(BaseModel):
    total_rows: int
    valid_rows: int
    invalid_rows: int
    outlier_rows: int
    quality_score: float
    missing_by_field: dict[str, int]
    invalid_by_rule: dict[str, int]
    sensor_errors: list[str]


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
        numeric_values = [
            self._get_numeric_field(validation_result, field_name)
            for validation_result in valid_validation_results
            if self._get_numeric_field(validation_result, field_name) is not None
        ]

        # Small groups produce unstable quartiles, so they are not outlier-scored.
        if len(numeric_values) < IQR_MINIMUM_SAMPLE_SIZE:
            return

        numeric_series = pd.Series(numeric_values)
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


class DataQualityReporter:
    def generate_quality_report(
        self,
        total_rows: int,
        validation_results: list[ValidationResult],
        quality_entries: list[QualityAnalysisEntry],
    ) -> DataQualityReport:
        valid_rows = sum(1 for validation_result in validation_results if validation_result.is_valid)
        invalid_rows = total_rows - valid_rows
        outlier_rows = sum(1 for quality_entry in quality_entries if quality_entry.is_outlier)

        return DataQualityReport(
            total_rows=total_rows,
            valid_rows=valid_rows,
            invalid_rows=invalid_rows,
            outlier_rows=outlier_rows,
            quality_score=self._calculate_quality_score(total_rows, valid_rows, outlier_rows),
            missing_by_field=self._count_missing_fields(validation_results),
            invalid_by_rule=self._count_invalid_rules(validation_results),
            sensor_errors=self._collect_sensor_errors(validation_results),
        )

    def _calculate_quality_score(
        self,
        total_rows: int,
        valid_rows: int,
        outlier_rows: int,
    ) -> float:
        if total_rows == 0:
            return 0

        # The score keeps validation failures as the primary penalty and applies
        # a smaller penalty for valid rows that are statistically unusual.
        return max(0, valid_rows / total_rows - (outlier_rows / total_rows * 0.3))

    def _count_missing_fields(self, validation_results: list[ValidationResult]) -> dict[str, int]:
        missing_by_field: dict[str, int] = {}

        for validation_result in validation_results:
            for validation_issue in validation_result.issues:
                if validation_issue.rule == "required":
                    missing_by_field[validation_issue.field] = (
                        missing_by_field.get(validation_issue.field, 0) + 1
                    )

        return missing_by_field

    def _count_invalid_rules(self, validation_results: list[ValidationResult]) -> dict[str, int]:
        invalid_by_rule: dict[str, int] = {}

        for validation_result in validation_results:
            for validation_issue in validation_result.issues:
                invalid_by_rule[validation_issue.rule] = (
                    invalid_by_rule.get(validation_issue.rule, 0) + 1
                )

        return invalid_by_rule

    def _collect_sensor_errors(self, validation_results: list[ValidationResult]) -> list[str]:
        sensor_errors: list[str] = []

        for validation_result in validation_results:
            for validation_issue in validation_result.issues:
                if (
                    validation_issue.rule == "invalid_marker"
                    and validation_issue.raw_value is not None
                    and validation_issue.raw_value not in sensor_errors
                ):
                    sensor_errors.append(validation_issue.raw_value)

        return sensor_errors
