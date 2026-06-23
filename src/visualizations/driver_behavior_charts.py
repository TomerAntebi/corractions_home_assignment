"""Driver behavior charts — control profile, reverse impact, and attention mapping."""

import matplotlib.pyplot as plt
import numpy as np

import visualizations.chart_theme as theme
import visualizations.plot_helpers as plot_helpers
from analytics.analytics import speed_stability_score
from ingestion import MeasurementColumn


def plot_control_profile(forward_metrics, reverse_metrics):
    fig, axes = plt.subplots(2, 1, figsize=theme.CONTROL_PROFILE_FIGURE_SIZE, sharex=True)
    categories = ["Forward", "Reverse"]
    x_positions = np.arange(len(categories))
    stability_values = [
        speed_stability_score(forward_metrics["speed_instability"]),
        speed_stability_score(reverse_metrics["speed_instability"]),
    ]
    jerkiness_values = [
        forward_metrics["steering_jerkiness"],
        reverse_metrics["steering_jerkiness"],
    ]

    plot_helpers.plot_control_metric_bars(
        axes[0],
        x_positions,
        stability_values,
        title="Speed Stability Score",
        ylabel="Score (%)",
        color=theme.BEHAVIOR_STABILITY_COLOR,
        label_color=theme.BEHAVIOR_STABILITY_LABEL_COLOR,
        value_format="{:.1f}%",
        y_limit=(0, 105),
    )
    plot_helpers.plot_control_metric_bars(
        axes[1],
        x_positions,
        jerkiness_values,
        title="Mean Steering Jerkiness",
        ylabel="Degrees (°)",
        color=theme.BEHAVIOR_JERKINESS_COLOR,
        label_color=theme.BEHAVIOR_JERKINESS_LABEL_COLOR,
        value_format="{:.1f}°",
    )

    axes[1].set_xticks(x_positions)
    axes[1].set_xticklabels(categories, fontsize=10, fontweight="bold")
    axes[1].set_xlabel("Driving direction")
    plot_helpers.set_figure_title(fig, "Control Profile: Forward vs Reverse Driving")
    fig.subplots_adjust(top=0.88, bottom=0.1, hspace=0.38)
    return fig


def plot_forward_reverse_impact(forward_impact_metrics):
    fig, axes = plt.subplots(1, 3, figsize=(12, 4.2))
    categories = [
        forward_impact_metrics["before_label"],
        forward_impact_metrics["after_label"],
    ]
    x_positions = np.arange(len(categories))
    before = forward_impact_metrics["before_reverse"]
    after = forward_impact_metrics["after_reverse"]
    metric_specs = [
        ("Average Speed", "Speed", [before["average_speed"], after["average_speed"]], "{:.1f}"),
        (
            "Speed Variability",
            "Std dev",
            [before["speed_variability"], after["speed_variability"]],
            "{:.1f}",
        ),
        (
            "Steering Change",
            "Mean change (°)",
            [before["steering_jerkiness"], after["steering_jerkiness"]],
            "{:.2f}°",
        ),
    ]

    for ax, spec in zip(axes, metric_specs):
        plot_helpers.plot_forward_impact_metric(ax, x_positions, categories, *spec)

    plot_helpers.set_figure_title(fig, "Forward Driving Impact: Before vs After Reverse")
    fig.text(
        0.02, 0.01,
        "Lower speed variability and steering change indicate smoother control.",
        fontsize=9, color=theme.LABEL_COLOR,
    )
    fig.subplots_adjust(top=0.78, bottom=0.22, wspace=0.28)
    return fig


def plot_attention_mapping(
    dataframe,
    wheel_delta,
    alert_mask,
    reverse_segments,
    forward_metrics,
    reverse_metrics,
):
    fig, ax = plt.subplots(figsize=theme.ATTENTION_MAPPING_FIGURE_SIZE)

    elapsed_seconds = dataframe[MeasurementColumn.ELAPSED_SECONDS]
    valid_mask = wheel_delta.notna()
    plot_wheel_delta = wheel_delta.loc[valid_mask]
    plot_elapsed_seconds = elapsed_seconds.loc[valid_mask]
    plot_alert_mask = alert_mask.loc[valid_mask]
    alert_count = int(plot_alert_mask.sum())
    session_max_second = elapsed_seconds.max()
    forward_threshold = forward_metrics["steering_threshold"]
    reverse_threshold = reverse_metrics["steering_threshold"]

    plot_helpers.shade_reverse_segments_by_elapsed(ax, reverse_segments)
    ax.plot(
        plot_elapsed_seconds, plot_wheel_delta,
        color=theme.STEERING_LINE_COLOR, linewidth=2.0, zorder=4,
    )
    plot_helpers.set_focused_ylim(ax, plot_wheel_delta, padding_ratio=0.18)
    plot_helpers.draw_context_threshold_lines(
        ax,
        reverse_segments,
        forward_threshold,
        reverse_threshold,
        session_max_second,
    )

    if plot_alert_mask.any():
        ax.scatter(
            plot_elapsed_seconds.loc[plot_alert_mask],
            plot_wheel_delta.loc[plot_alert_mask],
            color=theme.HIGHLIGHT_COLOR, s=90,
            edgecolors="black", linewidths=1.0, zorder=7,
        )

    legend_handles = [
        plot_helpers.legend_line("Steering change per second", theme.STEERING_LINE_COLOR),
        plot_helpers.legend_patch("Reverse driving period", theme.REVERSE_SECTION_COLOR),
        plot_helpers.legend_line(
            "Forward threshold "
            f"({forward_threshold:.1f}°)",
            theme.FORWARD_STATE_COLOR,
            linestyle="--",
            alpha=0.85,
        ),
        plot_helpers.legend_line(
            "Reverse threshold "
            f"({reverse_threshold:.1f}°)",
            theme.REVERSE_SECTION_COLOR,
            linestyle="--",
            alpha=0.85,
        ),
    ]
    if alert_count:
        legend_handles.append(
            plot_helpers.legend_marker(
                f"Threshold exceeded ({alert_count})",
                marker="o", color="w",
                markerfacecolor=theme.HIGHLIGHT_COLOR,
                markeredgecolor="black", markeredgewidth=1.0, markersize=9,
            )
        )

    ax.legend(
        handles=legend_handles, loc="upper center",
        bbox_to_anchor=(0.5, -0.14), ncol=3, frameon=False, fontsize=9,
    )

    ax.set_title(
        "Attention Mapping: Steering Spikes Over Session",
        fontsize=12, fontweight="bold", pad=12, loc="left", color=theme.LABEL_COLOR,
    )
    ax.set_xlabel("Elapsed seconds")
    ax.set_ylabel("Steering change (°)")
    ax.set_xlim(-1, session_max_second + 1)
    theme.style_axis(ax)

    fig.subplots_adjust(left=0.08, right=0.97, top=0.92, bottom=0.18)
    return fig
