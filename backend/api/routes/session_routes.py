from datetime import datetime
from uuid import UUID

from fastapi import APIRouter, Depends
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session

from analytics import StatisticsCalculator
from db.database import create_database_session
from db.models import MeasurementModel, SessionModel
from quality import DataQualityReporter
from schemas.dashboard_schemas import DashboardResponse, MeasurementResponse, SessionResponse


session_router = APIRouter()


@session_router.get("/api/v1/sessions", response_model=list[SessionResponse])
def get_sessions_route(
    database_session: Session = Depends(create_database_session),
) -> list[SessionResponse]:
    sessions = database_session.query(SessionModel).all()

    return [_map_session_response(session_model) for session_model in sessions]


@session_router.get(
    "/api/v1/sessions/{id}/dashboard",
    response_model=DashboardResponse,
)
def get_dashboard_route(
    id: UUID,
    database_session: Session = Depends(create_database_session),
) -> DashboardResponse | JSONResponse:
    session_model = database_session.get(SessionModel, id)
    if session_model is None:
        return JSONResponse(
            status_code=404,
            content={
                "error": "not_found",
                "message": "Session not found",
            },
        )

    measurements = session_model.measurements

    return DashboardResponse(
        session=_map_session_response(session_model),
        analytics=StatisticsCalculator().calculate_statistics(measurements),
        quality_report=DataQualityReporter().generate_quality_report_from_measurements(
            measurements
        ),
        measurements=[
            _map_measurement_response(measurement)
            for measurement in measurements
        ],
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
        timestamp=_format_timestamp(measurement.timestamp),
        speed=measurement.speed,
        wheel_angle=measurement.wheel_angle,
        reverse_state=measurement.reverse_state,
        is_valid=measurement.is_valid,
        is_outlier=measurement.is_outlier,
        validation_errors=measurement.validation_errors,
        raw_timestamp=measurement.raw_timestamp,
        raw_speed=measurement.raw_speed,
        raw_wheel_angle=measurement.raw_wheel_angle,
        raw_reverse_state=measurement.raw_reverse_state,
    )


def _format_timestamp(timestamp: datetime | None) -> str | None:
    if timestamp is None:
        return None

    return timestamp.isoformat().replace("+00:00", "Z")
