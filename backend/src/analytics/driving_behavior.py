"""Driver behavior metrics for validated field-test measurements."""

import pandas as pd

from db.models import MeasurementModel
from schemas.analytics_schemas import (
    ForwardDrivingResponse,
    ReverseDrivingResponse,
    SteeringBucketAnalysisResponse,
    SteeringIntensityBucketResponse,
)

from analytics.insights import describe_steering_bucket_trend
from analytics.statistics import build_forward_timeline, mean_or_none, std_or_none


TURN_ANGLE_THRESHOLD_DEGREES = 20.0
SHARP_TURN_ANGLE_THRESHOLD_DEGREES = 25.0

STEERING_INTENSITY_BUCKET_DEFINITIONS = (
    ("0-5°", 0, 5),
    ("5-10°", 5, 10),
    ("10-15°", 10, 15),
    ("15-20°", 15, 20),
    ("20-25°", 20, 25),
    ("25°+", 25, None),
)

STEERING_INTENSITY_BUCKET_COUNT = len(STEERING_INTENSITY_BUCKET_DEFINITIONS)


def _steering_intensity_bucket_index(absolute_wheel_angle: float) -> int:
    if absolute_wheel_angle < 5:
        return 0
    if absolute_wheel_angle < 10:
        return 1
    if absolute_wheel_angle < 15:
        return 2
    if absolute_wheel_angle < 20:
        return 3
    if absolute_wheel_angle < 25:
        return 4
    return 5


def _compute_speed_steering_correlation(
    correlation_speeds: list[float],
    correlation_absolute_angles: list[float],
) -> float | None:
    if not correlation_speeds:
        return None

    speed_series = pd.Series(correlation_speeds)
    angle_series = pd.Series(correlation_absolute_angles)
    speed_steering_correlation = speed_series.corr(angle_series)
    if pd.isna(speed_steering_correlation):
        return None

    return float(speed_steering_correlation)


def _build_steering_bucket_analysis(
    bucket_total_speeds: list[float],
    bucket_measurement_counts: list[int],
) -> SteeringBucketAnalysisResponse:
    buckets: list[SteeringIntensityBucketResponse] = []

    for bucket_index, (label, _, _) in enumerate(STEERING_INTENSITY_BUCKET_DEFINITIONS):
        measurement_count = bucket_measurement_counts[bucket_index]
        average_speed = (
            bucket_total_speeds[bucket_index] / measurement_count
            if measurement_count > 0
            else None
        )
        buckets.append(
            SteeringIntensityBucketResponse(
                label=label,
                average_speed=average_speed,
                measurement_count=measurement_count,
            )
        )

    return SteeringBucketAnalysisResponse(
        buckets=buckets,
        insight=describe_steering_bucket_trend(buckets),
    )


def calculate_forward_driving(
    forward_measurements: list[MeasurementModel],
) -> ForwardDrivingResponse:
    (
        wheel_angles,
        speeds,
        turn_speeds,
        straight_speeds,
        sharp_turns,
        bucket_total_speeds,
        bucket_measurement_counts,
        correlation_speeds,
        correlation_absolute_angles,
    ) = _collect_forward_driving_metrics(forward_measurements)
    speed_steering_correlation = _compute_speed_steering_correlation(
        correlation_speeds,
        correlation_absolute_angles,
    )
    steering_bucket_analysis = _build_steering_bucket_analysis(
        bucket_total_speeds,
        bucket_measurement_counts,
    )

    # speed_mean uses every forward row with a parsed speed (speeds). timeline includes
    # only rows where both speed and wheel_angle are present, so chart series and
    # speed_mean can reflect slightly different populations when wheel_angle is missing.
    return ForwardDrivingResponse(
        speed_mean=mean_or_none(speeds),
        steering_variability=std_or_none(wheel_angles),
        speed_variability=std_or_none(speeds),
        total_turns=len(turn_speeds),
        sharp_turns=sharp_turns,
        average_speed_during_turns=mean_or_none(turn_speeds),
        average_speed_during_straight_driving=mean_or_none(straight_speeds),
        speed_steering_correlation=speed_steering_correlation,
        steering_bucket_analysis=steering_bucket_analysis,
        timeline=build_forward_timeline(forward_measurements),
    )


def calculate_reverse_driving(
    analyzed_measurement_count: int,
    reverse_measurements: list[MeasurementModel],
) -> ReverseDrivingResponse:
    reverse_percentage = (
        len(reverse_measurements) / analyzed_measurement_count
        if analyzed_measurement_count > 0
        else 0.0
    )
    reverse_wheel_angles: list[float] = []
    reverse_speeds: list[float] = []

    for measurement in reverse_measurements:
        if measurement.wheel_angle is not None:
            reverse_wheel_angles.append(measurement.wheel_angle)
        if measurement.speed is not None:
            reverse_speeds.append(measurement.speed)

    return ReverseDrivingResponse(
        measurement_count=len(reverse_measurements),
        percentage=reverse_percentage,
        average_speed=mean_or_none(reverse_speeds),
        steering_variability=std_or_none(reverse_wheel_angles),
    )


def _collect_forward_driving_metrics(
    forward_measurements: list[MeasurementModel],
) -> tuple[
    list[float],
    list[float],
    list[float],
    list[float],
    int,
    list[float],
    list[int],
    list[float],
    list[float],
]:
    wheel_angles: list[float] = []
    speeds: list[float] = []
    turn_speeds: list[float] = []
    straight_speeds: list[float] = []
    sharp_turns = 0
    bucket_total_speeds = [0.0] * STEERING_INTENSITY_BUCKET_COUNT
    bucket_measurement_counts = [0] * STEERING_INTENSITY_BUCKET_COUNT
    correlation_speeds: list[float] = []
    correlation_absolute_angles: list[float] = []

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

        bucket_index = _steering_intensity_bucket_index(absolute_wheel_angle)
        bucket_total_speeds[bucket_index] += measurement.speed
        bucket_measurement_counts[bucket_index] += 1
        correlation_speeds.append(measurement.speed)
        correlation_absolute_angles.append(absolute_wheel_angle)

    return (
        wheel_angles,
        speeds,
        turn_speeds,
        straight_speeds,
        sharp_turns,
        bucket_total_speeds,
        bucket_measurement_counts,
        correlation_speeds,
        correlation_absolute_angles,
    )
