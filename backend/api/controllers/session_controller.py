from uuid import UUID

from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session

from core.error_responses import _session_not_found_response
from mappers.response_mapper import (
    _build_analytics_response,
    _build_data_quality_report_response,
    _map_measurement_response,
    _map_session_response,
    _map_session_summary,
)
from db.models import SessionModel
from schemas.dashboard_schemas import DashboardResponse
from schemas.session_schemas import SessionSummaryResponse


def get_sessions(
    database_session: Session,
) -> list[SessionSummaryResponse]:
    sessions = database_session.query(SessionModel).all()

    return [_map_session_summary(session_model) for session_model in sessions]


def get_dashboard(
    id: UUID,
    database_session: Session,
) -> DashboardResponse | JSONResponse:
    session_model = _get_session_or_none(database_session, id)
    if session_model is None:
        return _session_not_found_response()

    return DashboardResponse(
        session=_map_session_response(session_model),
        analytics=_build_analytics_response(session_model.measurements),
        quality_report=_build_data_quality_report_response(session_model.measurements),
        measurements=[
            _map_measurement_response(measurement)
            for measurement in session_model.measurements
        ],
    )


def _get_session_or_none(database_session: Session, session_id: UUID) -> SessionModel | None:
    return database_session.get(SessionModel, session_id)
