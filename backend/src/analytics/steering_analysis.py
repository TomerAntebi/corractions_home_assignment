"""Steering-speed relationship analytics."""

from dataclasses import dataclass

import pandas as pd

from db.models import MeasurementModel


STEERING_BUCKET_BINS = [0, 5, 10, 15, 20, 25, float("inf")]
STEERING_BUCKET_LABELS = ["0-5°", "5-10°", "10-15°", "15-20°", "20-25°", "25°+"]


@dataclass
class SteeringBucket:
    steering_bucket: str
    avg_speed: float | None
    measurement_count: int


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


def weighted_average_speed_for_buckets(
    buckets: list[SteeringBucket],
    bucket_labels: tuple[str, ...],
) -> float | None:
    populated_buckets = [
        bucket
        for bucket in buckets
        if bucket.steering_bucket in bucket_labels and bucket.measurement_count > 0
    ]
    if not populated_buckets:
        return None

    total_measurement_count = sum(
        bucket.measurement_count for bucket in populated_buckets
    )
    if total_measurement_count == 0:
        return None

    weighted_speed_sum = sum(
        bucket.avg_speed * bucket.measurement_count
        for bucket in populated_buckets
        if bucket.avg_speed is not None
    )

    return float(weighted_speed_sum / total_measurement_count)


def calculate_steering_speed_insight(
    forward_measurements: list[MeasurementModel],
) -> str:
    from analytics.insights import describe_average_speed_by_steering_insight

    forward_measurement_records = [
        {
            "speed": measurement.speed,
            "wheel_angle": measurement.wheel_angle,
        }
        for measurement in forward_measurements
        if measurement.speed is not None and measurement.wheel_angle is not None
    ]
    if not forward_measurement_records:
        return describe_average_speed_by_steering_insight([])

    forward_dataframe = pd.DataFrame(forward_measurement_records)
    bucket_dataframe = forward_dataframe[["speed", "wheel_angle"]].copy()
    bucket_dataframe["absolute_wheel_angle"] = bucket_dataframe["wheel_angle"].abs()
    bucket_dataframe["steering_bucket"] = pd.cut(
        bucket_dataframe["absolute_wheel_angle"],
        bins=STEERING_BUCKET_BINS,
        labels=STEERING_BUCKET_LABELS,
        right=False,
    )

    grouped_buckets = bucket_dataframe.groupby("steering_bucket", observed=False).agg(
        avg_speed=("speed", "mean"),
        measurement_count=("speed", "count"),
    )

    buckets = [
        SteeringBucket(
            steering_bucket=bucket_label,
            avg_speed=(
                float(grouped_buckets.loc[bucket_label, "avg_speed"])
                if bucket_label in grouped_buckets.index
                and pd.notna(grouped_buckets.loc[bucket_label, "avg_speed"])
                else None
            ),
            measurement_count=(
                int(grouped_buckets.loc[bucket_label, "measurement_count"])
                if bucket_label in grouped_buckets.index
                else 0
            ),
        )
        for bucket_label in STEERING_BUCKET_LABELS
    ]

    return describe_average_speed_by_steering_insight(buckets)
