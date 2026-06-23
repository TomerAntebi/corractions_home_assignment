"""Driving analytics — computes forward/reverse metrics, steering buckets, and behavior stats."""

import pandas as pd

from ingestion import MeasurementColumn

STEERING_BUCKET_BINS = [0, 5, 10, 20, float("inf")]
STEERING_BUCKET_LABELS = ["Straight", "Light Turn", "Moderate Turn", "Sharp Turn"]


def find_reverse_segments(dataframe, sample_rate_hz):
    """Return continuous reverse-driving periods in elapsed-session seconds."""
    if dataframe.empty:
        return []

    segments = []
    in_segment = False
    start_second = None
    end_second = None
    sample_interval = 1.0 / sample_rate_hz
    reverse_states = dataframe[MeasurementColumn.REVERSE_STATE]
    elapsed_seconds = dataframe[MeasurementColumn.ELAPSED_SECONDS]

    for reverse_state, elapsed_second in zip(reverse_states, elapsed_seconds):
        if reverse_state == 1:
            if not in_segment:
                start_second = elapsed_second
                in_segment = True
            end_second = elapsed_second
        elif in_segment:
            segments.append(_build_reverse_segment(start_second, end_second, sample_interval))
            in_segment = False

    if in_segment:
        segments.append(_build_reverse_segment(start_second, end_second, sample_interval))

    return segments


def _build_reverse_segment(start_second, end_second, sample_interval):
    return {
        "start_second": start_second,
        "end_second": end_second,
        "duration_seconds": end_second - start_second + sample_interval,
    }


def speed_stability_score(speed_instability):
    if speed_instability is None or pd.isna(speed_instability):
        return float("nan")

    return max(0.0, min(100.0, 100 * (1 - speed_instability / 15.0)))


def _context_steering_analysis(gear_data):
    """Calculate steering alerts only within a continuous forward/reverse gear segment."""
    gear_wheel_delta = gear_data.loc[
        gear_data["same_gear_as_previous"],
        "wheel_delta",
    ]
    valid_deltas = gear_wheel_delta.dropna()
    threshold = float("nan") if valid_deltas.empty else valid_deltas.quantile(0.95)
    event_count = 0 if pd.isna(threshold) else int((gear_wheel_delta > threshold).sum())

    return {
        "steering_threshold": threshold,
        "sudden_steering_events": event_count,
        "wheel_delta_mean": gear_wheel_delta.mean(),
    }


def _build_context_metrics(gear_data, steering_analysis):
    """Build the metrics shown in the mirrored Forward and Reverse KPI cards."""
    gear_speed_instability = gear_data.loc[
        gear_data["same_gear_as_previous"],
        "speed_instability",
    ].mean()

    return {
        "measurement_count": len(gear_data),
        "average_speed": gear_data[MeasurementColumn.SPEED].mean(),
        "speed_variability": gear_data[MeasurementColumn.SPEED].std(),
        "steering_variability": gear_data[MeasurementColumn.WHEEL_ANGLE].std(),
        "steering_jerkiness": steering_analysis["wheel_delta_mean"],
        "steering_threshold": steering_analysis["steering_threshold"],
        "sudden_steering_events": steering_analysis["sudden_steering_events"],
        "speed_instability": gear_speed_instability,
    }


def _build_steering_buckets(gear_data):
    """Group steering intensity to show whether sharper turns change average speed."""
    bucket_dataframe = gear_data.copy()
    bucket_dataframe["steering_bucket"] = pd.cut(
        bucket_dataframe[MeasurementColumn.WHEEL_ANGLE].abs(),
        bins=STEERING_BUCKET_BINS,
        labels=STEERING_BUCKET_LABELS,
    )
    return (
        bucket_dataframe
        .groupby("steering_bucket", observed=False)
        .agg(
            average_speed=(MeasurementColumn.SPEED, "mean"), count=(MeasurementColumn.SPEED, "count"),
        )
        .reset_index()
    )


def _forward_window_metrics(dataframe, window_mask):
    window_data = dataframe.loc[window_mask]
    return {
        "average_speed": window_data[MeasurementColumn.SPEED].mean(),
        "speed_variability": window_data[MeasurementColumn.SPEED].std(),
        "steering_jerkiness": window_data.loc[
            window_data["same_gear_as_previous"],
            "wheel_delta",
        ].mean(),
    }


def _build_forward_impact_metrics(dataframe, reverse_segments):
    """Compare forward driving before and after the first reverse maneuver."""
    if not reverse_segments:
        return None

    reverse_segment = reverse_segments[0]
    sample_interval = reverse_segment["duration_seconds"] - (
        reverse_segment["end_second"] - reverse_segment["start_second"]
    )
    after_reverse_start = reverse_segment["end_second"] + sample_interval
    forward_mask = dataframe[MeasurementColumn.REVERSE_STATE] == 0

    before_mask = forward_mask & (
        dataframe[MeasurementColumn.ELAPSED_SECONDS] < reverse_segment["start_second"]
    )
    after_mask = forward_mask & (
        dataframe[MeasurementColumn.ELAPSED_SECONDS] >= after_reverse_start
    )

    return {
        "before_label": (
            "Before Reverse\n"
            f"(0-{int(reverse_segment['start_second'] - sample_interval)}s)"
        ),
        "after_label": f"After Reverse\n({int(after_reverse_start)}s+)",
        "before_reverse": _forward_window_metrics(dataframe, before_mask),
        "after_reverse": _forward_window_metrics(dataframe, after_mask),
    }


def build_analytics_bundle(dataframe, sample_rate_hz=1):
    """Consume prepared features and return the analytics payload used by the dashboard."""
    forward_data = dataframe[dataframe[MeasurementColumn.REVERSE_STATE] == 0]
    reverse_data = dataframe[dataframe[MeasurementColumn.REVERSE_STATE] == 1]
    reverse_segments = find_reverse_segments(dataframe, sample_rate_hz)
    wheel_delta = dataframe["wheel_delta"]
    same_gear_as_previous = dataframe["same_gear_as_previous"]

    forward_steering = _context_steering_analysis(forward_data)
    reverse_steering = _context_steering_analysis(reverse_data)
    forward_metrics = _build_context_metrics(forward_data, forward_steering)
    reverse_metrics = _build_context_metrics(reverse_data, reverse_steering)
    forward_impact_metrics = _build_forward_impact_metrics(dataframe, reverse_segments)
    steering_alert_mask = pd.Series(False, index=dataframe.index)

    # Alerts are context-specific: forward and reverse use their own 95th-percentile limits.
    for reverse_state, steering_analysis in ((0, forward_steering), (1, reverse_steering)):
        threshold = steering_analysis["steering_threshold"]
        if pd.isna(threshold):
            continue

        gear_mask = dataframe[MeasurementColumn.REVERSE_STATE] == reverse_state
        steering_alert_mask |= gear_mask & same_gear_as_previous & (wheel_delta > threshold)

    return {
        "forward_metrics": forward_metrics,
        "reverse_metrics": reverse_metrics,
        "forward_impact_metrics": forward_impact_metrics,
        "forward_steering_buckets": _build_steering_buckets(forward_data),
        "reverse_steering_buckets": _build_steering_buckets(reverse_data),
        "reverse_segments": reverse_segments,
        "steering_alert_mask": steering_alert_mask,
        "wheel_delta": wheel_delta.where(same_gear_as_previous),
    }
