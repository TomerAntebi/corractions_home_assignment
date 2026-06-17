"""
Analytics calculations for validated field-test measurements.

Statistics are calculated from valid measurements, with outliers excluded by
default so unusual sensor values do not skew the operational summary.
"""

import numpy as np
import pandas as pd

from quality import QualityAnalysisEntry
from schemas.analytics_schemas import (
    AnalyticsResponse,
    NumericStatisticsResponse,
    ReverseStateSummaryResponse,
)
from validation.models import NormalizedMeasurement, ValidationResult


class StatisticsCalculator:
    def calculate_statistics(
        self,
        validated_measurements: list[ValidationResult | NormalizedMeasurement | dict[str, object | None]],
        quality_entries: list[QualityAnalysisEntry] | None = None,
    ) -> AnalyticsResponse:
        outlier_rows = {
            quality_entry.row_index
            for quality_entry in quality_entries or []
            if quality_entry.is_outlier
        }
        analyzed_measurements = [
            measurement
            for measurement in self._get_valid_measurements(validated_measurements)
            if measurement.row_index not in outlier_rows
        ]

        return AnalyticsResponse(
            analyzed_measurement_count=len(analyzed_measurements),
            speed=self._calculate_numeric_statistics(analyzed_measurements, "speed"),
            wheel_angle=self._calculate_numeric_statistics(analyzed_measurements, "wheel_angle"),
            reverse_state_summary=self._calculate_reverse_state_summary(analyzed_measurements),
        )

    def _get_valid_measurements(
        self,
        validated_measurements: list[ValidationResult | NormalizedMeasurement | dict[str, object | None]],
    ) -> list[NormalizedMeasurement]:
        valid_measurements: list[NormalizedMeasurement] = []

        for validated_measurement in validated_measurements:
            if isinstance(validated_measurement, ValidationResult):
                if validated_measurement.is_valid:
                    valid_measurements.append(validated_measurement.measurement)
                continue

            if isinstance(validated_measurement, NormalizedMeasurement):
                valid_measurements.append(validated_measurement)
                continue

            if bool(validated_measurement.get("is_valid", True)):
                valid_measurements.append(NormalizedMeasurement.model_validate(validated_measurement))

        return valid_measurements

    def _calculate_numeric_statistics(
        self,
        measurements: list[NormalizedMeasurement],
        field_name: str,
    ) -> NumericStatisticsResponse:
        numeric_values = [
            numeric_value
            for measurement in measurements
            if (numeric_value := getattr(measurement, field_name)) is not None
        ]

        if not numeric_values:
            return NumericStatisticsResponse(
                min=None,
                max=None,
                mean=None,
                median=None,
                std_dev=None,
                p5=None,
                p95=None,
            )

        numeric_series = pd.Series(numeric_values)

        # Percentiles use pandas quantile behavior to stay consistent with IQR analysis.
        return NumericStatisticsResponse(
            min=float(numeric_series.min()),
            max=float(numeric_series.max()),
            mean=float(numeric_series.mean()),
            median=float(numeric_series.median()),
            std_dev=float(np.std(numeric_values)),
            p5=float(numeric_series.quantile(0.05)),
            p95=float(numeric_series.quantile(0.95)),
        )

    def _calculate_reverse_state_summary(
        self,
        measurements: list[NormalizedMeasurement],
    ) -> ReverseStateSummaryResponse:
        reverse_count = sum(1 for measurement in measurements if measurement.reverse_state is True)
        forward_count = sum(1 for measurement in measurements if measurement.reverse_state is False)

        return ReverseStateSummaryResponse(
            forward_count=forward_count,
            reverse_count=reverse_count,
        )
