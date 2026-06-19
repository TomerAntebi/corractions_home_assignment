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
        analyzed_measurements = [
            measurement
            for measurement in measurements
            if measurement.is_valid and not measurement.is_outlier
        ]
        forward_measurements = [
            measurement
            for measurement in analyzed_measurements
            if measurement.reverse_state is False
        ]
        reverse_measurements = [
            measurement
            for measurement in analyzed_measurements
            if measurement.reverse_state is True
        ]
        forward_driving = calculate_forward_driving(forward_measurements)
        reverse_driving = calculate_reverse_driving(
            analyzed_measurements,
            reverse_measurements,
        )

        return AnalyticsResponse(
            forward_driving=forward_driving,
            reverse_driving=reverse_driving,
            driving_insights=build_driving_insights(forward_driving, reverse_driving),
        )
