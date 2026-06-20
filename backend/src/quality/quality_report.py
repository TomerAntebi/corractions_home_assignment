"""Quality report generation from persisted measurements."""

from db.models import MeasurementModel
from quality.models import DataQualityReport
from validation.models import RULE_INVALID_MARKER, RULE_REQUIRED


class DataQualityReporter:
    def generate_quality_report_from_measurements(
        self,
        measurements: list[MeasurementModel],
    ) -> DataQualityReport:
        total_rows = len(measurements)
        valid_rows = 0
        outlier_rows = 0
        missing_by_field: dict[str, int] = {}
        invalid_by_rule: dict[str, int] = {}
        sensor_errors: list[str] = []

        for measurement in measurements:
            if measurement.is_valid:
                valid_rows += 1
            if measurement.is_outlier:
                outlier_rows += 1

            for validation_error in measurement.validation_errors:
                rule = str(validation_error["rule"])
                invalid_by_rule[rule] = invalid_by_rule.get(rule, 0) + 1

                if rule == RULE_REQUIRED:
                    field = str(validation_error["field"])
                    missing_by_field[field] = missing_by_field.get(field, 0) + 1

                raw_value = validation_error.get("raw_value")
                if (
                    rule == RULE_INVALID_MARKER
                    and raw_value is not None
                    and str(raw_value) not in sensor_errors
                ):
                    sensor_errors.append(str(raw_value))

        return DataQualityReport(
            total_rows=total_rows,
            valid_rows=valid_rows,
            invalid_rows=total_rows - valid_rows,
            outlier_rows=outlier_rows,
            missing_by_field=missing_by_field,
            invalid_by_rule=invalid_by_rule,
            sensor_errors=sensor_errors,
        )
