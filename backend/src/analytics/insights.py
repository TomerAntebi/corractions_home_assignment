"""Text interpretation for analytics results."""

from schemas.analytics_schemas import ForwardDrivingResponse, ReverseDrivingResponse

from analytics.steering_analysis import SteeringBucket, weighted_average_speed_for_buckets


CORRELATION_THRESHOLD = 0.3
LOW_STEERING_VARIABILITY_THRESHOLD = 10.0
HIGH_STEERING_VARIABILITY_THRESHOLD = 20.0
LOW_SPEED_VARIABILITY_THRESHOLD = 10.0
REVERSE_INSIGHT_THRESHOLD = 0.1
LOW_STEERING_BUCKETS = ("0-5°", "5-10°")
HIGH_STEERING_BUCKETS = ("20-25°", "25°+")
STEERING_SPEED_CHANGE_THRESHOLD = 0.05


def build_driving_insights(
    forward_driving: ForwardDrivingResponse,
    reverse_driving: ReverseDrivingResponse,
) -> list[str]:
    driving_insights: list[str] = []

    if forward_driving.steering_variability is not None:
        if forward_driving.steering_variability < LOW_STEERING_VARIABILITY_THRESHOLD:
            driving_insights.append(
                "Forward steering behavior remained relatively stable throughout the session."
            )
        elif forward_driving.steering_variability >= HIGH_STEERING_VARIABILITY_THRESHOLD:
            driving_insights.append(
                "Forward steering behavior showed frequent steering corrections."
            )

    if (
        forward_driving.speed_variability is not None
        and forward_driving.speed_variability < LOW_SPEED_VARIABILITY_THRESHOLD
    ):
        driving_insights.append(
            "Forward vehicle speed remained relatively stable during the session."
        )

    if forward_driving.sharp_turns > 0:
        driving_insights.append(
            f"{forward_driving.sharp_turns:,} sharp turn measurements were detected during forward driving."
        )

    if forward_driving.speed_steering_correlation is None:
        driving_insights.append(
            "There is not enough forward-driving data to measure speed and steering relationship."
        )
    elif (
        -CORRELATION_THRESHOLD
        <= forward_driving.speed_steering_correlation
        <= CORRELATION_THRESHOLD
    ):
        driving_insights.append(
            "No meaningful relationship was detected between steering intensity and vehicle speed during forward driving."
        )

    if reverse_driving.percentage > REVERSE_INSIGHT_THRESHOLD:
        reverse_percentage_text = f"{reverse_driving.percentage * 100:.0f}%"
        driving_insights.append(
            f"Reverse driving represented {reverse_percentage_text} of analyzed measurements."
        )

    if (
        reverse_driving.steering_variability is not None
        and reverse_driving.steering_variability >= HIGH_STEERING_VARIABILITY_THRESHOLD
    ):
        driving_insights.append(
            "Steering corrections were elevated during reverse driving."
        )

    if not driving_insights:
        driving_insights.append(
            "No strong driving behavior patterns stood out from the measured values."
        )

    return driving_insights


def describe_speed_steering_correlation(correlation: float | None) -> str:
    if correlation is None:
        return "There is not enough data to compare speed and steering intensity."
    if correlation < -CORRELATION_THRESHOLD:
        return "Driver generally reduced speed while turning."
    if correlation <= CORRELATION_THRESHOLD:
        return "No clear relationship between speed and steering intensity."

    return "Higher steering angles tended to occur at higher speeds."


def describe_average_speed_by_steering_insight(
    buckets: list[SteeringBucket],
) -> str:
    populated_bucket_count = sum(
        1 for bucket in buckets if bucket.measurement_count > 0
    )
    if populated_bucket_count < 2:
        return "Not enough data across steering ranges to summarize speed behavior."

    low_average_speed = weighted_average_speed_for_buckets(
        buckets,
        LOW_STEERING_BUCKETS,
    )
    high_average_speed = weighted_average_speed_for_buckets(
        buckets,
        HIGH_STEERING_BUCKETS,
    )

    if low_average_speed is None or high_average_speed is None or low_average_speed == 0:
        return "Not enough data across steering ranges to summarize speed behavior."

    speed_difference_percentage = abs(high_average_speed - low_average_speed) / low_average_speed

    if speed_difference_percentage < STEERING_SPEED_CHANGE_THRESHOLD:
        return "Average speed remained relatively stable across steering ranges."

    if high_average_speed < low_average_speed:
        return (
            "Average speed decreased as steering intensity increased, suggesting the driver "
            "slowed down during stronger steering maneuvers."
        )

    return "Average speed increased as steering intensity increased."
