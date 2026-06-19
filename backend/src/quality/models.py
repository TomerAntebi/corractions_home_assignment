from pydantic import BaseModel, ConfigDict, Field


IQR_MINIMUM_SAMPLE_SIZE = 5
IQR_MULTIPLIER = 1.5


class QualityAnalysisEntry(BaseModel):
    row_index: int
    is_outlier: bool


class DataQualityReport(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    total_rows: int = Field(alias="totalRows")
    valid_rows: int = Field(alias="validRows")
    invalid_rows: int = Field(alias="invalidRows")
    outlier_rows: int = Field(alias="outlierRows")
    missing_by_field: dict[str, int] = Field(alias="missingByField")
    invalid_by_rule: dict[str, int] = Field(alias="invalidByRule")
    sensor_errors: list[str] = Field(alias="sensorErrors")
