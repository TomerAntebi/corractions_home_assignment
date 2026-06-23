"""Plot helpers — shared data prep, axis limits, annotations, and histogram styling."""

import matplotlib.dates as mdates
import matplotlib.pyplot as plt
import pandas as pd
from matplotlib.lines import Line2D
from matplotlib.patches import Patch

from ingestion import MeasurementColumn
from visualizations.chart_theme import (
    FORWARD_STATE_COLOR,
    LABEL_COLOR,
    REVERSE_SECTION_COLOR,
    SECONDARY_COLOR,
    TIMELINE_FIGURE_SIZE,
    context_colormap,
    context_color,
    finalize_chart,
    gradient_colors,
    style_axis,
)


def filter_driving_context(dataframe, reverse_state):
    return dataframe[dataframe[MeasurementColumn.REVERSE_STATE] == reverse_state].copy()


def format_time_axis(ax):
    ax.xaxis.set_major_formatter(mdates.DateFormatter("%H:%M:%S"))
    ax.tick_params(axis="x", rotation=25)


def set_figure_title(fig, title):
    fig.suptitle(
        title, fontsize=13, fontweight="bold", x=0.02, ha="left", color=LABEL_COLOR
    )


def set_focused_ylim(ax, values, *, padding_ratio=0.12):
    series = pd.Series(values).dropna()
    if series.empty:
        return

    span = series.max() - series.min()
    padding = max(span * padding_ratio, 0.5) if span else 0.5
    ax.set_ylim(series.min() - padding, series.max() + padding)


def set_focused_xlim(ax, values, *, padding_ratio=0.08):
    series = pd.Series(values).dropna()
    if series.empty:
        return

    span = series.max() - series.min()
    padding = max(span * padding_ratio, 0.5) if span else 0.5
    ax.set_xlim(series.min() - padding, series.max() + padding)


def add_mean_hline(ax, values, label_format="Avg: {:.1f}"):
    mean_value = pd.Series(values).mean()
    ax.axhline(
        mean_value, color=SECONDARY_COLOR, linestyle="--", linewidth=1.2, zorder=2,
    )
    xmax = ax.get_xlim()[1]
    ax.text(
        xmax,
        mean_value,
        f"  {label_format.format(mean_value)}",
        ha="right", va="center", fontsize=8, color=LABEL_COLOR,
    )


def label_bar(ax, bar, label, *, color=LABEL_COLOR, fontsize=9, fontweight=None):
    if pd.isna(bar.get_height()):
        return

    ax.text(
        bar.get_x() + bar.get_width() / 2,
        bar.get_height(),
        label,
        ha="center", va="bottom",
        fontsize=fontsize, fontweight=fontweight, color=color,
    )


def legend_line(label, color, **style):
    return Line2D([0], [0], color=color, linewidth=2.0, label=label, **style)


def legend_patch(label, color, alpha=0.14):
    return Patch(facecolor=color, alpha=alpha, edgecolor="none", label=label)


def legend_marker(label, **style):
    return Line2D([0], [0], label=label, **style)


def plot_forward_impact_metric(ax, x_positions, categories, title, ylabel, values, value_format):
    bars = ax.bar(
        x_positions, values, width=0.48,
        color=[FORWARD_STATE_COLOR, REVERSE_SECTION_COLOR],
        edgecolor="white", linewidth=1.0,
    )
    for bar, value in zip(bars, values):
        if pd.notna(value):
            label_bar(
                ax, bar, value_format.format(value),
                color=LABEL_COLOR, fontweight="bold",
            )
    ax.set(
        title=title, ylabel=ylabel, xticks=x_positions, ylim=(0, max(values) * 1.22)
    )
    ax.title.set_fontsize(11)
    ax.title.set_fontweight("bold")
    ax.set_xticklabels(categories, fontsize=8, fontweight="bold")
    style_axis(ax)


def plot_control_metric_bars(
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
        max_value = max((value for value in values if pd.notna(value)), default=5.0)
        ax.set_ylim(0, max(max_value * 1.35, 5.0))
    else:
        ax.set_ylim(*y_limit)

    for bar, value in zip(bars, values):
        if pd.notna(value):
            label_bar(
                ax, bar, value_format.format(value),
                color=label_color, fontweight="bold",
            )

    style_axis(ax)


def plot_context_timeline(dataframe, column, reverse_state, y_label, title):
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


def shade_reverse_segments_by_elapsed(ax, reverse_segments, *, alpha=0.14):
    for segment in reverse_segments:
        ax.axvspan(
            segment["start_second"], segment["end_second"],
            color=REVERSE_SECTION_COLOR, alpha=alpha, zorder=0,
        )


def _build_forward_intervals(reverse_segments, session_max_second):
    sorted_segments = sorted(
        reverse_segments,
        key=lambda segment: segment["start_second"],
    )
    forward_intervals = []
    current_start = 0.0

    for segment in sorted_segments:
        if segment["start_second"] > current_start:
            forward_intervals.append((current_start, segment["start_second"]))
        current_start = segment["end_second"]

    if current_start < session_max_second:
        forward_intervals.append((current_start, session_max_second))

    return sorted_segments, forward_intervals


def draw_context_threshold_lines(
    ax,
    reverse_segments,
    forward_threshold,
    reverse_threshold,
    session_max_second,
):
    sorted_segments, forward_intervals = _build_forward_intervals(
        reverse_segments,
        session_max_second,
    )

    for segment in sorted_segments:
        if pd.isna(reverse_threshold):
            continue

        start_second = segment["start_second"]
        end_second = segment["end_second"]
        ax.plot(
            [start_second, end_second],
            [reverse_threshold, reverse_threshold],
            color=REVERSE_SECTION_COLOR,
            linestyle="--", linewidth=2.0, alpha=0.85, zorder=3,
        )

    for interval_start, interval_end in forward_intervals:
        if pd.isna(forward_threshold):
            continue

        ax.plot(
            [interval_start, interval_end],
            [forward_threshold, forward_threshold],
            color=FORWARD_STATE_COLOR,
            linestyle="--", linewidth=2.0, alpha=0.85, zorder=3,
        )


def style_histogram(ax, values, *, reverse_state):
    cmap_name = context_colormap(reverse_state)
    patches = [patch for patch in ax.patches if patch.get_height() > 0]
    if not patches:
        return

    for patch, color in zip(patches, gradient_colors(len(patches), cmap_name)):
        patch.set_facecolor(color)

    counts = [patch.get_height() for patch in patches]
    ax.set_ylim(0, max(counts) * 1.12)

    for patch in patches:
        bar_height = patch.get_height()
        ax.text(
            patch.get_x() + patch.get_width() / 2,
            bar_height,
            f"{int(bar_height)}",
            ha="center", va="bottom", fontsize=8, color=LABEL_COLOR,
        )

    set_focused_xlim(ax, values)
