"""Text interpretation for analytics results."""

from analytics.constants import (
    CORRELATION_THRESHOLD,
    HIGH_STEERING_VARIABILITY_THRESHOLD,
    LOW_SPEED_VARIABILITY_THRESHOLD,
    LOW_STEERING_VARIABILITY_THRESHOLD,
    REVERSE_INSIGHT_THRESHOLD,
)
from schemas.analytics_schemas import (
    ForwardDrivingResponse,
    ReverseDrivingResponse,
    SteeringIntensityBucketResponse,
)


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
    else:
        driving_insights.append(
            describe_speed_steering_correlation(forward_driving.speed_steering_correlation)
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


def describe_steering_bucket_trend(
    buckets: list[SteeringIntensityBucketResponse],
) -> str:
    populated_buckets = [
        bucket
        for bucket in buckets
        if bucket.measurement_count > 0 and bucket.average_speed is not None
    ]
    if len(populated_buckets) < 2:
        return "Not enough steering intensity buckets to describe a speed trend."

    lowest_intensity_average = populated_buckets[0].average_speed
    highest_intensity_average = populated_buckets[-1].average_speed
    if lowest_intensity_average is None or highest_intensity_average is None:
        return "Not enough steering intensity buckets to describe a speed trend."

    if highest_intensity_average < lowest_intensity_average:
        return "Average speed decreased as steering intensity increased."
    if highest_intensity_average > lowest_intensity_average:
        return "Average speed increased as steering intensity increased."

    return "Average speed remained relatively stable across steering intensity ranges."
