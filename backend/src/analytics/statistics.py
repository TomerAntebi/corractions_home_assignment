"""Basic statistics for validated field-test measurements."""

import numpy as np

from db.models import MeasurementModel
from schemas.analytics_schemas import TimelinePointResponse


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


def _sorted_chart_ready_forward_measurements(
    forward_measurements: list[MeasurementModel],
) -> list[MeasurementModel]:
    return sorted(
        [
            measurement
            for measurement in forward_measurements
            if measurement.speed is not None and measurement.wheel_angle is not None
        ],
        key=lambda measurement: measurement.row_index,
    )


def build_forward_timeline(
    forward_measurements: list[MeasurementModel],
) -> list[TimelinePointResponse]:
    return [
        TimelinePointResponse(
            row_index=measurement.row_index,
            speed=measurement.speed,
            wheel_angle=measurement.wheel_angle,
        )
        for measurement in _sorted_chart_ready_forward_measurements(forward_measurements)
    ]
