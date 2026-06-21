"""Driving charts — timeline, distribution, and steering bucket plots for Forward/Reverse tabs."""

import matplotlib.pyplot as plt
import seaborn as sns

from visualizations.chart_helpers import (
    add_mean_hline,
    build_timeline_x_values,
    filter_driving_context,
    set_focused_ylim,
    style_histogram,
)
from visualizations.theme import (
    LABEL_COLOR,
    STANDARD_FIGURE_SIZE,
    TIMELINE_FIGURE_SIZE,
    WIDE_FIGURE_SIZE,
    context_color,
    context_colormap,
    finalize_chart,
    gradient_colors,
    style_axis,
)


def plot_timeline(dataframe, column, reverse_state, y_label, sample_rate_hz=None):
    context_data = filter_driving_context(dataframe, reverse_state)
    y_values = context_data[column]
    x_values, x_label = build_timeline_x_values(context_data, sample_rate_hz)
    valid_mask = y_values.notna()
    plot_y_values = y_values.loc[valid_mask]
    plot_x_values = x_values.loc[valid_mask]

    fig, ax = plt.subplots(figsize=TIMELINE_FIGURE_SIZE)
    ax.plot(
        plot_x_values,
        plot_y_values,
        linewidth=1.8,
        color=context_color(reverse_state),
        zorder=2,
    )
    set_focused_ylim(ax, plot_y_values)
    add_mean_hline(ax, plot_y_values)
    ax.set_xlabel(x_label)
    ax.set_ylabel(y_label)
    style_axis(ax)

    return finalize_chart(fig)


def plot_distribution(dataframe, column, reverse_state, xlabel):
    context_data = filter_driving_context(dataframe, reverse_state)
    values = context_data[column]
    bar_color = context_color(reverse_state)

    fig, ax = plt.subplots(figsize=STANDARD_FIGURE_SIZE)
    sns.histplot(
        values,
        bins=12,
        kde=True,
        color=bar_color,
        edgecolor="white",
        linewidth=0.8,
        ax=ax,
    )
    style_histogram(ax, values, reverse_state=reverse_state)
    ax.set_xlabel(xlabel)
    ax.set_ylabel("Number of measurements")
    style_axis(ax)

    return finalize_chart(fig)


def plot_steering_buckets(bucket_dataframe, reverse_state):
    fig, ax = plt.subplots(figsize=WIDE_FIGURE_SIZE)
    speeds = bucket_dataframe["average_speed"]
    session_average = speeds.mean()
    category_positions = range(len(bucket_dataframe))

    bars = ax.bar(
        category_positions,
        speeds,
        color=gradient_colors(
            len(bucket_dataframe),
            context_colormap(reverse_state),
        ),
        width=0.65,
        edgecolor="white",
        linewidth=0.8,
    )
    set_focused_ylim(ax, speeds)
    add_mean_hline(ax, speeds, label_format="Avg: {:.1f}")
    ax.set_xticks(category_positions)
    ax.set_xticklabels(
        [f"{label} deg" for label in bucket_dataframe["steering_bucket"].astype(str)]
    )
    ax.set_xlabel("Steering angle range")
    ax.set_ylabel("Average speed (km/h)")

    for index, bar in enumerate(bars):
        row = bucket_dataframe.iloc[index]
        bar_height = bar.get_height()
        delta = bar_height - session_average
        ax.text(
            bar.get_x() + bar.get_width() / 2,
            bar_height,
            f"{bar_height:.1f}\n{delta:+.1f} vs avg\n(n={int(row['count'])})",
            ha="center",
            va="bottom",
            fontsize=8,
            color=LABEL_COLOR,
        )

    style_axis(ax)

    return finalize_chart(fig)
