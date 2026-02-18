# ==========================================
# File: chart_renderer.py
# Added in iteration: 4
# Author: Karl Concha
#
# Purpose:
# Render a simple chart spec to SVG for stage artifacts.
# ==========================================

import io


def render_chart_svg(spec):
    try:
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
    except Exception:
        return None

    title = spec.get("title") or "Chart"
    labels = spec.get("labels") or spec.get("categories") or []
    values = spec.get("values") or spec.get("data") or []
    x_label = spec.get("x_label") or ""
    y_label = spec.get("y_label") or "Value"

    if not labels and values and isinstance(values[0], dict):
        labels = [v.get("label", "") for v in values]
        values = [v.get("value", 0) for v in values]

    if not labels or not values:
        return None

    n = min(len(labels), len(values))
    labels = labels[:n]
    values = values[:n]

    try:
        values = [float(v) for v in values]
    except Exception:
        return None

    fig, ax = plt.subplots(figsize=(8, 4.5), dpi=100)
    ax.bar(range(n), values, color=spec.get("color", "#6C63FF"))
    ax.set_title(title)
    ax.set_ylabel(y_label)
    if x_label:
        ax.set_xlabel(x_label)
    ax.set_xticks(range(n))
    ax.set_xticklabels(labels, rotation=25, ha="right")
    ax.grid(axis="y", linestyle="--", alpha=0.3)
    fig.tight_layout()

    buffer = io.StringIO()
    fig.savefig(buffer, format="svg")
    plt.close(fig)
    return buffer.getvalue()
