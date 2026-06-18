"""
Analytics calculations for validated field-test measurements.

Statistics are calculated from valid measurements, with outliers excluded by
default so unusual sensor values do not skew the operational summary.
"""

import numpy as np
import pandas as pd

from db.models import MeasurementModel
from schemas.analytics_schemas import AnalyticsResponse, DrivingBehaviorResponse


TURN_ANGLE_THRESHOLD_DEGREES = 20.0
SHARP_TURN_ANGLE_THRESHOLD_DEGREES = 25.0
LOW_STEERING_VARIABILITY_THRESHOLD = 10.0
HIGH_STEERING_VARIABILITY_THRESHOLD = 20.0
LOW_SPEED_VARIABILITY_THRESHOLD = 10.0
CORRELATION_THRESHOLD = 0.3
REVERSE_INSIGHT_THRESHOLD = 0.1


class StatisticsCalculator:
    def calculate_statistics(
        self,
        measurements: list[MeasurementModel],
    ) -> AnalyticsResponse:
        analyzed_measurements = self._filter_analyzed_measurements(measurements)
        forward_measurements = self._filter_forward_measurements(analyzed_measurements)
        reverse_measurements = self._filter_reverse_measurements(analyzed_measurements)
        driving_behavior = self._calculate_driving_behavior(
            analyzed_measurements,
            forward_measurements,
            reverse_measurements,
        )

        return AnalyticsResponse(
            speed_mean=self._calculate_mean(analyzed_measurements, "speed"),
            wheel_angle_mean=self._calculate_mean(analyzed_measurements, "wheel_angle"),
            driving_behavior=driving_behavior,
            driving_insights=self._build_driving_insights(driving_behavior),
        )

    # Filters
    def _filter_analyzed_measurements(
        self,
        measurements: list[MeasurementModel],
    ) -> list[MeasurementModel]:
        return [
            measurement
            for measurement in measurements
            if measurement.is_valid and not measurement.is_outlier
        ]

    def _filter_forward_measurements(
        self,
        analyzed_measurements: list[MeasurementModel],
    ) -> list[MeasurementModel]:
        return [
            measurement
            for measurement in analyzed_measurements
            if measurement.reverse_state is False
        ]

    def _filter_reverse_measurements(
        self,
        analyzed_measurements: list[MeasurementModel],
    ) -> list[MeasurementModel]:
        return [
            measurement
            for measurement in analyzed_measurements
            if measurement.reverse_state is True
        ]

    def _calculate_mean(
        self,
        measurements: list[MeasurementModel],
        field_name: str,
    ) -> float | None:
        numeric_values = [
            numeric_value
            for measurement in measurements
            if (numeric_value := getattr(measurement, field_name)) is not None
        ]

        return self._mean_or_none(numeric_values)

    # Driving behavior
    def _calculate_driving_behavior(
        self,
        analyzed_measurements: list[MeasurementModel],
        forward_measurements: list[MeasurementModel],
        reverse_measurements: list[MeasurementModel],
    ) -> DrivingBehaviorResponse:
        analyzed_row_count = len(analyzed_measurements)
        reverse_percentage = (
            len(reverse_measurements) / analyzed_row_count
            if analyzed_row_count > 0
            else 0.0
        )
        average_reverse_speed = self._mean_or_none(
            [measurement.speed for measurement in reverse_measurements if measurement.speed is not None]
        )

        if not forward_measurements:
            return DrivingBehaviorResponse(
                steering_variability=None,
                speed_variability=None,
                total_turns=0,
                sharp_turns=0,
                average_speed_during_turns=None,
                average_speed_during_straight_driving=None,
                speed_steering_correlation=None,
                speed_steering_correlation_caption=self._describe_speed_steering_correlation(None),
                reverse_percentage=reverse_percentage,
                average_reverse_speed=average_reverse_speed,
            )

        wheel_angles = [
            measurement.wheel_angle
            for measurement in forward_measurements
            if measurement.wheel_angle is not None
        ]
        speeds = [
            measurement.speed
            for measurement in forward_measurements
            if measurement.speed is not None
        ]
        turn_speeds = [
            measurement.speed
            for measurement in forward_measurements
            if measurement.wheel_angle is not None
            and measurement.speed is not None
            and abs(measurement.wheel_angle) >= TURN_ANGLE_THRESHOLD_DEGREES
        ]
        straight_speeds = [
            measurement.speed
            for measurement in forward_measurements
            if measurement.wheel_angle is not None
            and measurement.speed is not None
            and abs(measurement.wheel_angle) < TURN_ANGLE_THRESHOLD_DEGREES
        ]
        sharp_turns = sum(
            1
            for measurement in forward_measurements
            if measurement.wheel_angle is not None
            and abs(measurement.wheel_angle) >= SHARP_TURN_ANGLE_THRESHOLD_DEGREES
        )
        speed_steering_correlation = self._calculate_speed_steering_correlation(forward_measurements)

        return DrivingBehaviorResponse(
            steering_variability=self._std_or_none(wheel_angles),
            speed_variability=self._std_or_none(speeds),
            total_turns=len(turn_speeds),
            sharp_turns=sharp_turns,
            average_speed_during_turns=self._mean_or_none(turn_speeds),
            average_speed_during_straight_driving=self._mean_or_none(straight_speeds),
            speed_steering_correlation=speed_steering_correlation,
            speed_steering_correlation_caption=self._describe_speed_steering_correlation(
                speed_steering_correlation
            ),
            reverse_percentage=reverse_percentage,
            average_reverse_speed=average_reverse_speed,
        )

    def _calculate_speed_steering_correlation(
        self,
        forward_measurements: list[MeasurementModel],
    ) -> float | None:
        correlation_rows = [
            {
                "speed": measurement.speed,
                "absolute_wheel_angle": abs(measurement.wheel_angle),
            }
            for measurement in forward_measurements
            if measurement.speed is not None and measurement.wheel_angle is not None
        ]
        if not correlation_rows:
            return None

        correlation_dataframe = pd.DataFrame(correlation_rows)
        speed_steering_correlation = correlation_dataframe["speed"].corr(
            correlation_dataframe["absolute_wheel_angle"]
        )
        if pd.isna(speed_steering_correlation):
            return None

        return float(speed_steering_correlation)

    # Insights
    def _build_driving_insights(self, driving_behavior: DrivingBehaviorResponse) -> list[str]:
        insight_rows: list[str] = []

        if driving_behavior.steering_variability is not None:
            if driving_behavior.steering_variability < LOW_STEERING_VARIABILITY_THRESHOLD:
                insight_rows.append(
                    "Steering behavior remained relatively stable throughout the session."
                )
            elif driving_behavior.steering_variability >= HIGH_STEERING_VARIABILITY_THRESHOLD:
                insight_rows.append("Steering behavior showed frequent steering corrections.")

        if (
            driving_behavior.speed_variability is not None
            and driving_behavior.speed_variability < LOW_SPEED_VARIABILITY_THRESHOLD
        ):
            insight_rows.append("Vehicle speed remained relatively stable during the session.")

        if driving_behavior.sharp_turns > 0:
            insight_rows.append(
                f"{driving_behavior.sharp_turns:,} sharp turn measurements were detected."
            )

        if driving_behavior.speed_steering_correlation is None:
            insight_rows.append(
                "There is not enough data to measure speed and steering relationship."
            )
        elif (
            -CORRELATION_THRESHOLD
            <= driving_behavior.speed_steering_correlation
            <= CORRELATION_THRESHOLD
        ):
            insight_rows.append(
                "No meaningful relationship was detected between steering intensity and vehicle speed."
            )

        if driving_behavior.reverse_percentage > REVERSE_INSIGHT_THRESHOLD:
            reverse_percentage_text = f"{driving_behavior.reverse_percentage * 100:.0f}%"
            insight_rows.append(
                f"Reverse driving represented {reverse_percentage_text} of analyzed measurements."
            )

        if not insight_rows:
            insight_rows.append(
                "No strong driving behavior patterns stood out from the measured values."
            )

        return insight_rows

    def _describe_speed_steering_correlation(self, correlation: float | None) -> str:
        if correlation is None:
            return "There is not enough data to compare speed and steering intensity."
        if correlation < -CORRELATION_THRESHOLD:
            return "Driver generally reduced speed while turning."
        if correlation <= CORRELATION_THRESHOLD:
            return "No clear relationship between speed and steering intensity."

        return "Higher steering angles tended to occur at higher speeds."

    def _mean_or_none(self, numeric_values: list[float]) -> float | None:
        if not numeric_values:
            return None

        mean_value = float(np.mean(numeric_values))
        if pd.isna(mean_value):
            return None

        return mean_value

    def _std_or_none(self, numeric_values: list[float]) -> float | None:
        if not numeric_values:
            return None

        std_value = float(np.std(numeric_values))
        if pd.isna(std_value):
            return None

        return std_value
