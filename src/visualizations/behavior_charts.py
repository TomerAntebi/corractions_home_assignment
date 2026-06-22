"""Behavior charts — control profile and attention mapping for the Driver Behavior tab."""

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from matplotlib.lines import Line2D
from matplotlib.patches import Patch

import visualizations.chart_helpers as chart_helpers
import visualizations.theme as theme
from ingestion import MeasurementColumn


def _context_metric_values(behavior_metrics, metric_name):
    return [
        behavior_metrics[f"forward_{metric_name}"],
        behavior_metrics[f"reverse_{metric_name}"],
    ]


def _set_figure_title(fig, title):
    fig.suptitle(
        title, fontsize=13, fontweight="bold", x=0.02, ha="left", color=theme.LABEL_COLOR
    )


def plot_control_profile(behavior_metrics):
    fig, axes = plt.subplots(2, 1, figsize=theme.CONTROL_PROFILE_FIGURE_SIZE, sharex=True)
    categories = ["Forward", "Reverse"]
    x_positions = np.arange(len(categories))
    stability_values = _context_metric_values(behavior_metrics, "speed_stability_score")
    jerkiness_values = _context_metric_values(behavior_metrics, "steering_jerkiness")

    _plot_control_metric_bars(
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
    _plot_control_metric_bars(
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
    _set_figure_title(fig, "Control Profile: Forward vs Reverse Driving")
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
        _plot_forward_impact_metric(ax, x_positions, categories, *spec)

    _set_figure_title(fig, "Forward Driving Impact: Before vs After Reverse")
    fig.text(
        0.02, 0.01,
        "Lower speed variability and steering change indicate smoother control.",
        fontsize=9, color=theme.LABEL_COLOR,
    )
    fig.subplots_adjust(top=0.78, bottom=0.22, wspace=0.28)
    return fig


def _plot_forward_impact_metric(ax, x_positions, categories, title, ylabel, values, value_format):
    bars = ax.bar(
        x_positions, values, width=0.48,
        color=[theme.FORWARD_STATE_COLOR, theme.REVERSE_SECTION_COLOR],
        edgecolor="white", linewidth=1.0,
    )
    _label_bars(ax, bars, values, value_format)
    ax.set(
        title=title, ylabel=ylabel, xticks=x_positions, ylim=(0, max(values) * 1.22)
    )
    ax.title.set_fontsize(11)
    ax.title.set_fontweight("bold")
    ax.set_xticklabels(categories, fontsize=8, fontweight="bold")
    theme.style_axis(ax)


def _plot_control_metric_bars(
    ax,
    x_positions,
    values,
    *,
    title,
    ylabel,
    color,
    label_color,
    value_format,
    y_limit=None,
):
    bars = ax.bar(
        x_positions, values, width=0.45,
        color=color, edgecolor="white", linewidth=1.0,
    )
    ax.set_title(title, loc="left", fontsize=11, fontweight="bold")
    ax.set_ylabel(ylabel)

    if y_limit is None:
        max_value = max(
            (value for value in values if pd.notna(value)),
            default=5.0,
        )
        ax.set_ylim(0, max(max_value * 1.35, 5.0))
    else:
        ax.set_ylim(*y_limit)

    for bar, value in zip(bars, values):
        _label_bar(ax, bar, value, value_format, label_color)

    theme.style_axis(ax)


def _label_bars(ax, bars, values, value_format, color=theme.LABEL_COLOR):
    for bar, value in zip(bars, values):
        _label_bar(ax, bar, value, value_format, color)


def _label_bar(ax, bar, value, value_format, color):
    if pd.isna(value):
        return

    ax.text(
        bar.get_x() + bar.get_width() / 2,
        bar.get_height(),
        value_format.format(value),
        ha="center", va="bottom",
        fontsize=9, fontweight="bold", color=color,
    )


def _legend_line(label, color, **style):
    return Line2D(
        [0], [0], color=color, linewidth=2.0, label=label, **style,
    )


def _legend_patch(label, color, alpha=0.14):
    return Patch(facecolor=color, alpha=alpha, edgecolor="none", label=label)


def plot_attention_mapping(dataframe, behavior_metrics, reverse_segments):
    fig, ax = plt.subplots(figsize=theme.ATTENTION_MAPPING_FIGURE_SIZE)

    wheel_delta = behavior_metrics["wheel_delta"]
    alert_mask = behavior_metrics["steering_alert_mask"]
    elapsed_seconds = dataframe[MeasurementColumn.ELAPSED_SECONDS]
    valid_mask = wheel_delta.notna()
    plot_wheel_delta = wheel_delta.loc[valid_mask]
    plot_elapsed_seconds = elapsed_seconds.loc[valid_mask]
    plot_alert_mask = alert_mask.loc[valid_mask]
    alert_count = int(plot_alert_mask.sum())
    session_max_second = elapsed_seconds.max()

    chart_helpers.shade_reverse_segments_by_elapsed(ax, reverse_segments)
    ax.plot(
        plot_elapsed_seconds, plot_wheel_delta,
        color=theme.STEERING_LINE_COLOR, linewidth=2.0, zorder=4,
    )
    chart_helpers.set_focused_ylim(ax, plot_wheel_delta, padding_ratio=0.18)
    chart_helpers.draw_context_threshold_lines(
        ax,
        reverse_segments,
        behavior_metrics["forward_steering_threshold"],
        behavior_metrics["reverse_steering_threshold"],
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
        _legend_line("Steering change per second", theme.STEERING_LINE_COLOR),
        _legend_patch("Reverse driving period", theme.REVERSE_SECTION_COLOR),
        _legend_line(
            "Forward threshold "
            f"({behavior_metrics['forward_steering_threshold']:.1f}°)",
            theme.FORWARD_STATE_COLOR,
            linestyle="--",
            alpha=0.85,
        ),
        _legend_line(
            "Reverse threshold "
            f"({behavior_metrics['reverse_steering_threshold']:.1f}°)",
            theme.REVERSE_SECTION_COLOR,
            linestyle="--",
            alpha=0.85,
        ),
    ]
    if alert_count:
        legend_handles.append(
            Line2D(
                [0], [0], marker="o", color="w",
                markerfacecolor=theme.HIGHLIGHT_COLOR,
                markeredgecolor="black", markeredgewidth=1.0, markersize=9,
                label=f"Threshold exceeded ({alert_count})",
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
