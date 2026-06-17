from quality import DataQualityAnalyzer, DataQualityReporter
from validation.measurement_validator import MeasurementValidator


def create_measurement(
    row_index: int,
    speed: float | None = 10,
    wheel_angle: float | None = 0,
    raw_speed: object | None = "10",
    raw_wheel_angle: object | None = "0",
    timestamp: str | None = "2025-01-01T12:00:00+00:00",
    raw_timestamp: object | None = "2025-01-01T12:00:00Z",
    reverse_state: bool = False,
) -> dict[str, object | None]:
    return {
        "row_index": row_index,
        "timestamp": timestamp,
        "speed": speed,
        "wheel_angle": wheel_angle,
        "reverse_state": reverse_state,
        "raw_timestamp": raw_timestamp,
        "raw_speed": raw_speed,
        "raw_wheel_angle": raw_wheel_angle,
        "raw_reverse_state": "1" if reverse_state else "0",
    }


def test_required_validation_reports_missing_speed() -> None:
    measurement_validator = MeasurementValidator()

    validation_result = measurement_validator.validate_measurement(
        create_measurement(row_index=0, speed=None, raw_speed="")
    )

    assert validation_result.is_valid is False
    assert any(
        validation_issue.field == "speed" and validation_issue.rule == "required"
        for validation_issue in validation_result.issues
    )


def test_range_validation_reports_out_of_range_speed() -> None:
    measurement_validator = MeasurementValidator()

    validation_result = measurement_validator.validate_measurement(
        create_measurement(row_index=0, speed=450, raw_speed="450")
    )

    assert validation_result.is_valid is False
    assert any(
        validation_issue.field == "speed" and validation_issue.rule == "range"
        for validation_issue in validation_result.issues
    )


def test_error_timeout_validation_reports_invalid_marker() -> None:
    measurement_validator = MeasurementValidator()

    validation_result = measurement_validator.validate_measurement(
        create_measurement(row_index=0, speed=None, raw_speed="ERROR_TIMEOUT")
    )

    assert validation_result.is_valid is False
    assert any(
        validation_issue.field == "speed"
        and validation_issue.rule == "invalid_marker"
        and validation_issue.raw_value == "ERROR_TIMEOUT"
        for validation_issue in validation_result.issues
    )


def test_iqr_outlier_detection_flags_large_speed() -> None:
    measurement_validator = MeasurementValidator()
    data_quality_analyzer = DataQualityAnalyzer()
    normalized_measurements = [
        create_measurement(row_index=0, speed=10, raw_speed="10"),
        create_measurement(row_index=1, speed=11, raw_speed="11"),
        create_measurement(row_index=2, speed=12, raw_speed="12"),
        create_measurement(row_index=3, speed=13, raw_speed="13"),
        create_measurement(row_index=4, speed=14, raw_speed="14"),
        create_measurement(row_index=5, speed=100, raw_speed="100"),
    ]

    validation_results = measurement_validator.validate_all_measurements(normalized_measurements)
    quality_entries = data_quality_analyzer.analyze_quality(validation_results)

    assert quality_entries[5].is_outlier is True


def test_iqr_outlier_detection_groups_by_reverse_state() -> None:
    measurement_validator = MeasurementValidator()
    data_quality_analyzer = DataQualityAnalyzer()
    normalized_measurements = [
        create_measurement(row_index=0, speed=50, raw_speed="50"),
        create_measurement(row_index=1, speed=55, raw_speed="55"),
        create_measurement(row_index=2, speed=60, raw_speed="60"),
        create_measurement(row_index=3, speed=65, raw_speed="65"),
        create_measurement(row_index=4, speed=70, raw_speed="70"),
        create_measurement(row_index=5, speed=10, raw_speed="10", reverse_state=True),
        create_measurement(row_index=6, speed=11, raw_speed="11", reverse_state=True),
        create_measurement(row_index=7, speed=12, raw_speed="12", reverse_state=True),
        create_measurement(row_index=8, speed=12, raw_speed="12", reverse_state=True),
        create_measurement(row_index=9, speed=13, raw_speed="13", reverse_state=True),
        create_measurement(row_index=10, speed=125, raw_speed="125", reverse_state=True),
    ]

    validation_results = measurement_validator.validate_all_measurements(normalized_measurements)
    quality_entries = data_quality_analyzer.analyze_quality(validation_results)

    assert quality_entries[5].is_outlier is False
    assert quality_entries[6].is_outlier is False
    assert quality_entries[7].is_outlier is False
    assert quality_entries[8].is_outlier is False
    assert quality_entries[9].is_outlier is False
    assert quality_entries[10].is_outlier is True


def test_quality_score_calculation() -> None:
    measurement_validator = MeasurementValidator()
    data_quality_analyzer = DataQualityAnalyzer()
    data_quality_reporter = DataQualityReporter()
    normalized_measurements = [
        create_measurement(row_index=0, speed=10, raw_speed="10"),
        create_measurement(row_index=1, speed=11, raw_speed="11"),
        create_measurement(row_index=2, speed=12, raw_speed="12"),
        create_measurement(row_index=3, speed=13, raw_speed="13"),
        create_measurement(row_index=4, speed=14, raw_speed="14"),
        create_measurement(row_index=5, speed=100, raw_speed="100"),
        create_measurement(row_index=6, speed=None, raw_speed=""),
    ]

    validation_results = measurement_validator.validate_all_measurements(normalized_measurements)
    quality_entries = data_quality_analyzer.analyze_quality(validation_results)
    data_quality_report = data_quality_reporter.generate_quality_report(
        total_rows=len(normalized_measurements),
        validation_results=validation_results,
        quality_entries=quality_entries,
    )

    assert data_quality_report.valid_rows == 6
    assert data_quality_report.invalid_rows == 1
    assert data_quality_report.outlier_rows == 1
    assert data_quality_report.quality_score == max(0, 6 / 7 - (1 / 7 * 0.3))
