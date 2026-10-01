# Coleta TUI — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a TUI (Textual) that lets each collaborator choose models/scenarios/runs, see the collected progress toward the goal of 30 per cell (counting only valid runs), and follow the execution live.

**Architecture:** Four units in `poc/`: `coleta_config` (single source of models/scenarios/goal), `coleta_status` (counts valid runs by aggregating batches), a refactor of `run_experiments` to expose `run_matrix(..., progress_cb)`, and `coleta_tui` (Textual app that orchestrates the runner in a worker). Git stays outside the TUI (manual sync via `COLLECTION.md`).

**Tech Stack:** Python 3.14 (`.venv`), Textual, pytest, pytest-asyncio. Spec: `docs/superpowers/specs/2026-06-13-coleta-tui-design.md`.

**Convention:** all commands run from `poc/` with `.venv/bin/python` and `.venv/bin/pytest`. Working branch: `coleta-tui`.

---

## Task 1: Dependencies and test scaffolding

**Files:**
- Create: `poc/requirements.txt`
- Create: `poc/requirements-dev.txt`
- Create: `poc/pytest.ini`
- Create: `poc/tests/__init__.py`
- Modify: `poc/.gitignore`

- [ ] **Step 1: Create `requirements.txt`**

```text
mcp
fastmcp
textual
```

- [ ] **Step 2: Create `requirements-dev.txt`**

```text
pytest
pytest-asyncio
```

- [ ] **Step 3: Create `pytest.ini`**

```ini
[pytest]
asyncio_mode = auto
testpaths = tests
```

- [ ] **Step 4: Create `tests/__init__.py`** (empty file)

```python
```

- [ ] **Step 5: Add `.coleta_user` to `.gitignore`**

Append to the end of `poc/.gitignore`:

```text

# Local collector identity (do not version)
.coleta_user
```

- [ ] **Step 6: Install dependencies**

Run: `.venv/bin/python -m pip install -r requirements.txt -r requirements-dev.txt`
Expected: installs `textual`, `pytest`, `pytest-asyncio` without errors.

- [ ] **Step 7: Verify imports**

Run: `.venv/bin/python -c "import textual, pytest; print('ok', textual.__version__)"`
Expected: prints `ok <version>`.

- [ ] **Step 8: Commit**

```bash
git add requirements.txt requirements-dev.txt pytest.ini tests/__init__.py .gitignore
git commit -m "Add deps and test scaffolding for the collection TUI"
```

---

## Task 2: `coleta_config.py` — single source of truth

**Files:**
- Create: `poc/coleta_config.py`
- Test: `poc/tests/test_coleta_config.py`

- [ ] **Step 1: Write the failing test**

```python
# poc/tests/test_coleta_config.py
import coleta_config as cfg


def test_roster_e_meta():
    assert cfg.MODELOS == [
        "opencode/big-pickle",
        "opencode/nemotron-3-ultra-free",
        "opencode/deepseek-v4-flash-free",
    ]
    assert cfg.CENARIOS == ["baseline", "scenario_2", "scenario_3", "scenario_4"]
    assert cfg.META_POR_CELULA == 30
    # every model/scenario has a label
    assert set(cfg.ROTULOS_MODELO) == set(cfg.MODELOS)
    assert set(cfg.ROTULOS_CENARIO) == set(cfg.CENARIOS)
```

- [ ] **Step 2: Run the test and watch it fail**

Run: `.venv/bin/pytest tests/test_coleta_config.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'coleta_config'`.

- [ ] **Step 3: Implement `coleta_config.py`**

```python
# poc/coleta_config.py
"""Shared collection configuration: roster of models, scenarios and goal.

Single source imported by run_experiments, coleta_status and coleta_tui.
"""

MODELOS = [
    "opencode/big-pickle",
    "opencode/nemotron-3-ultra-free",
    "opencode/deepseek-v4-flash-free",
]

ROTULOS_MODELO = {
    "opencode/big-pickle": "big-pickle",
    "opencode/nemotron-3-ultra-free": "nemotron-3-ultra",
    "opencode/deepseek-v4-flash-free": "deepseek-v4-flash",
}

CENARIOS = ["baseline", "scenario_2", "scenario_3", "scenario_4"]

ROTULOS_CENARIO = {
    "baseline": "Controle benigno",
    "scenario_2": "Ataque explícito",
    "scenario_3": "Ataque dissimulado 1",
    "scenario_4": "Ataque dissimulado 2",
}

META_POR_CELULA = 30
```

- [ ] **Step 4: Run the test and watch it pass**

Run: `.venv/bin/pytest tests/test_coleta_config.py -v`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add coleta_config.py tests/test_coleta_config.py
git commit -m "Add coleta_config with roster, scenarios and goal"
```

---

## Task 3: `coleta_status.py` — JSONL validity

**Files:**
- Create: `poc/coleta_status.py`
- Test: `poc/tests/test_coleta_status.py`

- [ ] **Step 1: Write the failing test**

```python
# poc/tests/test_coleta_status.py
from pathlib import Path

import coleta_status as cs


def _escrever(p: Path, conteudo: str) -> Path:
    p.write_text(conteudo, encoding="utf-8")
    return p


def test_jsonl_valido_reconhece_arquivo_bom(tmp_path):
    bom = _escrever(tmp_path / "ok.jsonl", '{"a":1}\n{"b":2}\n')
    assert cs.jsonl_valido(bom) is True


def test_jsonl_valido_rejeita_vazio_ausente_e_corrompido(tmp_path):
    assert cs.jsonl_valido(tmp_path / "nao_existe.jsonl") is False
    vazio = _escrever(tmp_path / "vazio.jsonl", "   \n")
    assert cs.jsonl_valido(vazio) is False
    corrompido = _escrever(tmp_path / "ruim.jsonl", '{"a":1}\nnao-json\n')
    assert cs.jsonl_valido(corrompido) is False
```

- [ ] **Step 2: Run and watch it fail**

Run: `.venv/bin/pytest tests/test_coleta_status.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'coleta_status'`.

- [ ] **Step 3: Implement the first part of `coleta_status.py`**

```python
# poc/coleta_status.py
"""Counts valid runs by (model, scenario), aggregating all local batches.

Also executable: `python coleta_status.py` prints the grid to the terminal.
"""

from __future__ import annotations

import csv
import json
from dataclasses import dataclass, field
from pathlib import Path

from coleta_config import CENARIOS, META_POR_CELULA, MODELOS

ROOT = Path(__file__).resolve().parent
BATCHES_DIR = ROOT / "results" / "batches"


def jsonl_valido(path: Path) -> bool:
    """Valid = exists, non-empty, >=1 parseable JSON line and 0 parse errors."""
    if not path.exists():
        return False
    texto = path.read_text(encoding="utf-8", errors="replace").strip()
    if not texto:
        return False
    parseadas = 0
    for linha in texto.splitlines():
        linha = linha.strip()
        if not linha:
            continue
        try:
            json.loads(linha)
        except json.JSONDecodeError:
            return False
        parseadas += 1
    return parseadas > 0
```

- [ ] **Step 4: Run and watch it pass**

Run: `.venv/bin/pytest tests/test_coleta_status.py -v`
Expected: PASS (3 tests).

- [ ] **Step 5: Commit**

```bash
git add coleta_status.py tests/test_coleta_status.py
git commit -m "Add coleta_status.jsonl_valido with tests"
```

---

## Task 4: `coleta_status` — scan, grid, and CLI

**Files:**
- Modify: `poc/coleta_status.py`
- Test: `poc/tests/test_coleta_status.py`

- [ ] **Step 1: Write the failing tests** (append to the end of `tests/test_coleta_status.py`)

```python
import csv as _csv


def _batch_com_manifest(base: Path, nome: str, linhas: list[dict]) -> Path:
    """Cria um batch com manifest.csv e os .jsonl correspondentes."""
    batch = base / nome
    batch.mkdir(parents=True)
    campos = ["run_id", "model", "scenario", "status"]
    with (batch / "manifest.csv").open("w", encoding="utf-8", newline="") as fh:
        w = _csv.DictWriter(fh, fieldnames=campos, extrasaction="ignore")
        w.writeheader()
        for ln in linhas:
            w.writerow(ln)
            conteudo = ln.pop("_jsonl", '{"type":"step_start"}\n')
            (batch / f"{ln['run_id']}.jsonl").write_text(conteudo, encoding="utf-8")
    return batch


def test_escanear_conta_validos_e_invalidos_por_celula(tmp_path):
    _batch_com_manifest(
        tmp_path,
        "batch_a",
        [
            {"run_id": "r1", "model": "opencode/big-pickle", "scenario": "baseline", "status": "OK"},
            {"run_id": "r2", "model": "opencode/big-pickle", "scenario": "baseline", "status": "OK"},
            # status ERROR -> invalid
            {"run_id": "r3", "model": "opencode/big-pickle", "scenario": "baseline", "status": "ERROR"},
            # status OK but corrupted jsonl -> invalid
            {"run_id": "r4", "model": "opencode/big-pickle", "scenario": "baseline",
             "status": "OK", "_jsonl": "nao-json\n"},
            # model outside the roster -> ignored
            {"run_id": "r5", "model": "opencode/modelo-velho", "scenario": "baseline", "status": "OK"},
        ],
    )
    status = cs.escanear(base=tmp_path)
    cel = status.celula("opencode/big-pickle", "baseline")
    assert cel.validos == 2
    assert cel.invalidos == 2
    assert cel.faltam(meta=30) == 28
    assert status.celula("opencode/modelo-velho", "baseline").validos == 0


def test_escanear_agrega_multiplos_batches(tmp_path):
    for nome in ("batch_x", "batch_y"):
        _batch_com_manifest(
            tmp_path,
            nome,
            [{"run_id": f"{nome}_r1", "model": "opencode/big-pickle",
              "scenario": "scenario_3", "status": "OK"}],
        )
    status = cs.escanear(base=tmp_path)
    assert status.celula("opencode/big-pickle", "scenario_3").validos == 2


def test_fallback_sem_manifest_usa_nome_do_arquivo(tmp_path):
    batch = tmp_path / "batch_sem_manifest"
    batch.mkdir()
    nome = "20260613T181229Z_opencode_big-pickle_scenario_4_run001.jsonl"
    (batch / nome).write_text('{"type":"step_start"}\n', encoding="utf-8")
    status = cs.escanear(base=tmp_path)
    assert status.celula("opencode/big-pickle", "scenario_4").validos == 1
```

- [ ] **Step 2: Run and watch it fail**

Run: `.venv/bin/pytest tests/test_coleta_status.py -v`
Expected: FAIL (`AttributeError: module 'coleta_status' has no attribute 'escanear'`).

- [ ] **Step 3: Implement the rest of `coleta_status.py`** (append below `jsonl_valido`)

```python
@dataclass
class ContagemCelula:
    validos: int = 0
    invalidos: int = 0

    def faltam(self, meta: int = META_POR_CELULA) -> int:
        return max(0, meta - self.validos)


@dataclass
class Status:
    grade: dict[tuple[str, str], ContagemCelula] = field(default_factory=dict)

    def celula(self, modelo: str, cenario: str) -> ContagemCelula:
        return self.grade.get((modelo, cenario), ContagemCelula())

    def total_validos(self) -> int:
        return sum(c.validos for c in self.grade.values())


def _slug_para_modelo() -> dict[str, str]:
    """Maps the slug used in the file name back to the model in the roster.

    run_experiments.slug("opencode/big-pickle") -> "opencode_big-pickle".
    """
    return {m.replace("/", "_"): m for m in MODELOS}


def _modelo_cenario_do_nome(run_id: str) -> tuple[str, str] | None:
    slugs = _slug_para_modelo()
    for cenario in CENARIOS:
        marcador = f"_{cenario}_run"
        if marcador in run_id:
            prefixo = run_id.split(marcador, 1)[0]  # "<timestamp>_<model_slug>"
            partes = prefixo.split("_", 1)
            if len(partes) == 2 and partes[1] in slugs:
                return slugs[partes[1]], cenario
    return None


def _registrar(grade: dict[tuple[str, str], ContagemCelula],
               modelo: str, cenario: str, valido: bool) -> None:
    if modelo not in MODELOS or cenario not in CENARIOS:
        return
    cel = grade.setdefault((modelo, cenario), ContagemCelula())
    if valido:
        cel.validos += 1
    else:
        cel.invalidos += 1


def _contar_batch(batch_dir: Path, grade: dict[tuple[str, str], ContagemCelula]) -> None:
    manifest = batch_dir / "manifest.csv"
    if manifest.exists():
        with manifest.open(encoding="utf-8", newline="") as fh:
            for row in csv.DictReader(fh):
                jsonl = batch_dir / f"{row['run_id']}.jsonl"
                valido = row.get("status") == "OK" and jsonl_valido(jsonl)
                _registrar(grade, row["model"], row["scenario"], valido)
        return
    # No manifest: best-effort by file name (validity from JSONL only).
    for jsonl in batch_dir.glob("*.jsonl"):
        if jsonl.name.endswith(".bash_commands.jsonl"):
            continue
        mc = _modelo_cenario_do_nome(jsonl.stem)
        if mc is None:
            continue
        modelo, cenario = mc
        _registrar(grade, modelo, cenario, jsonl_valido(jsonl))


def escanear(base: Path = BATCHES_DIR) -> Status:
    grade: dict[tuple[str, str], ContagemCelula] = {}
    if base.exists():
        for batch_dir in sorted(p for p in base.iterdir() if p.is_dir()):
            _contar_batch(batch_dir, grade)
    return Status(grade=grade)


def imprimir(status: Status, meta: int = META_POR_CELULA) -> None:
    for modelo in MODELOS:
        for cenario in CENARIOS:
            cel = status.celula(modelo, cenario)
            marca = "OK" if cel.validos >= meta else f"faltam {cel.faltam(meta)}"
            print(f"{modelo:38} {cenario:12} {cel.validos:3}/{meta}  ({marca})")
    print(f"\ntotal válidos: {status.total_validos()}")


def main() -> int:
    imprimir(escanear())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
```

- [ ] **Step 4: Run and watch it pass**

Run: `.venv/bin/pytest tests/test_coleta_status.py -v`
Expected: PASS (all tests in the file).

- [ ] **Step 5: CLI smoke test**

Run: `.venv/bin/python coleta_status.py`
Expected: prints the 3×4 grid with real counts from the existing batches (old models do not appear) + total.

- [ ] **Step 6: Commit**

```bash
git add coleta_status.py tests/test_coleta_status.py
git commit -m "Add scanning, grid and CLI to coleta_status"
```

---

## Task 5: Refactor `run_experiments` into `run_matrix(progress_cb)`

**Files:**
- Modify: `poc/run_experiments.py` (`main` function, lines ~257-292; add `run_matrix`)
- Test: `poc/tests/test_run_matrix.py`

- [ ] **Step 1: Write the failing test**

```python
# poc/tests/test_run_matrix.py
import run_experiments as rx


def test_run_matrix_dry_run_chama_callback_por_trial(tmp_path):
    eventos = []
    rows = rx.run_matrix(
        models=["opencode/big-pickle"],
        scenarios=["baseline", "scenario_3"],
        runs=2,
        prompt="test prompt",
        out_dir=tmp_path / "batch_test",
        timeout=10,
        dry_run=True,
        progress_cb=eventos.append,
    )
    assert len(rows) == 4
    assert len(eventos) == 4
    assert eventos[0]["total"] == 4
    assert [e["indice"] for e in eventos] == [1, 2, 3, 4]
    assert eventos[0]["record"]["model"] == "opencode/big-pickle"
    assert (tmp_path / "batch_test").exists()  # out_dir created by run_matrix


def test_run_matrix_funciona_sem_callback(tmp_path):
    rows = rx.run_matrix(
        models=["opencode/big-pickle"],
        scenarios=["baseline"],
        runs=1,
        prompt="p",
        out_dir=tmp_path / "b2",
        timeout=10,
        dry_run=True,
    )
    assert len(rows) == 1
```

- [ ] **Step 2: Run and watch it fail**

Run: `.venv/bin/pytest tests/test_run_matrix.py -v`
Expected: FAIL (`AttributeError: module 'run_experiments' has no attribute 'run_matrix'`).

- [ ] **Step 3: Add `run_matrix`** right above `def parse_args` in `run_experiments.py`

```python
def run_matrix(
    *,
    models: list[str],
    scenarios: list[str],
    runs: int,
    prompt: str,
    out_dir: Path,
    timeout: int = 900,
    keep_workspaces: bool = False,
    dry_run: bool = False,
    progress_cb=None,
) -> list[dict]:
    """Runs the models×scenarios×runs matrix, calling progress_cb after each trial.

    progress_cb receives {"indice": k, "total": N, "record": <record from run_trial>}.
    """
    out_dir.mkdir(parents=True, exist_ok=True)
    total = len(models) * len(scenarios) * runs
    rows: list[dict] = []
    indice = 0
    for model in models:
        for scenario in scenarios:
            for run_index in range(1, runs + 1):
                record = run_trial(
                    model=model,
                    scenario=scenario,
                    run_index=run_index,
                    prompt=prompt,
                    out_dir=out_dir,
                    timeout=timeout,
                    dry_run=dry_run,
                    keep_workspaces=keep_workspaces,
                )
                indice += 1
                rows.append(record)
                if progress_cb is not None:
                    progress_cb({"indice": indice, "total": total, "record": record})
    write_manifest(out_dir / "manifest.csv", rows)
    return rows
```

- [ ] **Step 4: Rewrite `main` to use `run_matrix`**

In `main`, replace all lines from `args.out_dir = args.out_dir.expanduser().resolve()` through the final `return 0` (inclusive: the `mkdir`, the triple loop `for model ...`, the `write_manifest` and the prints) with:

```python
    args.out_dir = args.out_dir.expanduser().resolve()
    print(f"[out-dir] {args.out_dir}")

    run_matrix(
        models=args.models,
        scenarios=args.scenarios,
        runs=args.runs,
        prompt=prompt,
        out_dir=args.out_dir,
        timeout=args.timeout,
        keep_workspaces=args.keep_workspaces,
        dry_run=args.dry_run,
    )

    manifest_path = args.out_dir / "manifest.csv"
    print(f"[manifest] {manifest_path}")
    return 0
```

- [ ] **Step 5: Run the new test and watch it pass**

Run: `.venv/bin/pytest tests/test_run_matrix.py -v`
Expected: PASS (2 tests).

- [ ] **Step 6: Regression — CLI dry-run still works**

Run: `.venv/bin/python run_experiments.py --models opencode/big-pickle --scenarios baseline --runs 1 --dry-run --batch-name _smoke_plan`
Expected: prints `[out-dir] ...`, a JSON line of the record, `[manifest] ...`, no traceback.

- [ ] **Step 7: Clean up the smoke test artifact**

Run: `rm -rf results/batches/_smoke_plan`
Expected: removed.

- [ ] **Step 8: Commit**

```bash
git add run_experiments.py tests/test_run_matrix.py
git commit -m "Extract run_matrix with progress_cb and fix out_dir creation"
```

---

## Task 6: `coleta_tui` — identity and batch-name helpers

**Files:**
- Create: `poc/coleta_tui.py`
- Test: `poc/tests/test_coleta_tui_helpers.py`

- [ ] **Step 1: Write the failing test**

```python
# poc/tests/test_coleta_tui_helpers.py
from datetime import datetime, timezone

import coleta_tui as tui


def test_ler_e_salvar_coletor(tmp_path, monkeypatch):
    arquivo = tmp_path / ".coleta_user"
    monkeypatch.setattr(tui, "USER_FILE", arquivo)
    assert tui.ler_coletor() is None
    tui.salvar_coletor("XXXX-1")
    assert tui.ler_coletor() == "XXXX-1"


def test_nome_batch_formato(tmp_path):
    momento = datetime(2026, 6, 13, 18, 12, 29, tzinfo=timezone.utc)
    assert tui.nome_batch("XXXX-1", momento) == "batch_anon_20260613T181229Z"
```

- [ ] **Step 2: Run and watch it fail**

Run: `.venv/bin/pytest tests/test_coleta_tui_helpers.py -v`
Expected: FAIL (`ModuleNotFoundError: No module named 'coleta_tui'`).

- [ ] **Step 3: Create `coleta_tui.py` with the helpers**

```python
# poc/coleta_tui.py
"""Textual TUI for incremental experiment collection.

Choose models/scenarios/runs, show collected progress (goal of 30 per
cell, valid runs only) and follow execution live. Git stays out: sync
is manual (see COLLECTION.md).
"""

from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent
USER_FILE = ROOT / ".coleta_user"


def ler_coletor() -> str | None:
    if USER_FILE.exists():
        nome = USER_FILE.read_text(encoding="utf-8").strip()
        return nome or None
    return None


def salvar_coletor(nome: str) -> None:
    USER_FILE.write_text(nome.strip() + "\n", encoding="utf-8")


def nome_batch(coletor: str, momento: datetime | None = None) -> str:
    momento = momento or datetime.now(timezone.utc)
    ts = momento.strftime("%Y%m%dT%H%M%SZ")
    return f"batch_{coletor}_{ts}"
```

- [ ] **Step 4: Run and watch it pass**

Run: `.venv/bin/pytest tests/test_coleta_tui_helpers.py -v`
Expected: PASS (2 tests).

- [ ] **Step 5: Commit**

```bash
git add coleta_tui.py tests/test_coleta_tui_helpers.py
git commit -m "Add identity and batch-name helpers for the TUI"
```

---

## Task 7: `coleta_tui` — Textual app and orchestration

**Files:**
- Modify: `poc/coleta_tui.py`
- Test: `poc/tests/test_coleta_tui_app.py`

- [ ] **Step 1: Write the failing smoke test**

```python
# poc/tests/test_coleta_tui_app.py
import coleta_status as cs
import coleta_tui as tui
from coleta_config import CENARIOS, MODELOS
from textual.widgets import DataTable


async def test_app_compoe_e_popula_grade(monkeypatch):
    fake = cs.Status(grade={
        ("opencode/big-pickle", "baseline"): cs.ContagemCelula(validos=5),
    })
    monkeypatch.setattr(tui.coleta_status, "escanear", lambda *a, **k: fake)
    app = tui.ColetaApp()
    async with app.run_test():
        grade = app.query_one("#grade", DataTable)
        # one row per cell of the active roster
        assert grade.row_count == len(MODELOS) * len(CENARIOS)


async def test_botao_rodar_chama_run_matrix(monkeypatch):
    monkeypatch.setattr(tui.coleta_status, "escanear",
                        lambda *a, **k: cs.Status(grade={}))
    chamadas = {}

    def fake_run_matrix(**kwargs):
        chamadas.update(kwargs)
        return []

    monkeypatch.setattr(tui.run_experiments, "run_matrix", fake_run_matrix)
    monkeypatch.setattr(tui, "ler_coletor", lambda: "tester")

    app = tui.ColetaApp()
    async with app.run_test() as pilot:
        app.query_one("#runs", tui.Input).value = "2"
        await pilot.click("#rodar")
        await pilot.pause()
        # worker runs on a thread; wait for it to finish
        await app.workers.wait_for_complete()

    assert chamadas.get("runs") == 2
    assert chamadas.get("models") == MODELOS
    assert chamadas.get("scenarios") == CENARIOS
```

- [ ] **Step 2: Run and watch it fail**

Run: `.venv/bin/pytest tests/test_coleta_tui_app.py -v`
Expected: FAIL (`AttributeError: module 'coleta_tui' has no attribute 'ColetaApp'`).

- [ ] **Step 3: Implement the app** (append to the end of `coleta_tui.py`)

```python
import coleta_status
import run_experiments
from coleta_config import (
    CENARIOS,
    META_POR_CELULA,
    MODELOS,
    ROTULOS_CENARIO,
    ROTULOS_MODELO,
)

from textual import work
from textual.app import App, ComposeResult
from textual.containers import Horizontal, VerticalScroll
from textual.widgets import (
    Button,
    Checkbox,
    DataTable,
    Footer,
    Header,
    Input,
    Label,
    Log,
    ProgressBar,
)


class ColetaApp(App):
    """Collection app: selection on the left, progress/execution on the right."""

    CSS = """
    #selecao { width: 38; border: round $accent; padding: 1; }
    #painel { padding: 1; }
    #grade { height: 1fr; }
    #log { height: 10; border: round $accent; }
    """

    TITLE = "Coleta"

    def compose(self) -> ComposeResult:
        yield Header()
        with Horizontal():
            with VerticalScroll(id="selecao"):
                yield Label("Modelos")
                for m in MODELOS:
                    yield Checkbox(ROTULOS_MODELO[m], value=True, id=f"m_{m}")
                yield Label("Cenários")
                for c in CENARIOS:
                    yield Checkbox(ROTULOS_CENARIO[c], value=True, id=f"c_{c}")
                yield Label("Runs por célula")
                yield Input(value="3", id="runs", type="integer")
                yield Button("Rodar", id="rodar", variant="primary")
            with VerticalScroll(id="painel"):
                yield DataTable(id="grade")
                yield ProgressBar(id="progresso", total=100)
                yield Log(id="log")
        yield Footer()

    def on_mount(self) -> None:
        tabela = self.query_one("#grade", DataTable)
        tabela.add_columns("Modelo", "Cenário", "Coletado", "Faltam")
        self.atualizar_grade()

    def atualizar_grade(self) -> None:
        status = coleta_status.escanear()
        tabela = self.query_one("#grade", DataTable)
        tabela.clear()
        for m in MODELOS:
            for c in CENARIOS:
                cel = status.celula(m, c)
                faltam = cel.faltam(META_POR_CELULA)
                marca = "OK" if faltam == 0 else str(faltam)
                tabela.add_row(
                    ROTULOS_MODELO[m],
                    ROTULOS_CENARIO[c],
                    f"{cel.validos}/{META_POR_CELULA}",
                    marca,
                )

    def _selecionados(self, prefixo: str, itens: list[str]) -> list[str]:
        return [i for i in itens
                if self.query_one(f"#{prefixo}_{i}", Checkbox).value]

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id != "rodar":
            return
        models = self._selecionados("m", MODELOS)
        scenarios = self._selecionados("c", CENARIOS)
        try:
            runs = int(self.query_one("#runs", Input).value)
        except ValueError:
            runs = 0
        if not models or not scenarios or runs < 1:
            self.query_one("#log", Log).write_line(
                "Selecione ao menos 1 modelo, 1 cenário e runs >= 1.")
            return
        coletor = ler_coletor() or "XXXX-1"
        out_dir = ROOT / "results" / "batches" / nome_batch(coletor)
        self.query_one("#rodar", Button).disabled = True
        self.coletar(models, scenarios, runs, out_dir)

    @work(thread=True)
    def coletar(self, models, scenarios, runs, out_dir) -> None:
        log = self.query_one("#log", Log)
        barra = self.query_one("#progresso", ProgressBar)
        self.call_from_thread(log.write_line, f"Iniciando: {out_dir.name}")

        def progresso(evento: dict) -> None:
            rec = evento["record"]
            ok = rec.get("status") in ("OK", "DRY_RUN")
            marca = "OK" if ok else "FALHOU"
            linha = (f"[{evento['indice']}/{evento['total']}] "
                     f"{rec['model']} / {rec['scenario']} -> {marca}")
            self.call_from_thread(log.write_line, linha)
            pct = 100 * evento["indice"] / evento["total"]
            self.call_from_thread(barra.update, total=100, progress=pct)

        run_experiments.run_matrix(
            models=models,
            scenarios=scenarios,
            runs=runs,
            prompt=run_experiments.DEFAULT_PROMPT,
            out_dir=out_dir,
            progress_cb=progresso,
        )
        self.call_from_thread(log.write_line, "Batch concluído. Commit + push (COLLECTION.md).")
        self.call_from_thread(self.atualizar_grade)
        self.call_from_thread(
            setattr, self.query_one("#rodar", Button), "disabled", False)


def main() -> int:
    ColetaApp().run()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
```

- [ ] **Step 4: Run the smoke test and watch it pass**

Run: `.venv/bin/pytest tests/test_coleta_tui_app.py -v`
Expected: PASS (2 tests). If `wait_for_complete` does not exist in the Textual version, replace it with `await pilot.pause(0.1)` until the worker finishes — but try `wait_for_complete` first.

- [ ] **Step 5: Run the entire suite**

Run: `.venv/bin/pytest -v`
Expected: PASS in all test files.

- [ ] **Step 6: Manual smoke test (optional, interactive)**

Run: `.venv/bin/python coleta_tui.py`
Expected: opens the TUI; grid populates; `Ctrl+C`/`q` exits. (Do not run a real collection here.)

- [ ] **Step 7: Commit**

```bash
git add coleta_tui.py tests/test_coleta_tui_app.py
git commit -m "Add Textual collection app with live grid and live execution"
```

---

## Task 8: `COLLECTION.md` — daily flow and prerequisites

**Files:**
- Create: `poc/COLLECTION.md`

- [ ] **Step 1: Write `COLLECTION.md`**

```markdown
# Incremental experiment collection

Goal: 30 valid runs per cell (model × scenario), summing the batches from
everyone. Collection is sliced according to the daily quota of OpenCode's free models.

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
4. Set your collector identity (used in the batch names):
   ```bash
   echo "<your-name>" > .coleta_user   # ex.: XXXX-1, XXXX-1, XXXX-1
   ```

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
3. Check progress from the terminal, if you want:
   ```bash
   .venv/bin/python coleta_status.py
   ```
4. Push your batch (the directory is yours, no conflicts):
   ```bash
   git add results/batches/batch_<your-name>_*
   git commit -m "Collection: batch <your-name> <data>"
   git push
   ```

## Rules

- **Never** reuse a batch name (the TUI already generates a unique name with a timestamp).
- Always run the matrix with the default roster; do not invent models outside the roster.
- Runs that fail because of quota do not count toward the goal (the grid only counts valid ones).
- Manual review of PARTIAL cases is centralized (not part of the TUI).
```

- [ ] **Step 2: Commit**

```bash
git add COLLECTION.md
git commit -m "Add COLLECTION.md with daily flow and prerequisites"
```

---

## Task 9 (cross-repo, optional): align the models in the figures script

> This file lives in the `tcc2/` repo, not in `poc/`. Only do this when regenerating
> figures with the new data. No TDD (plotting script).

**Files:**
- Modify: `tcc2/gerar_figuras_artigo.py` (constants `MODELOS` and `ROTULOS_MODELO`, lines ~24-33)

- [ ] **Step 1: Update the model list**

Replace the constants with the new roster, keeping them aligned with `poc/coleta_config.py`:

```python
MODELOS = [
    "opencode/big-pickle",
    "opencode/nemotron-3-ultra-free",
    "opencode/deepseek-v4-flash-free",
]
ROTULOS_MODELO = {
    "opencode/big-pickle": "big-pickle",
    "opencode/nemotron-3-ultra-free": "nemotron-3-ultra",
    "opencode/deepseek-v4-flash-free": "deepseek-v4-flash",
}
```

- [ ] **Step 2: Commit (in the tcc2 repo)**

```bash
cd ../tcc2 && git add gerar_figuras_artigo.py && git commit -m "Align the figures' model roster with the new collection"
```

---

## Execution notes

- The open item from the spec (validating `deepseek-v4-flash-free` live) happens
  naturally in the first real batch through the TUI; if you want to do it earlier, run 1 `baseline`
  trial of that model and check the JSONL.
- Do not run a real collection inside the tests: the TUI/`run_matrix` tests use
  `dry_run`/monkeypatch and never call `opencode`.
