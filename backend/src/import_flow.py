"""
End-to-end import workflow for a field-test session.

Parse, normalize, validate (rules and IQR outliers), then persist. Persistence runs
inside a database transaction so a failed import leaves no partial session data.
"""

from uuid import UUID

from sqlalchemy.orm import Session

from ingestion import normalize_measurements, parse_csv, parse_metadata
from db.models import MeasurementModel, SessionModel
from validation.measurement_validator import validate_measurement
from validation.outlier_detection import detect_outliers
from validation.models import MeasurementRow


def import_session(
    metadata_content: str | bytes,
    csv_content: str | bytes,
    database_session: Session,
) -> SessionModel:
    session_metadata = parse_metadata(metadata_content)
    validated_measurements = validate_measurements(csv_content)
    session_model = persist_session_with_measurements(
        database_session=database_session,
        session_metadata=session_metadata,
        validated_measurements=validated_measurements,
    )
    return session_model


def validate_measurements(csv_content: str | bytes) -> list[MeasurementRow]:
    measurements_dataframe = parse_csv(csv_content)
    normalized_measurements = normalize_measurements(measurements_dataframe)

    measurements_rows: list[MeasurementRow] = []
    for normalized_measurement in normalized_measurements:
        measurements_rows.append(validate_measurement(normalized_measurement))

    return detect_outliers(measurements_rows)


def persist_session_with_measurements(
    database_session: Session,
    session_metadata: dict[str, object],
    validated_measurements: list[MeasurementRow],
) -> SessionModel:
    with database_session.begin():
        session_model = SessionModel(session_metadata=session_metadata)
        database_session.add(session_model)
        database_session.flush()
        measurement_models = create_measurement_models(
            session_id=session_model.id,
            validated_measurements=validated_measurements,
        )
        database_session.add_all(measurement_models)
        database_session.flush()

    database_session.refresh(session_model)
    return session_model


def create_measurement_models(
    session_id: UUID,
    validated_measurements: list[MeasurementRow],
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
                is_outlier=validated_measurement.is_outlier,
            )
        )

    return measurement_models
