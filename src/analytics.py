"""Driving analytics — computes forward/reverse metrics, steering buckets, and behavior stats."""

import pandas as pd

from ingestion import MeasurementColumn

STEERING_BUCKET_BINS = [0, 5, 10, 20, float("inf")]
STEERING_BUCKET_LABELS = ["Straight", "Light Turn", "Moderate Turn", "Sharp Turn"]


def find_reverse_segments(dataframe, sample_rate_hz):
    if dataframe.empty:
        return []

    segments = []
    in_segment = False
    start_second = None
    end_second = None
    sample_interval = 1.0 / sample_rate_hz

    for _, row in dataframe.iterrows():
        if row[MeasurementColumn.REVERSE_STATE] == 1:
            elapsed_second = row[MeasurementColumn.ELAPSED_SECONDS]
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


def _same_gear_as_previous(dataframe):
    return dataframe[MeasurementColumn.REVERSE_STATE] == dataframe[MeasurementColumn.REVERSE_STATE].shift(1)


def _context_series(series, dataframe, reverse_state, same_context):
    context_mask = dataframe[MeasurementColumn.REVERSE_STATE] == reverse_state
    valid_samples = context_mask & same_context
    return series.loc[valid_samples]


def _context_steering_analysis(wheel_delta, dataframe, reverse_state, same_context):
    context_wheel_delta = _context_series(wheel_delta, dataframe, reverse_state, same_context)
    valid_deltas = context_wheel_delta.dropna()
    threshold = float("nan") if valid_deltas.empty else valid_deltas.quantile(0.95)
    event_count = 0 if pd.isna(threshold) else int((context_wheel_delta > threshold).sum())

    return {
        "steering_threshold": threshold,
        "sudden_steering_events": event_count,
        "wheel_delta_mean": context_wheel_delta.mean(),
    }


def _build_steering_alert_mask(
    wheel_delta,
    dataframe,
    same_context,
    forward_threshold,
    reverse_threshold,
):
    alert_mask = pd.Series(False, index=dataframe.index)

    for reverse_state, threshold in ((0, forward_threshold), (1, reverse_threshold)):
        if pd.isna(threshold):
            continue

        context_mask = dataframe[MeasurementColumn.REVERSE_STATE] == reverse_state
        alert_mask |= context_mask & same_context & (wheel_delta > threshold)

    return alert_mask


def _build_context_metrics(
    dataframe,
    speed_instability,
    reverse_state,
    same_context,
    steering_analysis,
):
    context_data = dataframe[dataframe[MeasurementColumn.REVERSE_STATE] == reverse_state]
    context_speed_instability = _context_series(
        speed_instability, dataframe, reverse_state, same_context,
    ).mean()

    return {
        "measurement_count": len(context_data),
        "average_speed": context_data[MeasurementColumn.SPEED].mean(),
        "speed_variability": context_data[MeasurementColumn.SPEED].std(),
        "steering_variability": context_data[MeasurementColumn.WHEEL_ANGLE].std(),
        "steering_jerkiness": steering_analysis["wheel_delta_mean"],
        "steering_threshold": steering_analysis["steering_threshold"],
        "sudden_steering_events": steering_analysis["sudden_steering_events"],
        "speed_instability": context_speed_instability,
    }


def _build_steering_buckets(context_data):
    bucket_dataframe = context_data.copy()
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


def _forward_window_metrics(dataframe, wheel_delta, same_context, window_mask):
    window_data = dataframe.loc[window_mask]
    return {
        "average_speed": window_data[MeasurementColumn.SPEED].mean(),
        "speed_variability": window_data[MeasurementColumn.SPEED].std(),
        "steering_jerkiness": wheel_delta.loc[window_mask & same_context].mean(),
    }


def _build_forward_impact_metrics(dataframe, wheel_delta, same_context, reverse_segments):
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
        "before_reverse": _forward_window_metrics(dataframe, wheel_delta, same_context, before_mask),
        "after_reverse": _forward_window_metrics(dataframe, wheel_delta, same_context, after_mask),
    }


def build_analytics_bundle(dataframe, sample_rate_hz=1):
    forward_data = dataframe[dataframe[MeasurementColumn.REVERSE_STATE] == 0]
    reverse_data = dataframe[dataframe[MeasurementColumn.REVERSE_STATE] == 1]
    reverse_segments = find_reverse_segments(dataframe, sample_rate_hz)

    wheel_delta = dataframe[MeasurementColumn.WHEEL_ANGLE].diff().abs()
    speed_instability = dataframe[MeasurementColumn.SPEED].diff().abs()
    same_context = _same_gear_as_previous(dataframe)

    forward_steering = _context_steering_analysis(wheel_delta, dataframe, 0, same_context)
    reverse_steering = _context_steering_analysis(wheel_delta, dataframe, 1, same_context)
    forward_metrics = _build_context_metrics(
        dataframe, speed_instability, 0, same_context, forward_steering,
    )
    reverse_metrics = _build_context_metrics(
        dataframe, speed_instability, 1, same_context, reverse_steering,
    )
    forward_impact_metrics = _build_forward_impact_metrics(
        dataframe, wheel_delta, same_context, reverse_segments,
    )

    return {
        "forward_metrics": forward_metrics,
        "reverse_metrics": reverse_metrics,
        "forward_impact_metrics": forward_impact_metrics,
        "forward_steering_buckets": _build_steering_buckets(forward_data),
        "reverse_steering_buckets": _build_steering_buckets(reverse_data),
        "reverse_segments": reverse_segments,
        "steering_alert_mask": _build_steering_alert_mask(
            wheel_delta, dataframe, same_context,
            forward_steering["steering_threshold"],
            reverse_steering["steering_threshold"],
        ),
        "wheel_delta": wheel_delta.where(same_context),
    }
