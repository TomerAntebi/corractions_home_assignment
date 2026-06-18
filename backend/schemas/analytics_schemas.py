from pydantic import BaseModel, ConfigDict, Field


class DrivingBehaviorResponse(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

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
    reverse_percentage: float = Field(alias="reversePercentage")
    average_reverse_speed: float | None = Field(alias="averageReverseSpeed")


class AnalyticsResponse(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    speed_mean: float | None = Field(alias="speedMean")
    wheel_angle_mean: float | None = Field(alias="wheelAngleMean")
    driving_behavior: DrivingBehaviorResponse = Field(alias="drivingBehavior")
    driving_insights: list[str] = Field(alias="drivingInsights")
