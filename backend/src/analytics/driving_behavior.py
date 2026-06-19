"""Driver behavior metrics for validated field-test measurements."""

from dataclasses import dataclass

from db.models import MeasurementModel
from schemas.analytics_schemas import ForwardDrivingResponse, ReverseDrivingResponse

from analytics.insights import describe_speed_steering_correlation
from analytics.statistics import (
    build_forward_timeline,
    build_speed_steering_scatter,
    calculate_speed_mean,
    calculate_wheel_angle_mean,
    mean_or_none,
    std_or_none,
)
from analytics.steering_analysis import calculate_speed_steering_correlation


TURN_ANGLE_THRESHOLD_DEGREES = 20.0
SHARP_TURN_ANGLE_THRESHOLD_DEGREES = 25.0


@dataclass
class ForwardDrivingMetrics:
    wheel_angles: list[float]
    speeds: list[float]
    turn_speeds: list[float]
    straight_speeds: list[float]
    sharp_turns: int


def calculate_forward_driving(
    forward_measurements: list[MeasurementModel],
) -> ForwardDrivingResponse:
    forward_metrics = _calculate_forward_metrics(forward_measurements)
    speed_steering_correlation = (
        calculate_speed_steering_correlation(forward_measurements)
        if forward_measurements
        else None
    )

    return ForwardDrivingResponse(
        speed_mean=calculate_speed_mean(forward_measurements),
        wheel_angle_mean=calculate_wheel_angle_mean(forward_measurements),
        steering_variability=std_or_none(forward_metrics.wheel_angles),
        speed_variability=std_or_none(forward_metrics.speeds),
        total_turns=len(forward_metrics.turn_speeds),
        sharp_turns=forward_metrics.sharp_turns,
        average_speed_during_turns=mean_or_none(forward_metrics.turn_speeds),
        average_speed_during_straight_driving=mean_or_none(
            forward_metrics.straight_speeds
        ),
        speed_steering_correlation=speed_steering_correlation,
        speed_steering_correlation_caption=describe_speed_steering_correlation(
            speed_steering_correlation
        ),
        timeline=build_forward_timeline(forward_measurements),
        scatter=build_speed_steering_scatter(forward_measurements),
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
) -> ForwardDrivingMetrics:
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

    return ForwardDrivingMetrics(
        wheel_angles=wheel_angles,
        speeds=speeds,
        turn_speeds=turn_speeds,
        straight_speeds=straight_speeds,
        sharp_turns=sharp_turns,
    )
