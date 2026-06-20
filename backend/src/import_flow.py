"""
End-to-end import workflow for a field-test session.

Parse, normalize, validate, and quality analysis run first. Persistence runs
inside a database transaction so a failed import leaves no partial session data.
"""

from uuid import UUID

from sqlalchemy.orm import Session

from ingestion import normalize_measurements, parse_csv, parse_metadata
from db.models import MeasurementModel, SessionModel
from quality import DataQualityAnalyzer
from validation.measurement_validator import MeasurementValidator
from validation.models import MeasurementRow


def import_session(
    metadata_content: str | bytes,
    csv_content: str | bytes,
    database_session: Session,
) -> SessionModel:
    session_metadata = parse_metadata(metadata_content)
    validated_measurements = _validate_measurements(csv_content)
    outlier_row_indices = _detect_outlier_indices(validated_measurements)
    session_model = _persist_session(
        database_session=database_session,
        session_metadata=session_metadata,
        validated_measurements=validated_measurements,
        outlier_row_indices=outlier_row_indices,
    )
    return session_model


def _validate_measurements(csv_content: str | bytes) -> list[MeasurementRow]:
    measurement_validator = MeasurementValidator()

    measurements_dataframe = parse_csv(csv_content)
    normalized_measurements = normalize_measurements(measurements_dataframe)

    validated_measurements: list[MeasurementRow] = []
    for normalized_measurement in normalized_measurements:
        validated_measurement = measurement_validator.validate_measurement(normalized_measurement)
        validated_measurements.append(validated_measurement)

    return validated_measurements


def _detect_outlier_indices(validated_measurements: list[MeasurementRow]) -> set[int]:
    data_quality_analyzer = DataQualityAnalyzer()
    valid_rows = [
        validated_measurement
        for validated_measurement in validated_measurements
        if validated_measurement.is_valid
    ]
    return data_quality_analyzer.detect_outliers(valid_rows)


def _persist_session(
    database_session: Session,
    session_metadata: dict[str, object],
    validated_measurements: list[MeasurementRow],
    outlier_row_indices: set[int],
) -> SessionModel:
    with database_session.begin():
        session_model = SessionModel(session_metadata=session_metadata)
        database_session.add(session_model)
        database_session.flush()
        measurement_models = _create_measurement_models(
            session_id=session_model.id,
            validated_measurements=validated_measurements,
            outlier_row_indices=outlier_row_indices,
        )
        database_session.add_all(measurement_models)
        database_session.flush()

    database_session.refresh(session_model)
    return session_model


def _create_measurement_models(
    session_id: UUID,
    validated_measurements: list[MeasurementRow],
    outlier_row_indices: set[int],
) -> list[MeasurementModel]:
    measurement_models: list[MeasurementModel] = []
    for validated_measurement in validated_measurements:
        # Persist normalized values and validation metadata only; raw CSV fields
        # on MeasurementRow are used during validation and are not stored.
        measurement_models.append(
            MeasurementModel(
                session_id=session_id,
                row_index=validated_measurement.row_index,
                timestamp=validated_measurement.timestamp,
                speed=validated_measurement.speed,
                wheel_angle=validated_measurement.wheel_angle,
                reverse_state=validated_measurement.reverse_state,
                is_valid=validated_measurement.is_valid,
                validation_errors=[
                    validation_error.model_dump()
                    for validation_error in validated_measurement.validation_errors
                ],
                is_outlier=(
                    validated_measurement.is_valid
                    and validated_measurement.row_index in outlier_row_indices
                ),
            )
        )

    return measurement_models
