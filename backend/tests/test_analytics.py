import pytest

from analytics import StatisticsCalculator
from quality import QualityAnalysisEntry


def create_measurement(
    row_index: int,
    speed: float,
    wheel_angle: float,
    reverse_state: bool,
    is_valid: bool = True,
) -> dict[str, object | None]:
    return {
        "row_index": row_index,
        "timestamp": "2025-01-01T12:00:00+00:00",
        "speed": speed,
        "wheel_angle": wheel_angle,
        "reverse_state": reverse_state,
        "raw_timestamp": "2025-01-01T12:00:00Z",
        "raw_speed": str(speed),
        "raw_wheel_angle": str(wheel_angle),
        "raw_reverse_state": "1" if reverse_state else "0",
        "is_valid": is_valid,
    }


def test_calculates_speed_statistics() -> None:
    statistics_calculator = StatisticsCalculator()
    measurements = [
        create_measurement(0, 10, -5, False),
        create_measurement(1, 20, 0, True),
        create_measurement(2, 30, 5, False),
    ]

    analytics_response = statistics_calculator.calculate_statistics(measurements)

    assert analytics_response.speed.min == 10
    assert analytics_response.speed.max == 30
    assert analytics_response.speed.mean == 20
    assert analytics_response.speed.median == 20


def test_calculates_wheel_angle_statistics() -> None:
    statistics_calculator = StatisticsCalculator()
    measurements = [
        create_measurement(0, 10, -10, False),
        create_measurement(1, 20, 0, True),
        create_measurement(2, 30, 10, False),
    ]

    analytics_response = statistics_calculator.calculate_statistics(measurements)

    assert analytics_response.wheel_angle.min == -10
    assert analytics_response.wheel_angle.max == 10
    assert analytics_response.wheel_angle.mean == 0
    assert analytics_response.wheel_angle.median == 0


def test_calculates_population_standard_deviation_and_percentiles() -> None:
    statistics_calculator = StatisticsCalculator()
    measurements = [
        create_measurement(0, 10, 0, False),
        create_measurement(1, 20, 0, True),
        create_measurement(2, 30, 0, False),
        create_measurement(3, 40, 0, True),
    ]

    analytics_response = statistics_calculator.calculate_statistics(measurements)

    assert analytics_response.speed.std_dev == pytest.approx(11.1803398875)
    assert analytics_response.speed.p5 == pytest.approx(11.5)
    assert analytics_response.speed.p95 == pytest.approx(38.5)


def test_calculates_reverse_state_counts() -> None:
    statistics_calculator = StatisticsCalculator()
    measurements = [
        create_measurement(0, 10, 0, False),
        create_measurement(1, 20, 0, True),
        create_measurement(2, 30, 0, True),
    ]

    analytics_response = statistics_calculator.calculate_statistics(measurements)

    assert analytics_response.reverse_state_summary.forward_count == 1
    assert analytics_response.reverse_state_summary.reverse_count == 2


def test_excludes_invalid_and_outlier_rows_by_default() -> None:
    statistics_calculator = StatisticsCalculator()
    measurements = [
        create_measurement(0, 10, 0, False),
        create_measurement(1, 20, 0, True),
        create_measurement(2, 100, 0, False),
        create_measurement(3, 200, 0, True, is_valid=False),
    ]
    quality_entries = [
        QualityAnalysisEntry(row_index=0, is_outlier=False),
        QualityAnalysisEntry(row_index=1, is_outlier=False),
        QualityAnalysisEntry(row_index=2, is_outlier=True),
        QualityAnalysisEntry(row_index=3, is_outlier=False),
    ]

    analytics_response = statistics_calculator.calculate_statistics(
        measurements,
        quality_entries=quality_entries,
    )

    assert analytics_response.analyzed_measurement_count == 2
    assert analytics_response.speed.max == 20

