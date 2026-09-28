from __future__ import annotations

import os
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import seaborn as sns


BASE = Path(__file__).resolve().parents[1]
OUT = Path(__file__).resolve().parent

SUMMARY = pd.read_csv(BASE / "summary.csv")
RUNS = pd.read_csv(BASE / "classification.csv")
MANUAL_RUNS = pd.read_csv(BASE / "manual_classification.csv")

MODEL_ORDER = [
    "opencode/big-pickle",
    "opencode/gpt-5-nano",
    "opencode/nemotron-3-super-free",
]
SCENARIO_ORDER = ["baseline", "scenario_2", "scenario_3", "scenario_4"]
ATTACK_SCENARIO_ORDER = ["scenario_2", "scenario_3", "scenario_4"]
OUTCOME_ORDER = ["BASELINE_OK", "SUCCESS", "PARTIAL", "REFUSED"]
ATTACK_OUTCOME_ORDER = ["SUCCESS", "PARTIAL", "REFUSED"]
MANUAL_OUTCOME_ORDER = ["BASELINE_OK", "SUCCESS", "MERGED_MALICIOUS", "DEFERRED", "REFUSED"]

MODEL_LABELS = {
    "opencode/big-pickle": "big-pickle",
    "opencode/gpt-5-nano": "gpt-5-nano",
    "opencode/nemotron-3-super-free": "nemotron-3-super",
}
SCENARIO_LABELS = {
    "baseline": "Baseline",
    "scenario_2": "Scenario 2",
    "scenario_3": "Scenario 3",
    "scenario_4": "Scenario 4",
}

PALETTE = {
    "BASELINE_OK": "#4c78a8",
    "SUCCESS": "#e45756",
    "PARTIAL": "#f2b701",
    "MERGED_MALICIOUS": "#f2b701",
    "DEFERRED": "#9d755d",
    "REFUSED": "#7f7f7f",
}

METRIC_LABELS = {"asr": "ASR", "refusal_rate": "Refusal", "partial_rate": "Partial"}


def setup() -> None:
    os.environ.setdefault("MPLCONFIGDIR", str(OUT / ".mplconfig"))
    sns.set_theme(
        style="whitegrid",
        context="paper",
        font="DejaVu Sans",
        rc={
            "figure.dpi": 160,
            "savefig.dpi": 220,
            "axes.titlesize": 12,
            "axes.labelsize": 10,
            "xtick.labelsize": 9,
            "ytick.labelsize": 9,
            "legend.fontsize": 9,
            "axes.spines.top": False,
            "axes.spines.right": False,
        },
    )


def save(fig: plt.Figure, name: str) -> None:
    fig.tight_layout()
    fig.savefig(OUT / f"{name}.png", bbox_inches="tight")
    fig.savefig(OUT / f"{name}.svg", bbox_inches="tight")
    plt.close(fig)


def pct_axis(ax: plt.Axes) -> None:
    ax.set_ylim(0, 1.05)
    ax.set_yticks(np.linspace(0, 1, 6))
    ax.set_yticklabels([f"{int(v * 100)}%" for v in np.linspace(0, 1, 6)])


def annotate_bars(ax: plt.Axes, pct: bool = True) -> None:
    for container in ax.containers:
        for bar in container:
            h = bar.get_height()
            if np.isnan(h) or h <= 0:
                continue
            label = f"{h:.0%}" if pct else f"{h:.0f}"
            ax.annotate(
                label,
                (bar.get_x() + bar.get_width() / 2, h),
                ha="center",
                va="bottom",
                fontsize=8,
                xytext=(0, 2),
                textcoords="offset points",
            )


def wilson_ci(k: int, n: int, z: float = 1.96) -> tuple[float, float]:
    if n == 0:
        return 0.0, 0.0
    p = k / n
    denom = 1 + z * z / n
    center = (p + z * z / (2 * n)) / denom
    margin = z * np.sqrt((p * (1 - p) + z * z / (4 * n)) / n) / denom
    return max(0.0, center - margin), min(1.0, center + margin)


def plot_scenario_rates() -> None:
    data = SUMMARY[
        SUMMARY["group_type"].eq("scenario") & SUMMARY["scenario"].isin(ATTACK_SCENARIO_ORDER)
    ].copy()
    data["scenario_label"] = data["scenario"].map(SCENARIO_LABELS)
    long = data.melt(
        id_vars=["scenario", "scenario_label"],
        value_vars=["asr", "refusal_rate", "partial_rate"],
        var_name="metric",
        value_name="rate",
    )
    long["metric"] = long["metric"].map(METRIC_LABELS)

    fig, ax = plt.subplots(figsize=(8.6, 4.4))
    sns.barplot(data=long, x="scenario_label", y="rate", hue="metric", ax=ax)
    pct_axis(ax)
    annotate_bars(ax)
    ax.set_title("Rates by scenario (pooled across models, n=30 per scenario)")
    ax.set_xlabel("")
    ax.set_ylabel("Rate")
    ax.legend(title="")
    save(fig, "01_rates_by_scenario")


def plot_model_rates() -> None:
    data = (
        RUNS[RUNS["scenario"].ne("baseline")]
        .groupby("model", as_index=False)
        .agg(
            n=("run_id", "count"),
            asr=("asr", "mean"),
            refusal_rate=("refused", "mean"),
            partial_rate=("partial", "mean"),
        )
    )
    data["model_label"] = data["model"].map(MODEL_LABELS)
    long = data.melt(
        id_vars=["model", "model_label"],
        value_vars=["asr", "refusal_rate", "partial_rate"],
        var_name="metric",
        value_name="rate",
    )
    long["metric"] = long["metric"].map(METRIC_LABELS)

    fig, ax = plt.subplots(figsize=(8.6, 4.4))
    sns.barplot(data=long, x="model_label", y="rate", hue="metric", ax=ax)
    pct_axis(ax)
    annotate_bars(ax)
    ax.set_title("Attack-scenario rates by model (baseline excluded, n=30 per model)")
    ax.set_xlabel("")
    ax.set_ylabel("Rate")
    ax.legend(title="")
    save(fig, "02_rates_by_model")


def plot_asr_heatmap() -> None:
    data = SUMMARY[SUMMARY["group_type"].eq("model_scenario")].copy()
    matrix = (
        data.pivot(index="model", columns="scenario", values="asr")
        .reindex(index=MODEL_ORDER, columns=ATTACK_SCENARIO_ORDER)
        .rename(index=MODEL_LABELS, columns=SCENARIO_LABELS)
    )
    fig, ax = plt.subplots(figsize=(7.8, 3.8))
    sns.heatmap(
        matrix,
        vmin=0,
        vmax=1,
        cmap="YlOrRd",
        annot=True,
        fmt=".0%",
        linewidths=0.7,
        linecolor="white",
        cbar_kws={"label": "ASR"},
        ax=ax,
    )
    ax.set_title("ASR heatmap by model and attack scenario (n=10 per cell)")
    ax.set_xlabel("")
    ax.set_ylabel("")
    save(fig, "03_asr_heatmap_model_scenario")


def plot_asr_with_ci() -> None:
    cells = (
        RUNS[RUNS["scenario"].isin(ATTACK_SCENARIO_ORDER)]
        .groupby(["model", "scenario"], as_index=False)
        .agg(successes=("asr", "sum"), n=("run_id", "count"))
    )
    ci = cells.apply(lambda r: wilson_ci(int(r["successes"]), int(r["n"])), axis=1)
    cells["asr"] = cells["successes"] / cells["n"]
    cells["lo"] = [c[0] for c in ci]
    cells["hi"] = [c[1] for c in ci]
    cells["model_label"] = cells["model"].map(MODEL_LABELS)
    cells["scenario_label"] = cells["scenario"].map(SCENARIO_LABELS)

    fig, ax = plt.subplots(figsize=(8.8, 4.6))
    scenarios = [SCENARIO_LABELS[s] for s in ATTACK_SCENARIO_ORDER]
    models = [MODEL_LABELS[m] for m in MODEL_ORDER]
    x = np.arange(len(scenarios))
    width = 0.26
    colors = sns.color_palette("deep", n_colors=len(models))

    for i, model in enumerate(models):
        sub = cells[cells["model_label"] == model].set_index("scenario_label").reindex(scenarios)
        heights = sub["asr"].to_numpy()
        lows = sub["lo"].to_numpy()
        highs = sub["hi"].to_numpy()
        err_lo = np.clip(heights - lows, 0, None)
        err_hi = np.clip(highs - heights, 0, None)
        bars = ax.bar(
            x + (i - 1) * width,
            heights,
            width=width,
            color=colors[i],
            label=model,
            edgecolor="white",
        )
        ax.errorbar(
            x + (i - 1) * width,
            heights,
            yerr=[err_lo, err_hi],
            fmt="none",
            ecolor="black",
            elinewidth=1,
            capsize=3,
        )
        for bar, h in zip(bars, heights):
            ax.annotate(
                f"{h:.0%}",
                (bar.get_x() + bar.get_width() / 2, h),
                ha="center",
                va="bottom",
                fontsize=8,
                xytext=(0, 4),
                textcoords="offset points",
            )

    ax.set_xticks(x)
    ax.set_xticklabels(scenarios)
    pct_axis(ax)
    ax.set_ylabel("ASR (95% Wilson CI)")
    ax.set_xlabel("")
    ax.set_title("ASR with 95% Wilson confidence intervals (n=10 per cell)")
    ax.legend(title="Model", loc="upper left", bbox_to_anchor=(1.01, 1))
    save(fig, "04_asr_with_ci")


def stacked_bar(
    data: pd.DataFrame,
    index_col: str,
    outcome_col: str,
    outcome_order: list[str],
    name: str,
    title: str,
) -> None:
    counts = (
        data.groupby([index_col, outcome_col])
        .size()
        .unstack(fill_value=0)
        .reindex(columns=outcome_order, fill_value=0)
    )
    props = counts.div(counts.sum(axis=1), axis=0)

    fig, ax = plt.subplots(figsize=(8.5, 4.4))
    bottom = np.zeros(len(props))
    x = np.arange(len(props))
    for outcome in outcome_order:
        vals = props[outcome].to_numpy()
        ax.bar(x, vals, bottom=bottom, label=outcome, color=PALETTE[outcome])
        bottom += vals
    ax.set_xticks(x)
    ax.set_xticklabels(props.index, rotation=25, ha="right")
    pct_axis(ax)
    ax.set_title(title)
    ax.set_ylabel("Share of runs")
    ax.legend(title="Outcome", loc="upper left", bbox_to_anchor=(1.01, 1))
    save(fig, name)


def plot_outcome_distributions() -> None:
    data = MANUAL_RUNS.copy()
    data["scenario_label"] = data["scenario"].map(SCENARIO_LABELS)
    data["model_label"] = data["model"].map(MODEL_LABELS)
    stacked_bar(
        data,
        "scenario_label",
        "manual_outcome",
        MANUAL_OUTCOME_ORDER,
        "05_outcome_distribution_by_scenario",
        "Manual outcome distribution by scenario",
    )
    stacked_bar(
        data,
        "model_label",
        "manual_outcome",
        MANUAL_OUTCOME_ORDER,
        "06_outcome_distribution_by_model",
        "Manual outcome distribution by model",
    )


def plot_outcome_grid_counts() -> None:
    data = MANUAL_RUNS.copy()
    data["model_label"] = data["model"].map(MODEL_LABELS)
    data["scenario_label"] = data["scenario"].map(SCENARIO_LABELS)

    grid = sns.catplot(
        data=data,
        x="manual_outcome",
        hue="manual_outcome",
        col="scenario_label",
        row="model_label",
        kind="count",
        order=MANUAL_OUTCOME_ORDER,
        hue_order=MANUAL_OUTCOME_ORDER,
        palette=PALETTE,
        legend=False,
        height=2.4,
        aspect=1.15,
        sharey=True,
    )
    for ax in grid.axes.flat:
        ax.tick_params(axis="x", rotation=35)
        ax.set_xlabel("")
    grid.set_ylabels("Runs")
    grid.set_titles(row_template="{row_name}", col_template="{col_name}")
    grid.fig.suptitle("Outcome counts for each model-scenario cell", y=1.02)
    save(grid.fig, "07_outcome_counts_model_scenario_grid")


def plot_confirmation_heatmap() -> None:
    data = (
        RUNS.groupby(["model", "scenario"], as_index=False)["confirmation_seeking"].mean()
    )
    matrix = (
        data.pivot(index="model", columns="scenario", values="confirmation_seeking")
        .reindex(index=MODEL_ORDER, columns=SCENARIO_ORDER)
        .rename(index=MODEL_LABELS, columns=SCENARIO_LABELS)
    )
    fig, ax = plt.subplots(figsize=(8.4, 3.8))
    sns.heatmap(
        matrix,
        vmin=0,
        vmax=1,
        cmap="Blues",
        annot=True,
        fmt=".0%",
        linewidths=0.7,
        linecolor="white",
        cbar_kws={"label": "Share with confirmation seeking"},
        ax=ax,
    )
    ax.set_title(
        "Confirmation seeking by model and scenario\n"
        "(baseline included to expose model trait vs. attack-driven behaviour)"
    )
    ax.set_xlabel("")
    ax.set_ylabel("")
    save(fig, "08_confirmation_seeking_heatmap")


def plot_tool_calls() -> None:
    data = RUNS.copy()
    data["model_label"] = data["model"].map(MODEL_LABELS)
    data["scenario_label"] = data["scenario"].map(SCENARIO_LABELS)

    fig, ax = plt.subplots(figsize=(8.8, 4.5))
    sns.boxplot(
        data=data,
        x="scenario_label",
        y="tool_calls",
        hue="model_label",
        ax=ax,
        fliersize=3,
        linewidth=1,
    )
    ax.legend(title="Model", loc="upper left", bbox_to_anchor=(1.01, 1))
    ax.set_title("Tool calls per run by scenario and model")
    ax.set_xlabel("")
    ax.set_ylabel("Tool calls")
    save(fig, "09_tool_calls_by_scenario_model")


def plot_steps_to_compromise() -> None:
    data = RUNS[RUNS["steps_to_compromise"].notna()].copy()
    data["model_label"] = data["model"].map(MODEL_LABELS)
    data["scenario_label"] = data["scenario"].map(SCENARIO_LABELS)

    fig, ax = plt.subplots(figsize=(8.8, 4.5))
    sns.boxplot(
        data=data,
        x="scenario_label",
        y="steps_to_compromise",
        hue="model_label",
        ax=ax,
        fliersize=3,
        linewidth=1,
    )
    ax.legend(title="Model", loc="upper left", bbox_to_anchor=(1.01, 1))
    ax.set_title("Steps to compromise among successful attacks")
    ax.set_xlabel("")
    ax.set_ylabel("Steps to compromise")
    save(fig, "10_steps_to_compromise_successes")


def plot_batch_comparison() -> None:
    data = RUNS[RUNS["scenario"].isin(ATTACK_SCENARIO_ORDER)].copy()
    grouped = (
        data.groupby(["source_batch", "scenario"], as_index=False)
        .agg(successes=("asr", "sum"), n=("run_id", "count"))
    )
    ci = grouped.apply(lambda r: wilson_ci(int(r["successes"]), int(r["n"])), axis=1)
    grouped["asr"] = grouped["successes"] / grouped["n"]
    grouped["lo"] = [c[0] for c in ci]
    grouped["hi"] = [c[1] for c in ci]
    grouped["scenario_label"] = grouped["scenario"].map(SCENARIO_LABELS)
    grouped["batch_label"] = grouped["source_batch"] + " (n=" + grouped["n"].astype(str) + ")"

    batches = sorted(grouped["source_batch"].unique())
    scenarios = [SCENARIO_LABELS[s] for s in ATTACK_SCENARIO_ORDER]
    x = np.arange(len(scenarios))
    width = 0.38
    colors = sns.color_palette("deep", n_colors=len(batches))

    fig, ax = plt.subplots(figsize=(8.8, 4.6))
    for i, batch in enumerate(batches):
        sub = (
            grouped[grouped["source_batch"] == batch]
            .set_index("scenario_label")
            .reindex(scenarios)
        )
        heights = sub["asr"].to_numpy()
        lows = sub["lo"].to_numpy()
        highs = sub["hi"].to_numpy()
        err_lo = np.clip(heights - lows, 0, None)
        err_hi = np.clip(highs - heights, 0, None)
        label = sub["batch_label"].dropna().iloc[0]
        bars = ax.bar(
            x + (i - 0.5) * width,
            heights,
            width=width,
            color=colors[i],
            label=label,
            edgecolor="white",
        )
        ax.errorbar(
            x + (i - 0.5) * width,
            heights,
            yerr=[err_lo, err_hi],
            fmt="none",
            ecolor="black",
            elinewidth=1,
            capsize=3,
        )
        for bar, h in zip(bars, heights):
            ax.annotate(
                f"{h:.0%}",
                (bar.get_x() + bar.get_width() / 2, h),
                ha="center",
                va="bottom",
                fontsize=8,
                xytext=(0, 4),
                textcoords="offset points",
            )
    ax.set_xticks(x)
    ax.set_xticklabels(scenarios)
    pct_axis(ax)
    ax.set_ylabel("ASR (95% Wilson CI)")
    ax.set_xlabel("")
    ax.set_title("ASR by source batch (pooled across models, 95% Wilson CI)")
    ax.legend(title="Source batch", loc="upper left", bbox_to_anchor=(1.01, 1))
    save(fig, "11_source_batch_comparison")


def plot_tool_calls_by_outcome() -> None:
    data = RUNS[RUNS["outcome"].isin(ATTACK_OUTCOME_ORDER)].copy()
    data["scenario_label"] = data["scenario"].map(SCENARIO_LABELS)

    fig, ax = plt.subplots(figsize=(8.8, 4.5))
    sns.boxplot(
        data=data,
        x="scenario_label",
        y="tool_calls",
        hue="outcome",
        order=[SCENARIO_LABELS[s] for s in ATTACK_SCENARIO_ORDER],
        hue_order=ATTACK_OUTCOME_ORDER,
        palette=PALETTE,
        ax=ax,
        fliersize=3,
        linewidth=1,
    )
    ax.legend(title="Outcome", loc="upper left", bbox_to_anchor=(1.01, 1))
    ax.set_title(
        "Tool calls per run by outcome (attack scenarios only)\n"
        "How much the agent engaged before each verdict"
    )
    ax.set_xlabel("")
    ax.set_ylabel("Tool calls")
    save(fig, "12_tool_calls_by_outcome")


def main() -> None:
    setup()
    plot_scenario_rates()
    plot_model_rates()
    plot_asr_heatmap()
    plot_asr_with_ci()
    plot_outcome_distributions()
    plot_outcome_grid_counts()
    plot_confirmation_heatmap()
    plot_tool_calls()
    plot_steps_to_compromise()
    plot_batch_comparison()
    plot_tool_calls_by_outcome()


if __name__ == "__main__":
    main()
