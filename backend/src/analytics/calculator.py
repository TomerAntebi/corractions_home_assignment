"""
Analytics orchestration for validated field-test measurements.

Statistics are calculated from valid measurements, with outliers excluded by
default so unusual sensor values do not skew the operational summary.
"""

from db.models import MeasurementModel
from schemas.analytics_schemas import AnalyticsResponse

from analytics.driving_behavior import calculate_forward_driving, calculate_reverse_driving
from analytics.insights import build_driving_insights


class StatisticsCalculator:
    def calculate_statistics(
        self,
        measurements: list[MeasurementModel],
    ) -> AnalyticsResponse:
        analyzed_measurement_count = 0
        forward_measurements: list[MeasurementModel] = []
        reverse_measurements: list[MeasurementModel] = []

        for measurement in measurements:
            if not measurement.is_valid or measurement.is_outlier:
                continue

            analyzed_measurement_count += 1

            if measurement.reverse_state is False:
                forward_measurements.append(measurement)
            elif measurement.reverse_state is True:
                reverse_measurements.append(measurement)
            # Rows with reverse_state is None are analyzed but excluded from
            # forward/reverse metric groups; they still count toward reverse %.

        forward_driving = calculate_forward_driving(forward_measurements)
        reverse_driving = calculate_reverse_driving(
            analyzed_measurement_count,
            reverse_measurements,
        )

        return AnalyticsResponse(
            forward_driving=forward_driving,
            reverse_driving=reverse_driving,
            driving_insights=build_driving_insights(forward_driving, reverse_driving),
        )
