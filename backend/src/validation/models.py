from dataclasses import dataclass
from datetime import datetime

from pydantic import BaseModel


SENSOR_ERROR_MARKER = "ERROR_TIMEOUT"
ABSENT_VALUE_MARKERS = frozenset({"", "null", "NaN"})

REQUIRED_ANALYTICS_FIELDS = ("timestamp", "speed", "wheel_angle")
FIELDS_CHECKED_FOR_SENSOR_ERROR = (
    "timestamp",
    "speed",
    "wheel_angle",
    "reverse_state",
)
PARSED_NUMERIC_FIELDS = ("speed", "wheel_angle")

RULE_INVALID_MARKER = "invalid_marker"
RULE_NUMERIC = "numeric"
RULE_REQUIRED = "required"
RULE_RANGE = "range"


@dataclass(frozen=True)
class NumericRangeRule:
    field_name: str
    minimum: float
    maximum: float


NUMERIC_RANGE_RULES = (
    NumericRangeRule("speed", minimum=0, maximum=200),
    NumericRangeRule("wheel_angle", minimum=-45, maximum=45),
)


class NormalizedMeasurement(BaseModel):
    row_index: int
    timestamp: datetime | None
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
