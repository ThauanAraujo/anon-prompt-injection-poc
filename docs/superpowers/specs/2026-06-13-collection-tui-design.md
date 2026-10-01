# Design: Incremental Collection TUI (Coleta TUI)

Date: 2026-06-13
Repository: `poc/` (`tcc-prompt-injection-mcp`)

## Context and goal

The indirect prompt injection experiment needs to be expanded from 10 to
**30 runs per cell** (model × scenario). Collection is limited by the **daily
quota of OpenCode's free models**, so it has to be done **little by little** 
and **by more than one person** (XXXX-1, XXXX-1, XXXX-1), with the data 
accumulating over several days.

Two of the three original models (`gpt-5-nano`, `nemotron-3-super-free`)
disappeared from OpenCode's roster; collection will be redone from scratch with
a new roster: `big-pickle`, `nemotron-3-ultra-free`, `deepseek-v4-flash-free`.

This TUI gives each collaborator a single interface to: choose what to run, see
how much has already been collected (toward the goal of 30), and follow the
execution live — without having to memorize command-line flags.

### Decisions already locked (brainstorming)

- **Framework**: Textual (everyone is on a Unix-like environment: macOS, WSL,
  Linux).
- **Git**: outside the TUI. Synchronization (`pull`/`commit`/`push`) is manual,
  guided by a separate `COLLECTION.md`.
- **Counting**: goal of 30 per cell, counting **only valid runs** (discards
  quota errors/timeouts), aggregating all local batches.
- **Integration approach**: A — the TUI imports the runner and orchestrates the
  loop, receiving a callback per trial. Validated by a spike (dry-run + 1 real
  trial with `nemotron-3-ultra-free`: status OK, 27-line JSONL, 0 errors, real
  tool-calling via MCP).

## Architecture

Four units, each with an isolated responsibility:

### 1. `coleta_config.py` — single source of truth

Defines what all components need to share:

- `MODELOS`: list of the active aliases (`opencode/big-pickle`,
  `opencode/nemotron-3-ultra-free`, `opencode/deepseek-v4-flash-free`).
- `CENARIOS`: `["baseline", "scenario_2", "scenario_3", "scenario_4"]`.
- `ROTULOS_CENARIO`: friendly labels (`baseline` → "Controle benigno" (benign
  control), `scenario_2` → "Ataque explícito" (explicit attack), `scenario_3` →
  "Ataque dissimulado 1" (disguised attack 1), `scenario_4` → "Ataque
  dissimulado 2" (disguised attack 2)).
- `ROTULOS_MODELO`: short names for display.
- `META_POR_CELULA = 30`.

Imported by `run_experiments`, `coleta_status` and `coleta_tui` (all in `poc/`),
eliminating duplicated/divergent lists. `gerar_figuras_artigo.py` lives in the
`tcc2/` repo (separate) and cannot import this module; its model list is kept
manually aligned with the new roster.

### 2. `coleta_status.py` — counting (no UI)

Single source of truth for counting. Main API:

- `escanear(base=results/batches) -> Status`: sweeps all batches, classifies
  each run as valid/invalid, aggregates by (model, scenario).
- `Status.grade() -> dict[(modelo, cenario)] -> ContagemCelula`, where
  `ContagemCelula` has `validos`, `invalidos`, `faltam = max(0, META - validos)`.
- `Status.por_batch()` — per-batch breakdown (for debugging).

**Validity rule for a run** (all must be true):
1. the `<run_id>.jsonl` file exists and is not empty;
2. it has ≥1 parseable JSON line;
3. 0 parse errors in the non-empty lines;
4. the batch's `manifest.csv` marks `status=OK` for that run (discards
   `TIMEOUT`/`ERROR`). If there is no manifest, it falls back to criteria 1–3.

Also executable as a CLI (`python coleta_status.py`) that prints the grid in the
terminal — useful without opening the TUI.

### 3. `run_experiments.py` — minimal refactor

- Extract the triple loop from `main()` into a reusable function:
  `run_matrix(*, models, scenarios, runs, prompt, out_dir, timeout, keep_workspaces, dry_run, progress_cb=None) -> list[dict]`.
- `progress_cb(evento)` is called **after each trial** with a dictionary
  `{"indice": k, "total": N, "record": <record from run_trial>}`.
- Ensure `out_dir.mkdir(parents=True, exist_ok=True)` **inside** `run_matrix`,
  before the first trial (fixes a bug found in the spike: today the `mkdir` only
  happens in `main()`, and `run_trial` assumes the directory already exists).
- `main()` now calls `run_matrix` (the CLI stays identical for the user).

### 4. `coleta_tui.py` — Textual interface

Three regions on the screen:

- **Selection**: model checkboxes (from `MODELOS`), scenario checkboxes (with
  `ROTULOS_CENARIO`), numeric field "runs per cell", **Rodar** (Run) button.
- **Collected (live grid)**: model × scenario table showing
  `válidos/30 — faltam N` (valid/30 — N remaining), colored (green when
  complete). Loaded from `coleta_status.escanear()` on open and re-scanned at
  the end of each batch.
- **Live execution**: progress bar `trial k/N` + log of the latest trials
  (`modelo / cenário / run → OK | FALHOU`, where FALHOU = FAILED).

**Collector identity**: the batch is named `batch_<coletor>_<timestamp UTC>`.
The `<coletor>` is read from a `.coleta_user` file (gitignored). If it doesn't
exist, the TUI asks once on the first run and saves it.

## Data flow

1. **Open**: `coleta_status.escanear()` → fills the "Collected" grid.
2. **Select + Run**: the TUI builds
   `out_dir = results/batches/batch_<coletor>_<ts>` and fires a **Textual
   worker** (thread) that calls `run_matrix(..., progress_cb=postar_na_ui)`.
3. **During**: each trial returns → `progress_cb` posts a message to the UI
   (updates the bar + execution log). The UI is never updated directly from the
   thread; it uses Textual's message/`call_from_thread` mechanism.
4. **End of batch**: re-scans via `coleta_status` (accurate count, applying the
   validity rule) → updates the "Collected" grid.
5. **Sync**: manual, outside the TUI (`git pull/commit/push` via `COLLECTION.md`).

## Error handling

- A trial that fails (TIMEOUT/ERROR/empty JSONL) → appears as **FALHOU**
  (FAILED) in the log and **does not count** toward the goal (validity rule).
  Recovery = run more.
- The failure of an individual trial doesn't bring down the TUI: `run_trial`
  already catches timeouts; `run_matrix` continues the loop and reports the
  status via `progress_cb`.
- `opencode` missing or authentication error → the trial returns `ERROR`,
  visible in the log. (Environment prerequisites are documented in `COLLECTION.md`.)

## Tests

Focus on the logic; the UI gets only a smoke test.

- **`coleta_status`** (main): unit tests with fixture directories containing a
  valid run, an empty run, a timeout stub and mixed models; assertions on
  `validos`, `invalidos`, `faltam` per cell.
- **`run_matrix`**: test with `dry_run=True` checking that `progress_cb` is
  called `N` times with the correct `indice`/`total` and the expected records
  (same mechanics as the validated spike).
- **`coleta_tui`**: smoke test with Textual's test harness (`Pilot`) — the app
  composes, the grid populates from a fake `Status`, the Rodar button triggers
  the worker. Without covering the real execution path of `opencode`.

## Out of scope (YAGNI)

- Git inside the TUI (sync is manual via `COLLECTION.md`).
- Manual review UI for `PARTIAL` cases (stays centralized in `manual_review.py`).
- Chart generation in the TUI (`gerar_figuras_artigo.py` remains separate).
- Multi-user awareness beyond reading the batches present in `results/`.

## Open item

- Validate `deepseek-v4-flash-free` with 1 real trial before (or at the start of)
  the first collection. Low risk: same OpenCode path already validated for
  `nemotron-3-ultra-free`.

## Associated deliverables (outside this TUI, but related)

- `COLLECTION.md`: daily loop (`pull → run (TUI) → check → commit → push`) and
  environment prerequisites.
- Update the model list in `gerar_figuras_artigo.py` (`tcc2/` repo) to the new
  roster, kept manually aligned with `coleta_config`.
