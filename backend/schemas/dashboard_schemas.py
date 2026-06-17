from pydantic import BaseModel, ConfigDict, Field

from schemas.analytics_schemas import AnalyticsResponse
from schemas.session_schemas import SessionResponse


class DataQualityReportResponse(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    total_rows: int = Field(alias="totalRows")
    valid_rows: int = Field(alias="validRows")
    invalid_rows: int = Field(alias="invalidRows")
    outlier_rows: int = Field(alias="outlierRows")
    quality_score: float = Field(alias="qualityScore")
    missing_by_field: dict[str, int] = Field(alias="missingByField")
    invalid_by_rule: dict[str, int] = Field(alias="invalidByRule")
    sensor_errors: list[str] = Field(alias="sensorErrors")


class MeasurementResponse(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    row_index: int = Field(alias="rowIndex")
    timestamp: str | None
    speed: float | None
    wheel_angle: float | None = Field(alias="wheelAngle")
    reverse_state: bool | None = Field(alias="reverseState")
    is_valid: bool = Field(alias="isValid")
    is_outlier: bool = Field(alias="isOutlier")


class DashboardResponse(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    session: SessionResponse
    analytics: AnalyticsResponse
    quality_report: DataQualityReportResponse = Field(alias="qualityReport")
    measurements: list[MeasurementResponse]
