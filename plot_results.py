
from __future__ import annotations

import argparse
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import pandas as pd


ROOT = Path(__file__).resolve().parent
DEFAULT_INPUT = ROOT / "results" / "batches" / "tcc2_combined_10runs_20260505" / "manual_classification.csv"
DEFAULT_OUTPUT = ROOT / "results" / "batches" / "tcc2_combined_10runs_20260505" / "plots"
DEFAULT_THESIS_OUTPUT = ROOT.parent / "tcc2" / "figuras" / "resultados"

OUTCOME_ORDER = ["BASELINE_OK", "SUCCESS", "MERGED_MALICIOUS", "DEFERRED", "REFUSED"]
OUTCOME_LABELS = {
    "BASELINE_OK": "Baseline OK",
    "SUCCESS": "Execucao direta",
    "MERGED_MALICIOUS": "Merge malicioso",
    "DEFERRED": "Adiado",
    "REFUSED": "Recusa",
}
OUTCOME_COLORS = {
    "BASELINE_OK": "#4C78A8",
    "SUCCESS": "#D62728",
    "MERGED_MALICIOUS": "#F2B134",
    "DEFERRED": "#7F7F7F",
    "REFUSED": "#BDBDBD",
}

SCENARIO_ORDER = ["baseline", "scenario_2", "scenario_3", "scenario_4"]
SCENARIO_LABELS = {
    "baseline": "baseline\nn=30",
    "scenario_2": "scenario_2\nn=30",
    "scenario_3": "scenario_3\nn=30",
    "scenario_4": "scenario_4\nn=30",
}
MODEL_ORDER = [
    "opencode/big-pickle",
    "opencode/gpt-5-nano",
    "opencode/nemotron-3-super-free",
]
MODEL_LABELS = {
    "opencode/big-pickle": "big-pickle\nn=40",
    "opencode/gpt-5-nano": "gpt-5-nano\nn=40",
    "opencode/nemotron-3-super-free": "nemotron-3-super-free\nn=40",
}


def grouped_counts(df: pd.DataFrame, group_col: str, group_order: list[str]) -> pd.DataFrame:
    counts = (
        df.groupby([group_col, "manual_outcome"])
        .size()
        .unstack(fill_value=0)
        .reindex(index=group_order, columns=OUTCOME_ORDER, fill_value=0)
    )
    return counts


def plot_stacked_percent(
    counts: pd.DataFrame,
    labels: dict[str, str],
    title: str,
    output_base: Path,
) -> None:
    totals = counts.sum(axis=1)
    percentages = counts.div(totals, axis=0).fillna(0)

    fig, ax = plt.subplots(figsize=(10.4, 5.6))
    bottom = pd.Series(0.0, index=percentages.index)

    for outcome in OUTCOME_ORDER:
        values = percentages[outcome]
        bars = ax.bar(
            range(len(percentages.index)),
            values,
            bottom=bottom,
            color=OUTCOME_COLORS[outcome],
            edgecolor="white",
            linewidth=0.8,
            label=OUTCOME_LABELS[outcome],
        )
        for idx, bar in enumerate(bars):
            value = float(values.iloc[idx])
            count = int(counts[outcome].iloc[idx])
            if value >= 0.08 and count > 0:
                ax.text(
                    bar.get_x() + bar.get_width() / 2,
                    bottom.iloc[idx] + value / 2,
                    f"{count}\n{value:.0%}",
                    ha="center",
                    va="center",
                    fontsize=9,
                    color="#1f1f1f",
                )
        bottom += values

    ax.set_title(title, fontsize=13, pad=12)
    ax.set_ylabel("Proporcao das execucoes")
    ax.set_ylim(0, 1)
    ax.set_yticks([0, 0.25, 0.5, 0.75, 1.0])
    ax.set_yticklabels(["0%", "25%", "50%", "75%", "100%"])
    ax.set_xticks(range(len(percentages.index)))
    ax.set_xticklabels([labels.get(item, item) for item in percentages.index])
    ax.grid(axis="y", color="#E6E6E6", linewidth=0.8)
    ax.set_axisbelow(True)
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    ax.legend(
        loc="upper center",
        bbox_to_anchor=(0.5, -0.14),
        ncol=3,
        frameon=False,
    )
    fig.tight_layout(rect=(0, 0.05, 1, 1))

    output_base.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(output_base.with_suffix(".png"), dpi=220)
    fig.savefig(output_base.with_suffix(".svg"))
    plt.close(fig)


def generate(input_csv: Path, output_dirs: list[Path]) -> None:
    df = pd.read_csv(input_csv)
    required = {"scenario", "model", "manual_outcome"}
    missing = required - set(df.columns)
    if missing:
        raise ValueError(f"Missing required columns in {input_csv}: {sorted(missing)}")

    scenario_counts = grouped_counts(df, "scenario", SCENARIO_ORDER)
    model_counts = grouped_counts(df, "model", MODEL_ORDER)

    for output_dir in output_dirs:
        plot_stacked_percent(
            scenario_counts,
            SCENARIO_LABELS,
            "Composicao dos desfechos por cenario",
            output_dir / "desfechos-por-cenario",
        )
        plot_stacked_percent(
            model_counts,
            MODEL_LABELS,
            "Composicao dos desfechos por modelo",
            output_dir / "desfechos-por-modelo",
        )


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=Path, default=DEFAULT_INPUT, help="manual_classification.csv path")
    parser.add_argument(
        "--output-dir",
        type=Path,
        action="append",
        help="Directory to receive PNG and SVG files. Can be passed more than once.",
    )
    parser.add_argument(
        "--skip-thesis-output",
        action="store_true",
        help="Only write to --output-dir/default batch plots directory, not tcc2/figuras/resultados.",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    output_dirs = args.output_dir or [DEFAULT_OUTPUT]
    if not args.skip_thesis_output and DEFAULT_THESIS_OUTPUT not in output_dirs:
        output_dirs.append(DEFAULT_THESIS_OUTPUT)
    generate(args.input, output_dirs)


if __name__ == "__main__":
    main()
