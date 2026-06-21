import matplotlib.pyplot as plt
import pandas as pd
import seaborn as sns

from analytics import context_wheel_delta
from ingestion import MeasurementColumn

sns.set_theme(style="whitegrid", context="notebook")

FORWARD_STATE_COLOR = "#4C78A8"
REVERSE_SECTION_COLOR = "#F58518"
SECONDARY_COLOR = "#64748b"
HIGHLIGHT_COLOR = "#dc2626"
LABEL_COLOR = "#334155"

TIMELINE_FIGURE_SIZE = (12, 6.5)
STANDARD_FIGURE_SIZE = (12, 6.0)
WIDE_FIGURE_SIZE = (12, 6.5)


def plot_timeline(dataframe, column, reverse_state, y_label, sample_rate_hz=None):
    context_data = _filter_driving_context(dataframe, reverse_state)
    y_values = context_data[column]
    x_values, x_label = _build_timeline_x_values(context_data, sample_rate_hz)
    valid_mask = y_values.notna()
    plot_y_values = y_values.loc[valid_mask]
    plot_x_values = x_values.loc[valid_mask]

    fig, ax = plt.subplots(figsize=TIMELINE_FIGURE_SIZE)
    ax.plot(
        plot_x_values,
        plot_y_values,
        linewidth=1.8,
        color=FORWARD_STATE_COLOR,
        zorder=2,
    )
    _set_focused_ylim(ax, plot_y_values)
    _add_mean_hline(ax, plot_y_values)
    ax.set_xlabel(x_label)
    ax.set_ylabel(y_label)
    _style_axis(ax)

    return _finalize_chart(fig)


def plot_distribution(dataframe, column, reverse_state, xlabel):
    context_data = _filter_driving_context(dataframe, reverse_state)
    values = context_data[column]
    bar_color = (
        FORWARD_STATE_COLOR if reverse_state == 0 else REVERSE_SECTION_COLOR
    )

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
    _style_histogram(ax, values, reverse_state=reverse_state)
    ax.set_xlabel(xlabel)
    ax.set_ylabel("Number of measurements")
    _style_axis(ax)

    return _finalize_chart(fig)


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
    x_values, x_label = _build_timeline_x_values(plot_dataframe, sample_rate_hz)
    plot_x_values = x_values.loc[plot_wheel_delta.index]

    line_color = (
        FORWARD_STATE_COLOR if reverse_state == 0 else REVERSE_SECTION_COLOR
    )
    alert_color = HIGHLIGHT_COLOR if reverse_state == 0 else REVERSE_SECTION_COLOR
    alert_mask = plot_wheel_delta > threshold

    fig, ax = plt.subplots(figsize=TIMELINE_FIGURE_SIZE)
    ax.plot(
        plot_x_values,
        plot_wheel_delta,
        linewidth=1.8,
        color=line_color,
        zorder=2,
    )
    _set_focused_ylim(
        ax,
        pd.concat([plot_wheel_delta, pd.Series([threshold])]),
    )
    _add_mean_hline(ax, plot_wheel_delta)
    _add_threshold_hline(ax, threshold)

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

    _add_steering_correction_legend(
        ax,
        line_color=line_color,
        alert_color=alert_color,
    )
    ax.set_xlabel(x_label)
    ax.set_ylabel("Steering change (degrees)")
    _style_axis(ax)

    return _finalize_chart(fig)


def plot_steering_buckets(bucket_dataframe):
    fig, ax = plt.subplots(figsize=WIDE_FIGURE_SIZE)
    speeds = bucket_dataframe["average_speed"]
    session_average = speeds.mean()
    category_positions = range(len(bucket_dataframe))

    bars = ax.bar(
        category_positions,
        speeds,
        color=_gradient_colors(len(bucket_dataframe), "Blues"),
        width=0.65,
        edgecolor="white",
        linewidth=0.8,
    )
    _set_focused_ylim(ax, speeds)
    _add_mean_hline(ax, speeds, label_format="Avg: {:.1f}")
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

    _style_axis(ax)

    return _finalize_chart(fig)


def _filter_driving_context(dataframe, reverse_state):
    return dataframe[
        dataframe[MeasurementColumn.REVERSE_STATE] == reverse_state
    ].reset_index(drop=True)


def _build_timeline_x_values(dataframe, sample_rate_hz=None):
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


def _style_axis(ax):
    ax.grid(alpha=0.25, linewidth=0.8)
    ax.set_axisbelow(True)
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    ax.spines["left"].set_color("#cbd5e1")
    ax.spines["bottom"].set_color("#cbd5e1")
    ax.tick_params(colors=LABEL_COLOR, labelsize=9)
    ax.xaxis.label.set_color(LABEL_COLOR)
    ax.yaxis.label.set_color(LABEL_COLOR)


def _gradient_colors(count, cmap_name="Blues"):
    colormap = plt.colormaps[cmap_name]
    return [
        colormap(0.35 + 0.55 * index / max(count - 1, 1))
        for index in range(count)
    ]


def _set_focused_ylim(ax, values, *, padding_ratio=0.12, floor_zero=False):
    series = pd.Series(values).dropna()
    if series.empty:
        return

    span = series.max() - series.min()
    padding = max(span * padding_ratio, 0.5) if span else 0.5
    lower = 0 if floor_zero and series.min() >= 0 else series.min() - padding
    ax.set_ylim(lower, series.max() + padding)


def _set_focused_xlim(ax, values, *, padding_ratio=0.08):
    series = pd.Series(values).dropna()
    if series.empty:
        return

    span = series.max() - series.min()
    padding = max(span * padding_ratio, 0.5) if span else 0.5
    ax.set_xlim(series.min() - padding, series.max() + padding)


def _add_mean_vline(ax, values, label_format="μ = {:.1f}"):
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


def _add_mean_hline(ax, values, label_format="Avg: {:.1f}"):
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


def _add_threshold_hline(ax, threshold, label_format="Threshold: {:.1f}"):
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


def _add_steering_correction_legend(ax, *, line_color, alert_color):
    from matplotlib.lines import Line2D

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


def _style_histogram(ax, values, *, reverse_state):
    cmap_name = "Oranges" if reverse_state == 1 else "Blues"
    patches = [patch for patch in ax.patches if patch.get_height() > 0]
    if not patches:
        return

    for patch, color in zip(patches, _gradient_colors(len(patches), cmap_name)):
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

    _set_focused_xlim(ax, values)
    _add_mean_vline(ax, values)


def _finalize_chart(fig):
    fig.tight_layout()
    return fig
