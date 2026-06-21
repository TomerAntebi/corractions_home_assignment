"""Behavior charts — steering correction timeline with sudden-correction thresholds."""

import matplotlib.pyplot as plt
import pandas as pd

from analytics import context_wheel_delta
from visualizations.chart_helpers import (
    add_mean_hline,
    add_steering_correction_legend,
    add_threshold_hline,
    build_timeline_x_values,
    set_focused_ylim,
)
from visualizations.theme import (
    TIMELINE_FIGURE_SIZE,
    context_color,
    finalize_chart,
    style_axis,
)


def plot_steering_correction_timeline(
    dataframe,
    behavior_metrics,
    reverse_state,
    *,
    sample_rate_hz=1,
):
    threshold_key = (
        "forward_sudden_steering_threshold"
        if reverse_state == 0
        else "reverse_sudden_steering_threshold"
    )
    threshold = behavior_metrics[threshold_key]
    wheel_delta = behavior_metrics["wheel_delta"]
    valid_context_delta = context_wheel_delta(
        wheel_delta,
        dataframe,
        reverse_state,
    ).dropna()
    plot_dataframe = dataframe.loc[valid_context_delta.index]
    plot_wheel_delta = valid_context_delta
    x_values, x_label = build_timeline_x_values(plot_dataframe, sample_rate_hz)
    plot_x_values = x_values.loc[plot_wheel_delta.index]

    line_color = context_color(reverse_state)
    alert_color = context_color(reverse_state)
    alert_mask = plot_wheel_delta > threshold

    fig, ax = plt.subplots(figsize=TIMELINE_FIGURE_SIZE)
    ax.plot(
        plot_x_values,
        plot_wheel_delta,
        linewidth=1.8,
        color=line_color,
        zorder=2,
    )
    set_focused_ylim(
        ax,
        pd.concat([plot_wheel_delta, pd.Series([threshold])]),
    )
    add_mean_hline(ax, plot_wheel_delta)
    add_threshold_hline(ax, threshold)

    if alert_mask.any():
        ax.scatter(
            plot_x_values.loc[alert_mask],
            plot_wheel_delta.loc[alert_mask],
            color=alert_color,
            edgecolors="white",
            linewidths=1.2,
            s=40,
            zorder=4,
        )

    add_steering_correction_legend(
        ax,
        line_color=line_color,
        alert_color=alert_color,
    )
    ax.set_xlabel(x_label)
    ax.set_ylabel("Steering change (degrees)")
    style_axis(ax)

    return finalize_chart(fig)
