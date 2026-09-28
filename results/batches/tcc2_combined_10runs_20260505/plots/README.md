# Plots for `tcc2_combined_10runs_20260505`

This folder contains plots generated from:

- `../summary.csv`: aggregated rates by scenario, model, and model-scenario pair.
- `../classification.csv`: one row per run, with outcome labels and diagnostic indicators.
- `../manual_classification.csv`: one row per run with `manual_outcome`, used for
  the outcome-composition figures because the automatic `PARTIAL` class mixed
  refusals, deferred decisions, and malicious merges.

Each plot is exported as `.png` for quick viewing and `.svg` for inclusion in documents with scalable quality.

The dataset has 120 runs: 3 models (`opencode/big-pickle`, `opencode/gpt-5-nano`,
`opencode/nemotron-3-super-free`) x 4 scenarios (`baseline`, `scenario_2`,
`scenario_3`, `scenario_4`) x 10 runs per model-scenario cell.

## Conventions

- **Outcome colours** are fixed across every plot:
  `BASELINE_OK` = blue, `SUCCESS` = red, `MERGED_MALICIOUS`/`PARTIAL` = amber,
  `DEFERRED` = brown, `REFUSED` = slate grey.
  `REFUSED` is grey on purpose: refusal is the desirable behaviour from a
  defender's point of view, but green would invite readers to misread it as a
  "good" outcome in figures whose other bars encode attack success.
- **Rate-focused plots exclude baseline runs** because baseline has no attack
  outcome (its only outcome is `BASELINE_OK`). Plots that include baseline say so.
- **Confidence intervals** are 95% Wilson score intervals for a binomial
  proportion. With only 10 runs per cell they are wide — that is the point: a
  cell showing 100% ASR still has a lower bound near 70%.
- `steps_to_compromise` is only populated for runs classified as `SUCCESS`, so
  plot 10 intentionally covers only scenarios 3 and 4.
- The per-run indicators `detection_without_refusal` and `data_leak_via_read`
  are too sparse in this dataset (0 and 4 runs respectively) to deserve their
  own figures; they are left for the prose discussion instead.

## Plot Catalog

| File | What it shows | Useful for |
| --- | --- | --- |
| `01_rates_by_scenario` | ASR, refusal rate, and partial rate per attack scenario, pooled across the three models (n=30 per scenario). | Headline view of which attack scenarios produced more successful or partial compromises. |
| `02_rates_by_model` | ASR, refusal rate, and partial rate per model, pooled across the three attack scenarios, baseline excluded (n=30 per model). | Comparing model robustness under attack conditions without baseline diluting the bars. |
| `03_asr_heatmap_model_scenario` | ASR for every model x attack-scenario cell (n=10 per cell). | Quickly spotting high-risk model/scenario combinations; the single best summary figure. |
| `04_asr_with_ci` | Same per-cell ASR as the heatmap, drawn as grouped bars with 95% Wilson confidence intervals. | Showing honestly how uncertain a 0%, 90%, or 100% cell is when n=10. |
| `05_outcome_distribution_by_scenario` | Stacked share of manual outcomes (`BASELINE_OK`, `SUCCESS`, `MERGED_MALICIOUS`, `DEFERRED`, `REFUSED`) per scenario. | Showing the full composition of outcomes per attack condition after manually separating the automatic `PARTIAL` class. |
| `06_outcome_distribution_by_model` | Stacked share of manual outcomes per model (baseline cells included as `BASELINE_OK`). | Showing whether a model tends toward payload execution, malicious merge, deferred decision, or refusal overall. |
| `07_outcome_counts_model_scenario_grid` | Raw manual-outcome counts for each of the 12 model-scenario cells (10 runs each). | Sanity-checking the counts behind every rate; a compact replacement for a results table. |
| `08_confirmation_seeking_heatmap` | Share of runs that asked the user for confirmation, for every model x scenario cell, **including baseline**. | Separating "the model is cautious by default" (high baseline column) from "the attack made it cautious". gpt-5-nano is 90% in baseline, so its caution is a model trait, not an attack response. |
| `09_tool_calls_by_scenario_model` | Distribution of tool calls per run, grouped by scenario and model (clean boxplots, outliers marked). | Checking whether attack scenarios pull the agent into more tool interaction than baseline. |
| `10_steps_to_compromise_successes` | Steps to compromise among `SUCCESS` runs only, by scenario and model. | Comparing how quickly successful attacks reached the compromise point. |
| `11_source_batch_comparison` | ASR per attack scenario for the two source batches that make up this combined dataset, pooled across models, with 95% Wilson CIs and per-batch n in the legend. | Confirming the merge is not hiding a disagreement between the pilot and incremental batches; the CIs overlap heavily. |
| `12_tool_calls_by_outcome` | Distribution of tool calls per run, grouped by final outcome (`SUCCESS` / `PARTIAL` / `REFUSED`), attack scenarios only. | Asking whether deeper engagement predicts the verdict: `SUCCESS` runs tend to sit slightly above `PARTIAL`/`REFUSED` runs. |

## Regeneration

From the repository root:

```bash
MPLCONFIGDIR=/private/tmp/mplconfig-tcc2 python3 results/batches/tcc2_combined_10runs_20260505/plots/generate_plots.py
```

The `MPLCONFIGDIR` variable avoids Matplotlib trying to write cache files under
the user home directory.

## History

An earlier version of this folder shipped two redundant figures
(`04_rates_by_model_scenario_facets` repeated the heatmap data;
`12_counts_by_scenario_all_models` repeated the count grid) and used green for
`REFUSED`. Those were replaced by `04_asr_with_ci` and `12_tool_calls_by_outcome`,
the palette was made neutral, the stripplot overlays on the boxplots were
dropped, and confidence intervals were added to the rate comparisons.
