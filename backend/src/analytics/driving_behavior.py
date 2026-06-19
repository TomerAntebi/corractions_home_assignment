"""Driver behavior metrics for validated field-test measurements."""

import pandas as pd

from db.models import MeasurementModel
from schemas.analytics_schemas import ForwardDrivingResponse, ReverseDrivingResponse

from analytics.statistics import (
    build_forward_timeline,
    calculate_speed_mean,
    mean_or_none,
    std_or_none,
)


TURN_ANGLE_THRESHOLD_DEGREES = 20.0
SHARP_TURN_ANGLE_THRESHOLD_DEGREES = 25.0


def calculate_speed_steering_correlation(
    forward_measurements: list[MeasurementModel],
) -> float | None:
    correlation_measurements = [
        {
            "speed": measurement.speed,
            "absolute_wheel_angle": abs(measurement.wheel_angle),
        }
        for measurement in forward_measurements
        if measurement.speed is not None and measurement.wheel_angle is not None
    ]
    if not correlation_measurements:
        return None

    correlation_dataframe = pd.DataFrame(correlation_measurements)
    speed_steering_correlation = correlation_dataframe["speed"].corr(
        correlation_dataframe["absolute_wheel_angle"]
    )
    if pd.isna(speed_steering_correlation):
        return None

    return float(speed_steering_correlation)


def calculate_forward_driving(
    forward_measurements: list[MeasurementModel],
) -> ForwardDrivingResponse:
    wheel_angles, speeds, turn_speeds, straight_speeds, sharp_turns = (
        _calculate_forward_metrics(forward_measurements)
    )
    speed_steering_correlation = (
        calculate_speed_steering_correlation(forward_measurements)
        if forward_measurements
        else None
    )

    return ForwardDrivingResponse(
        speed_mean=calculate_speed_mean(forward_measurements),
        steering_variability=std_or_none(wheel_angles),
        speed_variability=std_or_none(speeds),
        total_turns=len(turn_speeds),
        sharp_turns=sharp_turns,
        average_speed_during_turns=mean_or_none(turn_speeds),
        average_speed_during_straight_driving=mean_or_none(straight_speeds),
        speed_steering_correlation=speed_steering_correlation,
        timeline=build_forward_timeline(forward_measurements),
    )


def calculate_reverse_driving(
    analyzed_measurements: list[MeasurementModel],
    reverse_measurements: list[MeasurementModel],
) -> ReverseDrivingResponse:
    analyzed_row_count = len(analyzed_measurements)
    reverse_percentage = (
        len(reverse_measurements) / analyzed_row_count
        if analyzed_row_count > 0
        else 0.0
    )
    reverse_wheel_angles = [
        measurement.wheel_angle
        for measurement in reverse_measurements
        if measurement.wheel_angle is not None
    ]

    return ReverseDrivingResponse(
        measurement_count=len(reverse_measurements),
        percentage=reverse_percentage,
        average_speed=mean_or_none(
            [
                measurement.speed
                for measurement in reverse_measurements
                if measurement.speed is not None
            ]
        ),
        steering_variability=std_or_none(reverse_wheel_angles),
    )


def _calculate_forward_metrics(
    forward_measurements: list[MeasurementModel],
) -> tuple[list[float], list[float], list[float], list[float], int]:
    wheel_angles: list[float] = []
    speeds: list[float] = []
    turn_speeds: list[float] = []
    straight_speeds: list[float] = []
    sharp_turns = 0

    for measurement in forward_measurements:
        if measurement.speed is not None:
            speeds.append(measurement.speed)

        if measurement.wheel_angle is None:
            continue

        wheel_angle = measurement.wheel_angle
        wheel_angles.append(wheel_angle)
        absolute_wheel_angle = abs(wheel_angle)

        if absolute_wheel_angle >= SHARP_TURN_ANGLE_THRESHOLD_DEGREES:
            sharp_turns += 1

        if measurement.speed is None:
            continue

        if absolute_wheel_angle >= TURN_ANGLE_THRESHOLD_DEGREES:
            turn_speeds.append(measurement.speed)
        else:
            straight_speeds.append(measurement.speed)

    return wheel_angles, speeds, turn_speeds, straight_speeds, sharp_turns
