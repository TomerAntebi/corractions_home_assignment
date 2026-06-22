"""Driving charts — timeline, distribution, and steering bucket plots for Forward/Reverse tabs."""

import matplotlib.pyplot as plt
import pandas as pd
import seaborn as sns

from ingestion import MeasurementColumn
from visualizations.chart_helpers import (
    add_mean_hline,
    filter_driving_context,
    format_time_axis,
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


def plot_speed_timeline(dataframe, reverse_state, title):
    return _plot_timeline(
        dataframe,
        MeasurementColumn.SPEED,
        reverse_state=reverse_state,
        y_label="Speed (km/h)",
        title=title,
    )


def plot_steering_timeline(dataframe, reverse_state, title):
    return _plot_timeline(
        dataframe,
        MeasurementColumn.WHEEL_ANGLE,
        reverse_state=reverse_state,
        y_label="Steering angle (degrees)",
        title=title,
    )


def _plot_timeline(dataframe, column, reverse_state, y_label, title):
    context_data = filter_driving_context(dataframe, reverse_state)
    y_values = context_data[column].copy()
    plot_values = y_values.interpolate(limit_direction="both")
    plot_values.loc[context_data.index.to_series().diff().gt(1)] = pd.NA
    x_values = context_data[MeasurementColumn.DISPLAY_TIME]
    valid_mask = y_values.notna()

    fig, ax = plt.subplots(figsize=TIMELINE_FIGURE_SIZE)
    ax.plot(
        x_values, plot_values,
        linewidth=1.8, color=context_color(reverse_state), zorder=2,
    )
    set_focused_ylim(ax, y_values.loc[valid_mask])
    add_mean_hline(ax, y_values.loc[valid_mask])
    ax.set(title=title, xlabel="Time", ylabel=y_label)
    format_time_axis(ax)
    style_axis(ax)

    return finalize_chart(fig)


def plot_distribution(dataframe, column, reverse_state, title, xlabel):
    context_data = filter_driving_context(dataframe, reverse_state)
    values = context_data[column]
    bar_color = context_color(reverse_state)

    fig, ax = plt.subplots(figsize=STANDARD_FIGURE_SIZE)
    sns.histplot(
        values, bins=12, kde=True, color=bar_color,
        edgecolor="white", linewidth=0.8, ax=ax,
    )
    style_histogram(ax, values, reverse_state=reverse_state)
    ax.set(title=title, xlabel=xlabel, ylabel="Number of measurements")
    style_axis(ax)

    return finalize_chart(fig)


def plot_steering_buckets(bucket_dataframe, reverse_state, title):
    fig, ax = plt.subplots(figsize=WIDE_FIGURE_SIZE)
    speeds = bucket_dataframe["average_speed"]
    session_average = speeds.mean()
    category_positions = range(len(bucket_dataframe))

    bars = ax.bar(
        category_positions, speeds,
        color=gradient_colors(
            len(bucket_dataframe),
            context_colormap(reverse_state),
        ),
        width=0.65, edgecolor="white", linewidth=0.8,
    )
    set_focused_ylim(ax, speeds)
    add_mean_hline(ax, speeds, label_format="Avg: {:.1f}")
    ax.set(
        title=title,
        xlabel="Steering intensity",
        ylabel="Average speed (km/h)",
        xticks=category_positions,
    )
    ax.set_xticklabels(bucket_dataframe["steering_bucket"].astype(str).tolist())

    for index, bar in enumerate(bars):
        row = bucket_dataframe.iloc[index]
        bar_height = bar.get_height()
        if pd.isna(bar_height):
            continue

        delta = bar_height - session_average
        ax.text(
            bar.get_x() + bar.get_width() / 2,
            bar_height,
            f"{bar_height:.1f}\n{delta:+.1f} vs avg\n(n={int(row['count'])})",
            ha="center", va="bottom", fontsize=8, color=LABEL_COLOR,
        )

    style_axis(ax)

    return finalize_chart(fig)
