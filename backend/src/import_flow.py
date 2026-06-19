"""
End-to-end import workflow for a field-test session.

The workflow keeps parsing, validation, quality analysis, and persistence in
one transaction boundary so partial imports can be rolled back.
"""

from datetime import date

from sqlalchemy.orm import Session

from ingestion import normalize_measurements, parse_csv, parse_metadata
from db.models import MeasurementModel, SessionModel
from quality import DataQualityAnalyzer
from validation.measurement_validator import MeasurementValidator
from validation.models import ValidationResult


def import_session(
    metadata_content: str | bytes,
    csv_content: str | bytes,
    database_session: Session,
) -> SessionModel:
    measurement_validator = MeasurementValidator()
    data_quality_analyzer = DataQualityAnalyzer()

    session_metadata = parse_metadata(metadata_content)

    # Import workflow: Parse -> Normalize -> Validate -> Quality -> Persist.
    measurements_dataframe = parse_csv(csv_content)
    normalized_measurements = normalize_measurements(measurements_dataframe)
    validation_results = [
        measurement_validator.validate_measurement(normalized_measurement)
        for normalized_measurement in normalized_measurements
    ]
    valid_rows = [
        validation_result
        for validation_result in validation_results
        if validation_result.is_valid
    ]
    outlier_row_indices = data_quality_analyzer.detect_outliers(valid_rows)

    try:
        session_model = SessionModel(
            session_id=str(session_metadata["session_id"]),
            vehicle_id=str(session_metadata["vehicle_id"]),
            driver_id=str(session_metadata["driver_id"]),
            recording_date=date.fromisoformat(str(session_metadata["recording_date"])),
            session_metadata=session_metadata,
        )
        database_session.add(session_model)
        database_session.flush()

        measurement_models = _create_measurement_models(
            session_model=session_model,
            validation_results=validation_results,
            outlier_row_indices=outlier_row_indices,
        )
        database_session.add_all(measurement_models)
        database_session.commit()
        database_session.refresh(session_model)
    except Exception:
        database_session.rollback()
        raise

    return session_model


def _create_measurement_models(
    session_model: SessionModel,
    validation_results: list[ValidationResult],
    outlier_row_indices: set[int],
) -> list[MeasurementModel]:
    measurement_models: list[MeasurementModel] = []
    for validation_result in validation_results:
        measurement = validation_result.measurement
        measurement_models.append(
            MeasurementModel(
                session_id=session_model.id,
                row_index=measurement.row_index,
                timestamp=measurement.timestamp,
                speed=measurement.speed,
                wheel_angle=measurement.wheel_angle,
                reverse_state=measurement.reverse_state,
                is_valid=validation_result.is_valid,
                validation_errors=[
                    validation_issue.model_dump()
                    for validation_issue in validation_result.issues
                ],
                is_outlier=measurement.row_index in outlier_row_indices,
            )
        )

    return measurement_models
