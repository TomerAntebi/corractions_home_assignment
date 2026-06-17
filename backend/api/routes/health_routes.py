from datetime import UTC, datetime

from fastapi import APIRouter

from schemas.common_schemas import HealthResponse


health_router = APIRouter()


@health_router.get("/api/v1/health", response_model=HealthResponse)
def get_health() -> HealthResponse:
    return HealthResponse(
        status="ok",
        timestamp=datetime.now(UTC).isoformat().replace("+00:00", "Z"),
    )
