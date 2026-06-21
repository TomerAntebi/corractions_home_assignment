import pandas as pd

from ingestion import MeasurementColumn

TURN_ANGLE_THRESHOLD_DEGREES = 20.0
SHARP_TURN_ANGLE_THRESHOLD_DEGREES = 25.0
SUDDEN_STEERING_STD_MULTIPLIER = 1.5

STEERING_BUCKET_BINS = [0, 5, 10, 15, 20, 25, float("inf")]
STEERING_BUCKET_LABELS = [
    "0-5",
    "5-10",
    "10-15",
    "15-20",
    "20-25",
    "25+",
]


def build_analytics_bundle(dataframe):
    forward_data = dataframe[dataframe[MeasurementColumn.REVERSE_STATE] == 0]
    reverse_data = dataframe[dataframe[MeasurementColumn.REVERSE_STATE] == 1]
    wheel_delta = dataframe[MeasurementColumn.WHEEL_ANGLE].diff().abs()
    speed_instability = dataframe[MeasurementColumn.SPEED].diff().abs()

    absolute_wheel_angles = forward_data[MeasurementColumn.WHEEL_ANGLE].abs()
    forward_events, forward_threshold = _context_sudden_steering(
        wheel_delta,
        dataframe,
        reverse_state=0,
    )
    reverse_events, reverse_threshold = _context_sudden_steering(
        wheel_delta,
        dataframe,
        reverse_state=1,
    )

    comparison_rows = []
    for driving_context, reverse_state in (("Forward", 0), ("Reverse", 1)):
        context_mask = dataframe[MeasurementColumn.REVERSE_STATE] == reverse_state
        comparison_rows.append(
            {
                "driving_context": driving_context,
                "wheel_delta_mean": wheel_delta.loc[context_mask].mean(),
                "speed_instability_mean": speed_instability.loc[context_mask].mean(),
            }
        )

    bucket_dataframe = dataframe.copy()
    bucket_dataframe["steering_bucket"] = pd.cut(
        bucket_dataframe[MeasurementColumn.WHEEL_ANGLE].abs(),
        bins=STEERING_BUCKET_BINS,
        labels=STEERING_BUCKET_LABELS,
    )
    steering_buckets = (
        bucket_dataframe
        .groupby("steering_bucket", observed=False)
        .agg(
            average_speed=(MeasurementColumn.SPEED, "mean"),
            count=(MeasurementColumn.SPEED, "count"),
        )
        .reset_index()
    )

    return {
        "forward_metrics": {
            "average_speed": forward_data[MeasurementColumn.SPEED].mean(),
            "speed_variability": forward_data[MeasurementColumn.SPEED].std(),
            "steering_variability": forward_data[MeasurementColumn.WHEEL_ANGLE].std(),
            "total_turns": int(
                (absolute_wheel_angles >= TURN_ANGLE_THRESHOLD_DEGREES).sum()
            ),
            "sharp_turns": int(
                (absolute_wheel_angles >= SHARP_TURN_ANGLE_THRESHOLD_DEGREES).sum()
            ),
            "speed_steering_correlation": forward_data[MeasurementColumn.SPEED].corr(
                forward_data[MeasurementColumn.WHEEL_ANGLE]
            ),
        },
        "reverse_metrics": {
            "reverse_percentage": (len(reverse_data) / len(dataframe)) * 100,
            "reverse_average_speed": reverse_data[MeasurementColumn.SPEED].mean(),
            "reverse_steering_variability": reverse_data[
                MeasurementColumn.WHEEL_ANGLE
            ].std(),
        },
        "behavior_metrics": {
            "steering_jerkiness": wheel_delta.mean(),
            "speed_instability": speed_instability.mean(),
            "sudden_steering_events": forward_events + reverse_events,
            "forward_sudden_steering_events": forward_events,
            "reverse_sudden_steering_events": reverse_events,
            "forward_sudden_steering_threshold": forward_threshold,
            "reverse_sudden_steering_threshold": reverse_threshold,
            "wheel_delta": wheel_delta,
        },
        "comparison": pd.DataFrame(comparison_rows),
        "steering_buckets": steering_buckets,
    }


def context_wheel_delta(wheel_delta, dataframe, reverse_state):
    same_context = dataframe[MeasurementColumn.REVERSE_STATE] == reverse_state
    valid_samples = same_context & same_context.shift(1, fill_value=False)
    return wheel_delta.loc[valid_samples]


def _context_sudden_steering(wheel_delta, dataframe, reverse_state):
    filtered_delta = context_wheel_delta(
        wheel_delta,
        dataframe,
        reverse_state,
    ).dropna()
    threshold = filtered_delta.mean() + (
        SUDDEN_STEERING_STD_MULTIPLIER * filtered_delta.std()
    )
    event_count = int((filtered_delta > threshold).sum())
    return event_count, threshold
