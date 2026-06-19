from pydantic import BaseModel, ConfigDict, Field

from quality import DataQualityReport
from schemas.analytics_schemas import AnalyticsResponse


class SessionResponse(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    id: str
    metadata: dict[str, object]


class MeasurementResponse(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    row_index: int = Field(alias="rowIndex")
    timestamp: str | None
    speed: float | None
    wheel_angle: float | None = Field(alias="wheelAngle")
    reverse_state: bool | None = Field(alias="reverseState")
    is_valid: bool = Field(alias="isValid")
    is_outlier: bool = Field(alias="isOutlier")
    validation_errors: list[dict[str, object]] = Field(alias="validationErrors")


class DashboardResponse(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    session: SessionResponse
    analytics: AnalyticsResponse
    quality_report: DataQualityReport = Field(alias="qualityReport")
