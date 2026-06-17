from pydantic import BaseModel


class NormalizedMeasurement(BaseModel):
    row_index: int
    timestamp: str | None
    speed: float | None
    wheel_angle: float | None
    reverse_state: bool | None
    raw_timestamp: object | None
    raw_speed: object | None
    raw_wheel_angle: object | None
    raw_reverse_state: object | None


class ValidationIssue(BaseModel):
    field: str
    rule: str
    message: str
    raw_value: str | None = None


class ValidationResult(BaseModel):
    measurement: NormalizedMeasurement
    issues: list[ValidationIssue]
    is_valid: bool
