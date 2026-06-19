from pydantic import BaseModel, ConfigDict, Field


class TimelinePointResponse(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    row_index: int = Field(alias="rowIndex")
    speed: float = Field(alias="speed")
    wheel_angle: float = Field(alias="wheelAngle")


class ScatterPointResponse(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    speed: float = Field(alias="speed")
    wheel_angle: float = Field(alias="wheelAngle")


class ForwardDrivingResponse(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    speed_mean: float | None = Field(alias="speedMean")
    wheel_angle_mean: float | None = Field(alias="wheelAngleMean")
    steering_variability: float | None = Field(alias="steeringVariability")
    speed_variability: float | None = Field(alias="speedVariability")
    total_turns: int = Field(alias="totalTurns")
    sharp_turns: int = Field(alias="sharpTurns")
    average_speed_during_turns: float | None = Field(alias="averageSpeedDuringTurns")
    average_speed_during_straight_driving: float | None = Field(
        alias="averageSpeedDuringStraightDriving",
    )
    speed_steering_correlation: float | None = Field(alias="speedSteeringCorrelation")
    speed_steering_correlation_caption: str = Field(alias="speedSteeringCorrelationCaption")
    timeline: list[TimelinePointResponse]
    scatter: list[ScatterPointResponse]


class ReverseDrivingResponse(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    measurement_count: int = Field(alias="measurementCount")
    percentage: float = Field(alias="percentage")
    average_speed: float | None = Field(alias="averageSpeed")
    steering_variability: float | None = Field(alias="steeringVariability")


class AnalyticsResponse(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    forward_driving: ForwardDrivingResponse = Field(alias="forwardDriving")
    reverse_driving: ReverseDrivingResponse = Field(alias="reverseDriving")
    driving_insights: list[str] = Field(alias="drivingInsights")
    steering_speed_insight: str = Field(alias="steeringSpeedInsight")
