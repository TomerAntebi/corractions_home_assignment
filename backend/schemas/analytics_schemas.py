from pydantic import BaseModel, ConfigDict, Field


class NumericStatisticsResponse(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    min: float | None
    max: float | None
    mean: float | None
    median: float | None
    std_dev: float | None = Field(alias="stdDev")
    p5: float | None
    p95: float | None


class ReverseStateSummaryResponse(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    forward_count: int = Field(alias="forwardCount")
    reverse_count: int = Field(alias="reverseCount")


class AnalyticsResponse(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    analyzed_measurement_count: int = Field(alias="analyzedMeasurementCount")
    speed: NumericStatisticsResponse
    wheel_angle: NumericStatisticsResponse = Field(alias="wheelAngle")
    reverse_state_summary: ReverseStateSummaryResponse = Field(alias="reverseStateSummary")
