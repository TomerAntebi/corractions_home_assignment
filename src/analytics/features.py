"""Analytics features — reusable columns consumed by analytics calculations."""

import pandas as pd

from ingestion import MeasurementColumn


def build_analytics_dataframe(dataframe: pd.DataFrame) -> pd.DataFrame:
    """Add reusable per-row features; metrics and thresholds are computed later."""
    analytics_dataframe = dataframe.copy()
    analytics_dataframe["wheel_delta"] = (
        analytics_dataframe[MeasurementColumn.WHEEL_ANGLE].diff().abs()
    )
    analytics_dataframe["speed_instability"] = (
        analytics_dataframe[MeasurementColumn.SPEED].diff().abs()
    )
    analytics_dataframe["same_gear_as_previous"] = (
        analytics_dataframe[MeasurementColumn.REVERSE_STATE]
        == analytics_dataframe[MeasurementColumn.REVERSE_STATE].shift(1)
    )

    return analytics_dataframe
