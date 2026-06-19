"""Basic statistics for validated field-test measurements."""

import numpy as np

from db.models import MeasurementModel
from schemas.analytics_schemas import ScatterPointResponse, TimelinePointResponse


def mean_or_none(numeric_samples: list[float]) -> float | None:
    if not numeric_samples:
        return None

    return float(np.mean(numeric_samples))


def std_or_none(numeric_samples: list[float]) -> float | None:
    if not numeric_samples:
        return None

    return float(np.std(numeric_samples))


def calculate_speed_mean(
    analyzed_measurements: list[MeasurementModel],
) -> float | None:
    return mean_or_none(
        [
            measurement.speed
            for measurement in analyzed_measurements
            if measurement.speed is not None
        ]
    )


def calculate_wheel_angle_mean(
    analyzed_measurements: list[MeasurementModel],
) -> float | None:
    return mean_or_none(
        [
            measurement.wheel_angle
            for measurement in analyzed_measurements
            if measurement.wheel_angle is not None
        ]
    )


def _chart_ready_forward_measurements(
    forward_measurements: list[MeasurementModel],
) -> list[MeasurementModel]:
    return [
        measurement
        for measurement in forward_measurements
        if measurement.speed is not None and measurement.wheel_angle is not None
    ]


def build_forward_timeline(
    forward_measurements: list[MeasurementModel],
) -> list[TimelinePointResponse]:
    return [
        TimelinePointResponse(
            row_index=measurement.row_index,
            speed=measurement.speed,
            wheel_angle=measurement.wheel_angle,
        )
        for measurement in sorted(
            _chart_ready_forward_measurements(forward_measurements),
            key=lambda item: item.row_index,
        )
        if measurement.speed is not None and measurement.wheel_angle is not None
    ]


def build_speed_steering_scatter(
    forward_measurements: list[MeasurementModel],
) -> list[ScatterPointResponse]:
    return [
        ScatterPointResponse(
            speed=measurement.speed,
            wheel_angle=measurement.wheel_angle,
        )
        for measurement in sorted(
            _chart_ready_forward_measurements(forward_measurements),
            key=lambda item: item.row_index,
        )
        if measurement.speed is not None and measurement.wheel_angle is not None
    ]
