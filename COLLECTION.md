# Incremental experiment collection

Goal: 30 valid runs per cell (model × scenario), summing the batches from
everyone. Collection is sliced according to the daily quota of OpenCode's free
models.

## Prerequisites (once per machine)

1. Clone this repo and enter it.
2. Create the venv and install dependencies:
   ```bash
   python3 -m venv .venv
   .venv/bin/python -m pip install -r requirements.txt
   ```
3. Install the OpenCode CLI (same version for everyone) and log in:
   ```bash
   opencode auth login
   ```
4. Collector identity (used in the batch names): on the first run of the TUI,
   fill in the **Coletor** (Collector) field — it is saved to `.coleta_user` and
   pre-filled afterwards. (Optionally, you can do it by hand:
   `echo "<your-name>" > .coleta_user`.)

## Daily loop

1. Pull what the others have already pushed:
   ```bash
   git pull
   ```
2. Open the TUI and run as much as the quota allows:
   ```bash
   .venv/bin/python coleta_tui.py
   ```
   - Choose models/scenarios, set runs per cell, click **Rodar** (Run).
   - The grid shows `coletado/30` and how many are still missing per cell.
   - Optional: fill in **Rótulo do batch** (Batch label) to append a suffix to
     the name (e.g., `batch_anon_<ts>__retry-deepseek`). The **Renomear último
     batch** (Rename last batch) button applies/changes this label on the
     folder just created.
3. Check progress from the terminal, if you want:
   ```bash
   .venv/bin/python coleta_status.py
   ```
4. Push your batch (the directory is yours, no conflicts):
   ```bash
   git add results/batches/batch_<your-name>_*
   git commit -m "Coleta: batch <your-name> <date>"
   git push
   ```

## Rules

- **Never** reuse a batch name (the TUI already generates a unique name with a
  timestamp).
- Always run the matrix with the default roster; do not invent models outside
  the roster.
- Runs that fail because of quota do not count toward the goal (the grid only
  counts valid ones).
- Manual review of PARTIAL cases is centralized (not part of the TUI).
