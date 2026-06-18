"""
Data quality analysis for validated measurement rows.

Quality analysis detects statistical outliers and summarizes validation issues.
Invalid measurements are excluded from outlier detection because they should not
influence the distribution used to judge valid sensor values.
"""

import pandas as pd
from pydantic import BaseModel, ConfigDict, Field

from db.models import MeasurementModel
from validation.models import ValidationResult


IQR_MINIMUM_SAMPLE_SIZE = 5
IQR_MULTIPLIER = 1.5


class QualityAnalysisEntry(BaseModel):
    row_index: int
    is_outlier: bool


class DataQualityReport(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    total_rows: int = Field(alias="totalRows")
    valid_rows: int = Field(alias="validRows")
    invalid_rows: int = Field(alias="invalidRows")
    outlier_rows: int = Field(alias="outlierRows")
    missing_by_field: dict[str, int] = Field(alias="missingByField")
    invalid_by_rule: dict[str, int] = Field(alias="invalidByRule")
    sensor_errors: list[str] = Field(alias="sensorErrors")


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
    def generate_quality_report_from_measurements(
        self,
        measurements: list[MeasurementModel],
    ) -> DataQualityReport:
        total_rows = len(measurements)
        valid_rows = sum(1 for measurement in measurements if measurement.is_valid)
        outlier_rows = sum(1 for measurement in measurements if measurement.is_outlier)

        return DataQualityReport(
            total_rows=total_rows,
            valid_rows=valid_rows,
            invalid_rows=total_rows - valid_rows,
            outlier_rows=outlier_rows,
            missing_by_field=self._count_missing_fields_from_measurements(measurements),
            invalid_by_rule=self._count_invalid_rules_from_measurements(measurements),
            sensor_errors=self._collect_sensor_errors_from_measurements(measurements),
        )

    def _count_missing_fields_from_measurements(
        self,
        measurements: list[MeasurementModel],
    ) -> dict[str, int]:
        missing_by_field: dict[str, int] = {}

        for measurement in measurements:
            for validation_error in measurement.validation_errors:
                if validation_error.get("rule") == "required":
                    field = str(validation_error["field"])
                    missing_by_field[field] = missing_by_field.get(field, 0) + 1

        return missing_by_field

    def _count_invalid_rules_from_measurements(
        self,
        measurements: list[MeasurementModel],
    ) -> dict[str, int]:
        invalid_by_rule: dict[str, int] = {}

        for measurement in measurements:
            for validation_error in measurement.validation_errors:
                rule = str(validation_error["rule"])
                invalid_by_rule[rule] = invalid_by_rule.get(rule, 0) + 1

        return invalid_by_rule

    def _collect_sensor_errors_from_measurements(
        self,
        measurements: list[MeasurementModel],
    ) -> list[str]:
        sensor_errors: list[str] = []

        for measurement in measurements:
            for validation_error in measurement.validation_errors:
                raw_value = validation_error.get("raw_value")
                if (
                    validation_error.get("rule") == "invalid_marker"
                    and raw_value is not None
                    and str(raw_value) not in sensor_errors
                ):
                    sensor_errors.append(str(raw_value))

        return sensor_errors
