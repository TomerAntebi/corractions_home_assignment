from analytics import StatisticsCalculator
from db.models import MeasurementModel, SessionModel
from quality import DataQualityReporter, QualityAnalysisEntry
from schemas.analytics_schemas import AnalyticsResponse
from schemas.dashboard_schemas import DataQualityReportResponse, MeasurementResponse
from schemas.session_schemas import SessionResponse, SessionSummaryResponse
from validation.models import NormalizedMeasurement, ValidationIssue, ValidationResult


def _map_session_summary(session_model: SessionModel) -> SessionSummaryResponse:
    data_quality_report = _build_data_quality_report_response(session_model.measurements)

    return SessionSummaryResponse(
        id=str(session_model.id),
        session_id=session_model.session_id,
        vehicle_id=session_model.vehicle_id,
        driver_id=session_model.driver_id,
        recording_date=session_model.recording_date.isoformat(),
        metadata=session_model.session_metadata,
        quality_score=data_quality_report.quality_score,
    )


def _map_session_response(session_model: SessionModel) -> SessionResponse:
    return SessionResponse(
        id=str(session_model.id),
        session_id=session_model.session_id,
        vehicle_id=session_model.vehicle_id,
        driver_id=session_model.driver_id,
        recording_date=session_model.recording_date.isoformat(),
        metadata=session_model.session_metadata,
    )


def _map_measurement_response(measurement: MeasurementModel) -> MeasurementResponse:
    return MeasurementResponse(
        row_index=measurement.row_index,
        timestamp=measurement.timestamp.isoformat().replace("+00:00", "Z")
        if measurement.timestamp is not None
        else None,
        speed=measurement.speed,
        wheel_angle=measurement.wheel_angle,
        reverse_state=measurement.reverse_state,
        is_valid=measurement.is_valid,
        is_outlier=measurement.is_outlier,
    )


def _build_analytics_response(measurements: list[MeasurementModel]) -> AnalyticsResponse:
    return StatisticsCalculator().calculate_statistics(
        _build_validation_results(measurements),
        quality_entries=_build_quality_entries(measurements),
    )


def _build_data_quality_report_response(measurements: list[MeasurementModel]) -> DataQualityReportResponse:
    validation_results = _build_validation_results(measurements)
    data_quality_report = DataQualityReporter().generate_quality_report(
        total_rows=len(measurements),
        validation_results=validation_results,
        quality_entries=_build_quality_entries(measurements),
    )

    return DataQualityReportResponse.model_validate(data_quality_report.model_dump())


def _build_validation_results(measurements: list[MeasurementModel]) -> list[ValidationResult]:
    return [
        ValidationResult(
            measurement=NormalizedMeasurement(
                row_index=measurement.row_index,
                timestamp=_format_timestamp(measurement),
                speed=measurement.speed,
                wheel_angle=measurement.wheel_angle,
                reverse_state=measurement.reverse_state,
                raw_timestamp=measurement.raw_timestamp,
                raw_speed=measurement.raw_speed,
                raw_wheel_angle=measurement.raw_wheel_angle,
                raw_reverse_state=measurement.raw_reverse_state,
            ),
            issues=[
                ValidationIssue.model_validate(validation_error)
                for validation_error in measurement.validation_errors
            ],
            is_valid=measurement.is_valid,
        )
        for measurement in measurements
    ]


def _build_quality_entries(measurements: list[MeasurementModel]) -> list[QualityAnalysisEntry]:
    return [
        QualityAnalysisEntry(
            row_index=measurement.row_index,
            is_outlier=measurement.is_outlier,
        )
        for measurement in measurements
    ]


def _format_timestamp(measurement: MeasurementModel) -> str | None:
    if measurement.timestamp is None:
        return None

    return measurement.timestamp.isoformat().replace("+00:00", "Z")

