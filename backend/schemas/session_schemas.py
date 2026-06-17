from pydantic import BaseModel, ConfigDict, Field


class SessionSummaryResponse(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    id: str
    session_id: str = Field(alias="sessionId")
    vehicle_id: str = Field(alias="vehicleId")
    driver_id: str = Field(alias="driverId")
    recording_date: str = Field(alias="recordingDate")
    metadata: dict[str, object]
    quality_score: float = Field(alias="qualityScore")


class SessionResponse(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    id: str
    session_id: str = Field(alias="sessionId")
    vehicle_id: str = Field(alias="vehicleId")
    driver_id: str = Field(alias="driverId")
    recording_date: str = Field(alias="recordingDate")
    metadata: dict[str, object]
