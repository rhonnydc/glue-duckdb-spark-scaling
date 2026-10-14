"""Render the AWS Glue benchmark figures from run-level CSVs.

Requires Matplotlib. Run from any directory: python scripts/generate_figures.py
"""

from __future__ import annotations

import csv
from collections import defaultdict
from pathlib import Path
from statistics import mean

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.lines import Line2D
from matplotlib.patches import FancyBboxPatch
from matplotlib.ticker import FuncFormatter, MultipleLocator


ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "figures"
STAGES = ("0.3gb", "1.0gb", "3.0gb", "4.5gb", "6.0gb", "10.0gb")
PAIRED_STAGES = STAGES[:4]
LABELS = ("0.3 GB", "1 GB", "3 GB", "4.5 GB", "6 GB", "10 GB")
ENGINES = ("duckdb", "spark")

# Two series colors and a separate, subdued status color.
INK = "#27343D"
MUTED = "#64717A"
GRID = "#E5E9E8"
DUCK = "#286B75"
SPARK = "#BD8055"
FAIL = "#A55F56"
SUCCESS_TINT = "#EAF2F0"
FAIL_TINT = "#F7EEEB"
PAPER = "#FEFEFC"


def read_csv(name: str) -> list[dict[str, str]]:
    with (ROOT / "results" / name).open(newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


COMPLETED = [row for row in read_csv("glue_scaling_runs.csv")
             if row["data_volume"] in STAGES]
INCOMPLETE = read_csv("glue_scaling_failures.csv")
completed_groups: dict[tuple[str, str], list[dict[str, str]]] = defaultdict(list)
incomplete_groups: dict[tuple[str, str], list[dict[str, str]]] = defaultdict(list)
for row in COMPLETED:
    completed_groups[row["data_volume"], row["engine"]].append(row)
for row in INCOMPLETE:
    incomplete_groups[row["stage"], row["engine"]].append(row)


def validate() -> None:
    expected = {
        (stage, engine): (5 if stage not in ("6.0gb", "10.0gb") else
                          1 if engine == "spark" else 0)
        for stage in STAGES for engine in ENGINES
    }
    for key, n in expected.items():
        if len(completed_groups[key]) != n:
            raise ValueError(f"Unexpected completed-run count for {key}: {len(completed_groups[key])}")
    if len(incomplete_groups["6.0gb", "duckdb"]) != 2 or len(incomplete_groups["10.0gb", "duckdb"]) != 3:
        raise ValueError("Unexpected DuckDB non-completion counts")
    if any(key not in expected for key in completed_groups):
        raise ValueError("Unexpected size or engine in completed runs")
    if any((key[1] != "duckdb" or key[0] not in ("6.0gb", "10.0gb")) for key in incomplete_groups):
        raise ValueError("Unexpected non-completion group")
    for stage in STAGES:
        rows = completed_groups[stage, "spark"] + completed_groups[stage, "duckdb"] + incomplete_groups[stage, "duckdb"]
        if len({r["input_bytes"] for r in rows}) != 1:
            raise ValueError(f"Input byte counts disagree at {stage}")


validate()
X = {stage: int(completed_groups[stage, "spark"][0]["input_bytes"]) / 1e9 for stage in STAGES}


def style() -> None:
    plt.rcParams.update({
        "font.family": "Segoe UI",
        "font.size": 11,
        "text.color": INK,
        "axes.labelcolor": MUTED,
        "xtick.color": MUTED,
        "ytick.color": MUTED,
        "axes.edgecolor": GRID,
        "axes.linewidth": 0.8,
        "figure.facecolor": PAPER,
        "axes.facecolor": PAPER,
        "savefig.facecolor": PAPER,
    })


LAYOUTS = {
    "github": {
        "size": (12.8, 7.2), "dpi": 150,
        "plot": (0.095, 0.345, 0.84, 0.365),
        "band": (0.095, 0.15, 0.84, 0.075),
        "title_y": 0.925, "sub_y": 0.865, "legend_y": 0.815,
        "footer_y": 0.045,
        "title_size": 20, "sub_size": 11.7, "tick_size": 10.5,
    },
}


def new_figure(layout: str, title: str, subtitle: str, *, legend: bool = True):
    cfg = LAYOUTS[layout]
    fig = plt.figure(figsize=cfg["size"], dpi=cfg["dpi"])
    left = cfg["plot"][0]
    fig.text(left, cfg["title_y"], title, ha="left", va="top", fontsize=cfg["title_size"],
             fontweight="semibold", color=INK)
    fig.text(left, cfg["sub_y"], subtitle, ha="left", va="top", fontsize=cfg["sub_size"], color=MUTED)
    if legend:
        handles = [
            Line2D([], [], color=DUCK, lw=2.1, marker="o", markersize=4.5, label="DuckDB"),
            Line2D([], [], color=SPARK, lw=2.1, marker="o", markersize=4.5, label="Spark"),
        ]
        fig.legend(handles=handles, loc="upper left", bbox_to_anchor=(left - 0.005, cfg["legend_y"]),
                   frameon=False, ncol=2, columnspacing=1.9, handlelength=2.0,
                   handletextpad=0.55, fontsize=cfg["tick_size"])
    return fig, cfg


def clean_axis(ax, cfg: dict, *, numeric_x: bool = True) -> None:
    ax.spines[["top", "right", "left"]].set_visible(False)
    ax.spines["bottom"].set_color(GRID)
    ax.tick_params(axis="both", which="both", length=0, pad=9, labelsize=cfg["tick_size"])
    ax.grid(axis="y", color=GRID, linewidth=0.7)
    ax.set_axisbelow(True)
    if numeric_x:
        ax.set_xlim(0, 10.65)
        ax.set_xticks([X[stage] for stage in STAGES], LABELS)


def status_band(fig, cfg: dict, *, crosses: bool = True) -> None:
    """Outcome track is independent of the numeric axes, so failure is never zero."""
    band = fig.add_axes(cfg["band"])
    band.set_xlim(0, 10.65)
    band.set_ylim(0, 1)
    band.axis("off")
    band.axhline(0.98, color=GRID, lw=0.8)
    label_size = cfg["tick_size"] - 0.4
    band.text(0, 0.45, "DuckDB non-completion", ha="left", va="center",
              fontsize=label_size, color=MUTED)
    for stage in ("6.0gb", "10.0gb"):
        attempts = len(incomplete_groups[stage, "duckdb"])
        label = f"×  0/{attempts}" if crosses else f"0/{attempts} completed"
        band.text(X[stage], 0.45, label, ha="center", va="center",
                  fontsize=label_size + 0.3, fontweight="semibold", color=FAIL)


def source_note(fig, cfg: dict, text: str) -> None:
    fig.text(cfg["plot"][0], cfg["footer_y"], text, ha="left", va="bottom",
             fontsize=cfg["tick_size"] - 1.7, color=MUTED)


def line_figure(layout: str, metric: str):
    is_cost = metric == "estimated_glue_compute_usd"
    title = "Execution cost vs. dataset size" if is_cost else "Execution time vs. dataset size"
    subtitle = ("Estimated Glue compute cost per completed job" if is_cost else
                "Average job duration (start to finish), or wall time")
    fig, cfg = new_figure(layout, title, subtitle)
    ax = fig.add_axes(cfg["plot"])
    clean_axis(ax, cfg)
    ax.set_ylabel("USD per job" if is_cost else "Seconds", fontsize=cfg["tick_size"],
                  rotation=0, labelpad=0, ha="left", va="bottom")
    ax.yaxis.set_label_coords(0, 1.025)
    if is_cost:
        ax.set_ylim(0, 0.12)
        ax.yaxis.set_major_locator(MultipleLocator(0.02))
        ax.yaxis.set_major_formatter(FuncFormatter(lambda y, _: f"${y:.2f}"))
    else:
        ax.set_ylim(0, 700)
        ax.yaxis.set_major_locator(MultipleLocator(100))

    for engine, color in (("duckdb", DUCK), ("spark", SPARK)):
        stages = [stage for stage in STAGES if completed_groups[stage, engine]]
        xx = [X[stage] for stage in stages]
        yy = [mean(float(row[metric]) for row in completed_groups[stage, engine]) for stage in stages]
        ax.plot(xx, yy, color=color, lw=2.15, marker="o", markersize=4.8,
                markerfacecolor=PAPER, markeredgewidth=1.75, solid_capstyle="round", zorder=3)

    status_band(fig, cfg)
    if is_cost:
        source_note(fig, cfg, "Means of completed jobs; n=5 through 4.5 GB, Spark n=1 at 6 and 10 GB.\n"
                              "Glue compute estimate at $0.308/DPU-hour; other AWS charges excluded.")
    else:
        source_note(fig, cfg, "Means of completed jobs. n=5 per engine through 4.5 GB; Spark n=1 at 6 and 10 GB.")
    return fig


def paired_time_figure(layout: str):
    fig, cfg = new_figure(
        layout,
        "Execution time: 0.3–4.5 GB",
        "Average job duration (start to finish), or wall time",
    )
    ax = fig.add_axes((cfg["plot"][0], 0.27, cfg["plot"][2], 0.44))
    clean_axis(ax, cfg, numeric_x=False)
    ax.set_xlim(0, 5.0)
    ax.set_xticks([X[stage] for stage in PAIRED_STAGES], LABELS[:4])
    ax.set_ylim(0, 400)
    ax.yaxis.set_major_locator(MultipleLocator(50))
    ax.set_ylabel("Seconds", fontsize=cfg["tick_size"], rotation=0,
                  labelpad=0, ha="left", va="bottom")
    ax.yaxis.set_label_coords(0, 1.025)

    for engine, color in (("duckdb", DUCK), ("spark", SPARK)):
        values = [mean(float(row["wall_seconds"])
                       for row in completed_groups[stage, engine])
                  for stage in PAIRED_STAGES]
        ax.plot([X[stage] for stage in PAIRED_STAGES], values,
                color=color, lw=2.15, marker="o", markersize=4.8,
                markerfacecolor=PAPER, markeredgewidth=1.75,
                solid_capstyle="round", zorder=3)

    source_note(fig, cfg,
                "Five completed runs per engine and size. Only volumes where both engines completed are shown.")
    return fig


def success_figure(layout: str):
    fig, cfg = new_figure(layout, "ETL execution success", "Completed jobs / attempted jobs", legend=False)
    pos = (0.155, 0.25, 0.79, 0.49)
    row_label_x = 0.09
    ax = fig.add_axes(pos)
    ax.set_xlim(-0.42, 5.43)
    ax.set_ylim(-0.15, 2.15)
    ax.axis("off")

    for col, (stage, label) in enumerate(zip(STAGES, LABELS)):
        ax.text(col, 1.95, label, ha="center", va="center", color=INK,
                fontsize=cfg["tick_size"] + 0.2, fontweight="semibold")
    for row_index, engine in enumerate(ENGINES):
        y = 1.27 - row_index * 0.92
        figure_y = pos[1] + pos[3] * ((y + 0.15) / 2.3)
        fig.text(row_label_x, figure_y, "DuckDB" if engine == "duckdb" else "Spark",
                 ha="left", va="center", color=INK, fontsize=cfg["tick_size"] + 1,
                 fontweight="semibold")
        for col, stage in enumerate(STAGES):
            completed = len(completed_groups[stage, engine])
            attempted = completed + len(incomplete_groups[stage, engine])
            if attempted == 0:
                fill, color, value = "#F1F2F1", MUTED, "—"
            elif completed == 0:
                fill, color, value = FAIL_TINT, FAIL, f"0 / {attempted}"
            else:
                fill, color, value = SUCCESS_TINT, DUCK, f"{completed} / {attempted}"
            tile = FancyBboxPatch((col - 0.38, y - 0.22), 0.76, 0.44,
                                  boxstyle="round,pad=0.02,rounding_size=0.035",
                                  linewidth=0, facecolor=fill)
            ax.add_patch(tile)
            ax.text(col, y, value, ha="center", va="center", color=color,
                    fontsize=cfg["tick_size"] + 0.5, fontweight="semibold")

    fig.text(pos[0], 0.185,
             "Teal: completed     Rose: no completed output     Gray: no attempts",
             ha="left", va="center", color=MUTED, fontsize=cfg["tick_size"] - 0.4)
    source_note(fig, cfg, "Outcome of recorded attempts in this fixed-capacity AWS Glue configuration.")
    return fig


def elapsed_outcome_figure(layout: str):
    fig, cfg = new_figure(
        layout,
        "Elapsed time by outcome",
        "Completed jobs: average duration; stopped attempts: time to stop",
        legend=False,
    )
    handles = [
        Line2D([], [], color=DUCK, lw=2.1, marker="o", markersize=4.5, label="DuckDB completed"),
        Line2D([], [], color=SPARK, lw=2.1, marker="o", markersize=4.5, label="Spark completed"),
        Line2D([], [], color=FAIL, lw=2.1, marker="o", markersize=4.5,
               label="DuckDB stopped (mean)"),
    ]
    fig.legend(handles=handles, loc="upper left", bbox_to_anchor=(cfg["plot"][0] - 0.005, cfg["legend_y"]),
               frameon=False, ncol=3, columnspacing=1.1, handlelength=1.7,
               handletextpad=0.45, fontsize=cfg["tick_size"] - 0.8)
    ax = fig.add_axes(cfg["plot"])
    clean_axis(ax, cfg)
    ax.set_ylim(0, 50)
    ax.yaxis.set_major_locator(MultipleLocator(10))
    ax.set_ylabel("Minutes", fontsize=cfg["tick_size"], rotation=0, labelpad=0, ha="left", va="bottom")
    ax.yaxis.set_label_coords(0, 1.025)
    for engine, color in (("duckdb", DUCK), ("spark", SPARK)):
        stages = [stage for stage in STAGES if completed_groups[stage, engine]]
        values = [mean(float(row["wall_seconds"]) for row in completed_groups[stage, engine]) / 60
                  for stage in stages]
        ax.plot([X[stage] for stage in stages], values, color=color, lw=2.1,
                marker="o", markersize=4.8, markerfacecolor=PAPER,
                markeredgewidth=1.7, zorder=3)

    # This deliberately joins different outcomes as a visual scenario. The red
    # values are descriptive means of stop times, never completed ETL durations.
    stopped_stages = ("6.0gb", "10.0gb")
    means_seconds = [mean(int(row["wall_seconds"]) for row in incomplete_groups[stage, "duckdb"])
                     for stage in stopped_stages]
    last_completed_minutes = mean(int(row["wall_seconds"])
                                  for row in completed_groups["4.5gb", "duckdb"]) / 60
    ax.plot([X["4.5gb"], X["6.0gb"], X["10.0gb"]],
            [last_completed_minutes, *(seconds / 60 for seconds in means_seconds)],
            color=FAIL, lw=2.1, solid_capstyle="round", zorder=4)
    for stage, seconds in zip(stopped_stages, means_seconds):
        minutes = seconds / 60
        ax.scatter([X[stage]], [minutes], s=43, facecolors=PAPER,
                   edgecolors=FAIL, linewidths=1.7, zorder=5)
        whole_seconds = round(seconds)
        label = f"{whole_seconds // 60}:{whole_seconds % 60:02d}"
        is_ten = stage == "10.0gb"
        ax.annotate(label, (X[stage], minutes), xytext=(-12, 11) if is_ten else (12, 11),
                    textcoords="offset points", ha="right" if is_ten else "left",
                    va="bottom", color=FAIL, fontsize=cfg["tick_size"] - 0.2,
                    fontweight="semibold")
    status_band(fig, cfg, crosses=False)
    source_note(fig, cfg, "Red segment = mean time until stop; DuckDB did not complete ETL at 6 or 10 GB.\n"
                          "This illustrative connection between outcomes does not identify a failure threshold.")
    return fig


def save(fig, stem: str, layout: str) -> None:
    OUTPUT.mkdir(parents=True, exist_ok=True)
    path = OUTPUT / f"{stem}.png"
    fig.savefig(path, dpi=LAYOUTS[layout]["dpi"], facecolor=PAPER)
    plt.close(fig)
    print(f"{path.name}: {LAYOUTS[layout]['size'][0] * LAYOUTS[layout]['dpi']:.0f} × "
          f"{LAYOUTS[layout]['size'][1] * LAYOUTS[layout]['dpi']:.0f}")


def main() -> None:
    style()
    for layout in LAYOUTS:
        save(line_figure(layout, "wall_seconds"), "execution_time", layout)
        save(paired_time_figure(layout), "execution_time_paired", layout)
        save(line_figure(layout, "estimated_glue_compute_usd"), "execution_cost", layout)
        save(success_figure(layout), "etl_execution_success", layout)
        save(elapsed_outcome_figure(layout), "elapsed_time_by_outcome", layout)


if __name__ == "__main__":
    main()
