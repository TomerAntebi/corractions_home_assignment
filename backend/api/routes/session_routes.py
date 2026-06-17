from uuid import UUID

from fastapi import APIRouter, Depends
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session

from api.controllers.session_controller import (
    get_dashboard,
    get_sessions,
)
from db.database import create_database_session
from schemas.common_schemas import ErrorResponse
from schemas.dashboard_schemas import DashboardResponse
from schemas.session_schemas import SessionSummaryResponse


session_router = APIRouter()


@session_router.get("/api/v1/sessions", response_model=list[SessionSummaryResponse])
def get_sessions_route(
    database_session: Session = Depends(create_database_session),
) -> list[SessionSummaryResponse]:
    return get_sessions(database_session=database_session)


@session_router.get(
    "/api/v1/sessions/{id}/dashboard",
    response_model=DashboardResponse,
    responses={404: {"model": ErrorResponse}},
)
def get_dashboard_route(
    id: UUID,
    database_session: Session = Depends(create_database_session),
) -> DashboardResponse | JSONResponse:
    return get_dashboard(id=id, database_session=database_session)
