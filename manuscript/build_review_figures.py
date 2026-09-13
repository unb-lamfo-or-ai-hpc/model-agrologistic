"""Render partial review evidence without filling missing experimental values."""
from __future__ import annotations

import json
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import seaborn as sns

ROOT = Path(__file__).resolve().parent


def build() -> None:
    """Keep partial diagnostic observations separate from comparative claims."""
    data = json.loads((ROOT / "results_snapshot.json").read_text(encoding="utf-8"))
    destination = ROOT / "figures"
    destination.mkdir(exist_ok=True)
    sns.set_theme(style="whitegrid", context="paper", font_scale=1.15)

    def save(fig, name):
        fig.tight_layout()
        fig.savefig(destination / f"{name}.png", dpi=200, bbox_inches="tight")
        plt.close(fig)

    fig, ax = plt.subplots(figsize=(7.2, 3.2))
    families = data["validation"]
    accepted = [r["accepted"] for r in families]
    remaining = [r["expected"] - r["accepted"] for r in families]
    positions = np.arange(len(families))
    ax.barh(positions, accepted, color="#287c8e", label="Accepted reference")
    ax.barh(positions, remaining, left=accepted, color="#dfaa48", label="Incomplete hierarchy")
    ax.set_yticks(positions, [r["family"] for r in families])
    ax.set_xlabel("Number of selected reference executions")
    ax.set_xticks(range(6))
    ax.invert_yaxis()
    ax.legend(loc="lower right", fontsize=8)
    save(fig, "validation-coverage")

    fig, ax = plt.subplots(figsize=(7.2, 3.2))
    bottom = np.zeros(2)
    for arc, color in zip(("OD", "DC", "DD", "OC"),
                          sns.color_palette("colorblind", 4), strict=True):
        values = np.array([data["routing"][n][arc] for n in ("215", "500")]) / 1000
        ax.bar(("215 warehouses", "500 warehouses"), values, bottom=bottom,
               label=arc, color=color)
        bottom += values
    ax.set_ylabel("Materialized ordered routes (thousands)")
    ax.legend(title="Route family", ncol=4, loc="upper left")
    ax.set_ylim(0, 335)
    for i, total in enumerate(bottom):
        ax.text(i, total + 4, f"{total:,.3f}", ha="center")
    save(fig, "routing-growth")

    completed = [r for r in data["jobs"] if r["elapsed_seconds"] is not None]
    labels = [r["configuration"] + "\n" + r["job"] for r in completed]
    colors = ["#287c8e" if r["status"] == "COMPLETED" else "#bd6841" for r in completed]
    fig, axes = plt.subplots(1, 2, figsize=(7.2, 3.6))
    axes[0].bar(range(3), [r["elapsed_seconds"] / 3600 for r in completed], color=colors)
    axes[0].set_ylabel("Whole-job elapsed time (hours)")
    axes[1].bar(range(3), [r["max_rss_kib"] / 1048576 for r in completed], color=colors)
    axes[1].set_ylabel("Maximum resident-set size (GiB)")
    for ax in axes:
        ax.set_xticks(range(3), labels, rotation=22, ha="right", fontsize=7)
    fig.suptitle("Blue: completed; orange: failed. Running retry excluded.", fontsize=10)
    save(fig, "retry-resources")

    failed = [r for r in completed if r["economic_gap_fraction"] is not None]
    fig, ax = plt.subplots(figsize=(7.2, 3.2))
    ax.barh([r["job"] for r in failed],
            [100 * r["economic_gap_fraction"] for r in failed], color="#bd6841")
    ax.axvline(1, color="#287c8e", label="Configured target: 1%")
    ax.axvline(10, color="#69518a", linestyle="--", label="10% reference, not configured")
    ax.set_xlim(0, 60)
    ax.set_xlabel("Economic-pass incumbent–bound relative gap (%)")
    for i, row in enumerate(failed):
        ax.text(100 * row["economic_gap_fraction"] + 1, i,
                f"{100 * row['economic_gap_fraction']:.2f}%", va="center")
    ax.legend(loc="lower right", fontsize=8)
    save(fig, "incomplete-economic-gaps")


if __name__ == "__main__":
    build()
