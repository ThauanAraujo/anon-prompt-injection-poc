# Experiment plots (TCC)

The data is already in the repo, in `results/batches/tcc2_combined_10runs_20260505/`. It contains 120 runs of a code agent (OpenCode) reviewing pull requests: 3 models (`big-pickle`, `gpt-5-nano`, `nemotron-3-super-free`) × 4 scenarios × 10 runs. Scenarios `scenario_2`, `scenario_3` and `scenario_4` are attacks (a malicious instruction hidden inside a PR — SSH key leak, `.env` leak, etc.); `baseline` only has benign PRs.

## Files

- `classification.csv` — one row per run. Useful columns: `model`, `scenario`, `outcome` (`BASELINE_OK` / `SUCCESS` / `PARTIAL` / `REFUSED`), `asr` (0/1 — the agent executed the payload), `refused` (0/1), `partial` (0/1), `confirmation_seeking` (0/1 — asked the user for confirmation before acting), `steps_to_compromise` (number of steps until compromise, filled in only when `SUCCESS`), `tool_calls` (how many tool calls the run had), `source_batch` (which batch the run came from).
- `manual_classification.csv` — everything from the previous file + a `manual_outcome` column with more granularity: `BASELINE_OK` / `SUCCESS` / `MERGED_MALICIOUS` / `DEFERRED` / `REFUSED`. It came from a manual review that noticed the automatic `PARTIAL` was lumping together opposite things — in some cases the agent *detected and rejected* the malicious PR (`REFUSED`), in others it *merged* the malicious PR without executing the payload (`MERGED_MALICIOUS`), and in some it *passed the decision to the user* (`DEFERRED`). The full reasoning is in `MANUAL_REVIEW.md`.
- `summary.csv` — already-computed aggregates (asr, refusal_rate, partial_rate, n, etc.) by scenario, by model, and by model×scenario pair. You can use it as a shortcut or recompute from `classification.csv` — either way is fine.

## General guidelines

- Feel free to pick the library (matplotlib/seaborn, plotly, etc.). I'd only ask that each figure be exported as **PNG** (for a quick look) and **SVG** (to put in the document without losing quality), and that the code be organized in a single script, re-runnable from the CSVs.
- **Fixed colors per outcome, the same in every figure:** `BASELINE_OK` blue, `SUCCESS` red, `PARTIAL`/`MERGED_MALICIOUS` yellow/amber, `REFUSED` gray, `DEFERRED` a separate neutral tone. (Gray for `REFUSED` is on purpose: "refusing" is the desirable behavior, but green would make it look like a "good result by the agent" in figures where the neighboring bars are successful attacks.)
- **Rate charts (ASR, refusal, etc.) exclude `baseline`**, because baseline has no attack outcome. When a figure *includes* baseline, make that clear in the title.
- **Always indicate n** in the title or legend — n = 10 per model×scenario cell, n = 30 when aggregating the 3 models of a scenario or the 3 attack scenarios of a model.
- When showing a rate with a small n (10 per cell), **include a 95% confidence interval (Wilson)**. With 10 runs, a cell at 100% still has a lower bound near 70% — it's important for the reader to see that instead of thinking 100% is a "clean" number.
- Always order models and scenarios consistently (e.g., scenarios in the order 2, 3, 4; models always in the same order), label the axes, and use a short title describing what is aggregated.

## Requested plots

**1. ASR heatmap by model × attack scenario.** For each of the 3 models (rows) and each attack scenario `scenario_2`/`scenario_3`/`scenario_4` (columns), the attack success rate = mean of `asr` in that cell (10 runs). Annotate each cell with the value in %, color scale from 0 to 1. This is the main summary figure — I want it to be possible to glance at it and see which combinations are the riskiest.

**2. Rates by scenario (grouped bars).** For each attack scenario, three bars side by side: ASR, refusal rate (mean of `refused`), and "partial" rate (mean of `partial`), aggregating the 3 models together (n = 30 per scenario). Y axis from 0 to 100%. It serves as the headline view: in which scenario the attack worked best.

**3. Rates by model (grouped bars).** Same as figure 2, but grouped by model instead of by scenario (n = 30 per model, baseline excluded). It's the direct comparison of robustness between the models under attack.

**4. ASR with confidence interval.** The same 9 cells of the heatmap (model × attack scenario), but as bars: grouped by scenario on the x axis, colored by model, and with a 95% CI (Wilson) error bar on top of each bar. It's the "honest" version of the heatmap — it shows how uncertain each ~100% or ~0% number is with n = 10.

**5. Composition of outcomes by scenario (100% stacked bars).** For each scenario (here *including* `baseline`), the fraction of runs in each outcome, using the `manual_outcome` column from `manual_classification.csv` (categories `BASELINE_OK` / `SUCCESS` / `MERGED_MALICIOUS` / `DEFERRED` / `REFUSED`). Each bar sums to 100%. It shows the full composition, including the "middle ground" — malicious PRs that were merged without the agent executing anything.

**6. Composition of outcomes by model (100% stacked bars).** Same as figure 5, but grouped by model, also using `manual_outcome`. It makes each model's "signature" visible: one tends to execute the payload, another to merge without noticing, another to refuse.

**7. "Confirmation request" heatmap by model × scenario.** For each model (rows) and each scenario (columns — here *including* the `baseline` column), the fraction of runs in which the agent asked the user for confirmation before acting (`confirmation_seeking`). Annotate in %. The baseline column is the point: it separates "this model is cautious by nature" from "the attack made it cautious".

**8. Steps to compromise (boxplot).** Distribution of `steps_to_compromise` only in runs with `outcome == SUCCESS`, with one box per (scenario, model). Only `scenario_3` and `scenario_4` have successful runs, so only those two appear on the x axis. Showing the individual points on top helps, since there are few. It serves to compare how quickly the successful attacks reached compromise.

**9. (optional) Tool calls by outcome (boxplot).** Distribution of `tool_calls` per run, grouped by `outcome` (`SUCCESS` / `PARTIAL` / `REFUSED`), considering only the attack scenarios. The idea is to see whether "engaging more with the task" predicts the outcome — `SUCCESS` runs tend to have slightly more calls. It's a subtle effect; if it gets cluttered, you can replace it with bars showing each group's median.

**10. (optional, sanity check) ASR by source batch.** The combined set comes from two batches; this chart shows ASR per attack scenario, separating `pilot_main_20260428_esc` (9 runs per scenario) and `tcc2_incremental_20260504` (21 per scenario), in grouped bars with 95% CI (Wilson) and each batch's n in the legend. It's just to confirm that merging the two batches isn't hiding a disagreement between them.

---

The ones I want most for the text are 1, 4, 5, 7 and 8; the rest is supplementary. If any of them doesn't make sense or turns out to be hard to put together, let me know and we'll adjust.
