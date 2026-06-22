"""Chart theme — shared colors, figure sizes, seaborn setup, and axis styling."""

import matplotlib.pyplot as plt
import seaborn as sns

sns.set_theme(style="whitegrid", context="notebook")

FORWARD_STATE_COLOR = "#4C78A8"
REVERSE_SECTION_COLOR = "#F58518"
SECONDARY_COLOR = "#64748b"
HIGHLIGHT_COLOR = "#dc2626"
LABEL_COLOR = "#334155"

TIMELINE_FIGURE_SIZE = (12, 4.6)
STANDARD_FIGURE_SIZE = (10.5, 4.2)
WIDE_FIGURE_SIZE = (11, 4.5)
CONTROL_PROFILE_FIGURE_SIZE = (12, 4.8)
ATTENTION_MAPPING_FIGURE_SIZE = (12, 5.2)
BEHAVIOR_STABILITY_COLOR = "#2ca02c"
BEHAVIOR_STABILITY_LABEL_COLOR = "#1e6b1e"
BEHAVIOR_JERKINESS_COLOR = "#d62728"
BEHAVIOR_JERKINESS_LABEL_COLOR = "#8c1a1a"
STEERING_LINE_COLOR = "#475569"


def context_color(reverse_state):
    return FORWARD_STATE_COLOR if reverse_state == 0 else REVERSE_SECTION_COLOR


def context_colormap(reverse_state):
    return "Oranges" if reverse_state == 1 else "Blues"


def style_axis(ax):
    ax.grid(alpha=0.25, linewidth=0.8)
    ax.set_axisbelow(True)
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    ax.spines["left"].set_color("#cbd5e1")
    ax.spines["bottom"].set_color("#cbd5e1")
    ax.tick_params(colors=LABEL_COLOR, labelsize=9)
    ax.xaxis.label.set_color(LABEL_COLOR)
    ax.yaxis.label.set_color(LABEL_COLOR)


def gradient_colors(count, cmap_name="Blues"):
    colormap = plt.colormaps[cmap_name]
    return [
        colormap(0.35 + 0.55 * index / max(count - 1, 1))
        for index in range(count)
    ]


def finalize_chart(fig):
    fig.tight_layout()
    return fig
