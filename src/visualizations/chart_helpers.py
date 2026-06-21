"""Chart helpers — shared data prep, axis limits, annotations, and histogram styling."""

import pandas as pd
from matplotlib.lines import Line2D

from ingestion import MeasurementColumn
from visualizations.theme import (
    HIGHLIGHT_COLOR,
    LABEL_COLOR,
    SECONDARY_COLOR,
    context_colormap,
    gradient_colors,
)


def filter_driving_context(dataframe, reverse_state):
    return dataframe[
        dataframe[MeasurementColumn.REVERSE_STATE] == reverse_state
    ].reset_index(drop=True)


def build_timeline_x_values(dataframe, sample_rate_hz=None):
    def elapsed_or_sample_index():
        if sample_rate_hz and sample_rate_hz > 0:
            elapsed_seconds = pd.Series(
                dataframe.index / sample_rate_hz,
                index=dataframe.index,
            )
            return elapsed_seconds, "Elapsed time (seconds)"

        sample_index = pd.Series(range(len(dataframe)), index=dataframe.index)
        return sample_index, "Sample index"

    if MeasurementColumn.TIMESTAMP not in dataframe.columns:
        return elapsed_or_sample_index()

    timestamps = dataframe[MeasurementColumn.TIMESTAMP]

    if timestamps.isna().any():
        return elapsed_or_sample_index()

    if not timestamps.is_monotonic_increasing:
        return elapsed_or_sample_index()

    if timestamps.nunique() <= 1:
        return elapsed_or_sample_index()

    if timestamps.nunique() < len(dataframe):
        return elapsed_or_sample_index()

    elapsed_seconds = (timestamps - timestamps.iloc[0]).dt.total_seconds()

    if elapsed_seconds.nunique() < len(dataframe):
        return elapsed_or_sample_index()

    return elapsed_seconds, "Elapsed time (seconds)"


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
        mean_value,
        color=SECONDARY_COLOR,
        linestyle="--",
        linewidth=1.2,
        zorder=3,
    )
    _, ymax = ax.get_ylim()
    ax.text(
        mean_value,
        ymax * 0.95,
        label_format.format(mean_value),
        ha="left",
        va="top",
        fontsize=8,
        color=LABEL_COLOR,
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
        mean_value,
        color=SECONDARY_COLOR,
        linestyle="--",
        linewidth=1.2,
        zorder=2,
    )
    xmax = ax.get_xlim()[1]
    ax.text(
        xmax,
        mean_value,
        f"  {label_format.format(mean_value)}",
        ha="right",
        va="center",
        fontsize=8,
        color=LABEL_COLOR,
    )


def add_threshold_hline(ax, threshold, label_format="Threshold: {:.1f}"):
    ax.axhline(
        threshold,
        color=HIGHLIGHT_COLOR,
        linestyle=":",
        linewidth=1.2,
        zorder=2,
    )
    xmax = ax.get_xlim()[1]
    ax.text(
        xmax,
        threshold,
        f"  {label_format.format(threshold)}",
        ha="right",
        va="bottom",
        fontsize=8,
        color=LABEL_COLOR,
    )


def add_steering_correction_legend(ax, *, line_color, alert_color):
    ax.legend(
        handles=[
            Line2D(
                [0],
                [0],
                color=line_color,
                linewidth=1.8,
                label="Steering change",
            ),
            Line2D(
                [0],
                [0],
                color=SECONDARY_COLOR,
                linestyle="--",
                linewidth=1.2,
                label="Average steering change",
            ),
            Line2D(
                [0],
                [0],
                color=HIGHLIGHT_COLOR,
                linestyle=":",
                linewidth=1.2,
                label="Sudden correction threshold",
            ),
            Line2D(
                [0],
                [0],
                marker="o",
                color="w",
                markerfacecolor=alert_color,
                markeredgecolor=alert_color,
                markersize=8,
                label="Abrupt correction",
            ),
        ],
        frameon=False,
        fontsize=8,
        loc="upper right",
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
            ha="center",
            va="bottom",
            fontsize=8,
            color=LABEL_COLOR,
        )

    set_focused_xlim(ax, values)
    add_mean_vline(ax, values)
