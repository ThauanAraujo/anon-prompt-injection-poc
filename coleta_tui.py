
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


SEPARADOR_SUFIXO = "__"


def _slug_sufixo(sufixo: str) -> str:
    if not sufixo or not sufixo.strip():
        return ""
    return run_experiments.slug(sufixo)


def aplicar_sufixo(nome_base: str, sufixo: str) -> str:
    s = _slug_sufixo(sufixo)
    return f"{nome_base}{SEPARADOR_SUFIXO}{s}" if s else nome_base


def base_sem_sufixo(nome: str) -> str:
    return nome.split(SEPARADOR_SUFIXO, 1)[0]


def nome_batch(coletor: str, momento: datetime | None = None, sufixo: str = "") -> str:
    momento = momento or datetime.now(timezone.utc)
    ts = momento.strftime("%Y%m%dT%H%M%SZ")
    return aplicar_sufixo(f"batch_{coletor}_{ts}", sufixo)


def renomear_batch(batch_dir: Path, novo_sufixo: str) -> Path:
    novo_nome = aplicar_sufixo(base_sem_sufixo(batch_dir.name), novo_sufixo)
    novo = batch_dir.parent / novo_nome
    if novo != batch_dir:
        batch_dir.rename(novo)
    return novo


import coleta_status
import run_experiments
from coleta_config import (
    CENARIOS,
    META_POR_CELULA,
    MODELOS,
    ROTULOS_CENARIO,
    ROTULOS_MODELO,
    TIMEOUT_POR_TRIAL,
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
                for idx, m in enumerate(MODELOS):
                    yield Checkbox(ROTULOS_MODELO[m], value=True, id=f"m_{idx}")
                yield Label("Cenários")
                for idx, c in enumerate(CENARIOS):
                    yield Checkbox(ROTULOS_CENARIO[c], value=True, id=f"c_{idx}")
                yield Label("Runs por célula")
                yield Input(value="3", id="runs", type="integer")
                yield Label("Coletor")
                yield Input(value=ler_coletor() or "", placeholder="seu nome",
                            id="coletor")
                yield Label("Rótulo do batch (opcional)")
                yield Input(placeholder="ex.: retry-deepseek", id="sufixo")
                yield Button("Rodar", id="rodar", variant="primary")
                yield Button("Renomear último batch", id="renomear", disabled=True)
            with VerticalScroll(id="painel"):
                yield DataTable(id="grade")
                yield ProgressBar(id="progresso", total=100)
                yield Log(id="log")
        yield Footer()

    def on_mount(self) -> None:
        self._ultimo_batch: Path | None = None
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
        return [item for idx, item in enumerate(itens)
                if self.query_one(f"#{prefixo}_{idx}", Checkbox).value]

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "rodar":
            self._rodar()
        elif event.button.id == "renomear":
            self._renomear()

    def _rodar(self) -> None:
        log = self.query_one("#log", Log)
        models = self._selecionados("m", MODELOS)
        scenarios = self._selecionados("c", CENARIOS)
        try:
            runs = int(self.query_one("#runs", Input).value)
        except ValueError:
            runs = 0
        coletor = self.query_one("#coletor", Input).value.strip()
        sufixo = self.query_one("#sufixo", Input).value
        if not coletor:
            log.write_line("Defina o nome do coletor antes de rodar.")
            return
        if not models or not scenarios or runs < 1:
            log.write_line("Selecione ao menos 1 modelo, 1 cenário e runs >= 1.")
            return
        salvar_coletor(coletor)
        out_dir = ROOT / "results" / "batches" / nome_batch(coletor, sufixo=sufixo)
        self.query_one("#rodar", Button).disabled = True
        self.query_one("#renomear", Button).disabled = True
        self.coletar(models, scenarios, runs, out_dir)

    def _renomear(self) -> None:
        log = self.query_one("#log", Log)
        if self._ultimo_batch is None or not self._ultimo_batch.exists():
            log.write_line("Nenhum batch desta sessão para renomear.")
            return
        sufixo = self.query_one("#sufixo", Input).value
        novo = renomear_batch(self._ultimo_batch, sufixo)
        self._ultimo_batch = novo
        log.write_line(f"Renomeado para: {novo.name}")
        self.atualizar_grade()

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
            timeout=TIMEOUT_POR_TRIAL,
            progress_cb=progresso,
        )
        self._ultimo_batch = out_dir
        self.call_from_thread(log.write_line, "Batch concluído. Commit + push (COLETA.md).")
        self.call_from_thread(self.atualizar_grade)
        self.call_from_thread(
            setattr, self.query_one("#rodar", Button), "disabled", False)
        self.call_from_thread(
            setattr, self.query_one("#renomear", Button), "disabled", False)


def main() -> int:
    ColetaApp().run()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
