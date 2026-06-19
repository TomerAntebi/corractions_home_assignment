import matplotlib.pyplot as plt
from matplotlib.axes import Axes
from matplotlib.figure import Figure
import pandas as pd

from dashboard.helpers import format_count


PRIMARY_COLOR = "#2563eb"
SECONDARY_COLOR = "#64748b"
SUCCESS_COLOR = "#16a34a"
WARNING_COLOR = "#f59e0b"
DANGER_COLOR = "#dc2626"
CHART_COLORS = [PRIMARY_COLOR, WARNING_COLOR, DANGER_COLOR, SUCCESS_COLOR, SECONDARY_COLOR]


def style_axis(ax: Axes) -> None:
    ax.grid(alpha=0.18)
    ax.set_axisbelow(True)
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    ax.spines["left"].set_color("#cbd5e1")
    ax.spines["bottom"].set_color("#cbd5e1")
    ax.tick_params(colors="#334155", labelsize=9)
    ax.xaxis.label.set_color("#334155")
    ax.yaxis.label.set_color("#334155")


def create_horizontal_bar_chart(
    dataframe: pd.DataFrame,
    category_column: str,
    value_column: str,
    x_label: str,
) -> Figure:
    chart_height = max(2.4, 0.55 * len(dataframe) + 1.2)
    fig, ax = plt.subplots(figsize=(9, chart_height))
    bar_values = pd.to_numeric(dataframe[value_column], errors="coerce").fillna(0)
    categories = dataframe[category_column].astype(str)
    bar_colors = [CHART_COLORS[index % len(CHART_COLORS)] for index in range(len(dataframe))]

    ax.barh(categories, bar_values, color=bar_colors)
    ax.set_xlabel(x_label)
    ax.set_ylabel("")
    ax.invert_yaxis()
    style_axis(ax)
    ax.grid(axis="x", alpha=0.18)
    ax.grid(axis="y", visible=False)

    max_value = float(bar_values.max()) if not bar_values.empty else 0
    x_limit = max(max_value * 1.18, 1)
    ax.set_xlim(0, x_limit)
    label_offset = x_limit * 0.02
    for index, value in enumerate(bar_values):
        ax.text(
            max(float(value), 0) + label_offset,
            index,
            format_count(float(value)),
            va="center",
            fontsize=9,
            color="#334155",
        )

    fig.tight_layout()

    return fig


def create_line_chart(
    dataframe: pd.DataFrame,
    x_column: str,
    y_column: str,
    x_label: str,
    y_label: str,
    reference_value: float | None = None,
    reference_label: str | None = None,
) -> Figure:
    fig, ax = plt.subplots(figsize=(10, 4.2))

    ax.plot(dataframe[x_column], dataframe[y_column], linewidth=2, color=PRIMARY_COLOR)
    if reference_value is not None and reference_label is not None:
        ax.axhline(
            reference_value,
            color=SECONDARY_COLOR,
            linestyle="--",
            linewidth=1.2,
            label=reference_label,
        )
        ax.legend(frameon=False, fontsize=9)
    ax.set_xlabel(x_label)
    ax.set_ylabel(y_label)
    style_axis(ax)
    fig.tight_layout()

    return fig


GROUPED_BAR_COLORS = {
    "Forward": PRIMARY_COLOR,
    "Reverse": SECONDARY_COLOR,
}


def create_grouped_bar_chart(
    dataframe: pd.DataFrame,
    category_column: str,
    group_column: str,
    value_column: str,
    x_label: str,
    y_label: str,
) -> Figure:
    fig, ax = plt.subplots(figsize=(8, 4.2))
    categories = dataframe[category_column].astype(str).drop_duplicates().tolist()
    groups = dataframe[group_column].astype(str).drop_duplicates().tolist()
    bar_width = 0.35
    category_positions = list(range(len(categories)))
    grouped_bar_values: list[tuple[str, list[float], list[float]]] = []
    max_value = 0.0

    for group_index, group_name in enumerate(groups):
        group_dataframe = dataframe[dataframe[group_column].astype(str) == group_name]
        bar_values = [
            float(
                pd.to_numeric(
                    group_dataframe.loc[
                        group_dataframe[category_column].astype(str) == category,
                        value_column,
                    ].iloc[0],
                    errors="coerce",
                )
            )
            if not group_dataframe.loc[
                group_dataframe[category_column].astype(str) == category
            ].empty
            else 0.0
            for category in categories
        ]
        bar_positions = [
            category_index + (group_index - (len(groups) - 1) / 2) * bar_width
            for category_index in category_positions
        ]
        grouped_bar_values.append((group_name, bar_positions, bar_values))
        max_value = max(max_value, max(bar_values, default=0.0))

    y_limit = max(max_value * 1.18, 1)
    label_offset = y_limit * 0.02

    for group_index, (group_name, bar_positions, bar_values) in enumerate(grouped_bar_values):
        bars = ax.bar(
            bar_positions,
            bar_values,
            width=bar_width,
            label=group_name,
            color=GROUPED_BAR_COLORS.get(
                group_name,
                CHART_COLORS[group_index % len(CHART_COLORS)],
            ),
        )
        for bar in bars:
            bar_height = bar.get_height()
            ax.text(
                bar.get_x() + bar.get_width() / 2,
                bar_height + label_offset,
                f"{bar_height:.1f}",
                ha="center",
                va="bottom",
                fontsize=9,
                color="#334155",
            )

    ax.set_xticks(category_positions)
    ax.set_xticklabels(categories)
    ax.set_xlabel(x_label)
    ax.set_ylabel(y_label)
    ax.set_ylim(0, y_limit)
    ax.legend(frameon=False, fontsize=9)
    style_axis(ax)
    ax.grid(axis="y", alpha=0.18)
    ax.grid(axis="x", visible=False)
    fig.tight_layout()

    return fig


def create_scatter_chart(
    dataframe: pd.DataFrame,
    x_column: str,
    y_column: str,
    x_label: str,
    y_label: str,
) -> Figure:
    fig, ax = plt.subplots(figsize=(8, 5))
    ax.scatter(
        dataframe[x_column],
        dataframe[y_column],
        alpha=0.65,
        s=36,
        color=PRIMARY_COLOR,
        edgecolors="white",
        linewidths=0.4,
    )
    ax.set_xlabel(x_label)
    ax.set_ylabel(y_label)
    style_axis(ax)
    fig.tight_layout()

    return fig

