"""Chart helpers — shared data prep, axis limits, annotations, and histogram styling."""

import matplotlib.dates as mdates
import pandas as pd

from ingestion import MeasurementColumn
from visualizations.theme import (
    FORWARD_STATE_COLOR,
    LABEL_COLOR,
    REVERSE_SECTION_COLOR,
    SECONDARY_COLOR,
    context_colormap,
    gradient_colors,
)


def filter_driving_context(dataframe, reverse_state):
    return dataframe[dataframe[MeasurementColumn.REVERSE_STATE] == reverse_state].copy()


def format_time_axis(ax):
    ax.xaxis.set_major_formatter(mdates.DateFormatter("%H:%M:%S"))
    ax.tick_params(axis="x", rotation=25)


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


def add_mean_vline(ax, values, label_format="μ = {:.1f}"):
    mean_value = pd.Series(values).mean()
    ax.axvline(
        mean_value, color=SECONDARY_COLOR, linestyle="--", linewidth=1.2, zorder=3,
    )
    _, ymax = ax.get_ylim()
    ax.text(
        mean_value,
        ymax * 0.95,
        label_format.format(mean_value),
        ha="left", va="top", fontsize=8, color=LABEL_COLOR,
        bbox={
            "boxstyle": "round,pad=0.2",
            "facecolor": "white",
            "edgecolor": "none",
            "alpha": 0.85,
        },
    )


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
    add_mean_vline(ax, values)
