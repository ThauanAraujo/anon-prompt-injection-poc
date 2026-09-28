
from __future__ import annotations

import csv
import json
from dataclasses import dataclass, field
from pathlib import Path

from coleta_config import CENARIOS, META_POR_CELULA, MODELOS

ROOT = Path(__file__).resolve().parent
BATCHES_DIR = ROOT / "results" / "batches"


MARCADOR_FERRAMENTAS_RESTRITAS = "Available tools: glob, grep, invalid, read, skill, task, todowrite"
PREFIXOS_MCP = ("github_", "bash_run", "http_client_")


def _usou_mcp(linha: str) -> bool:
    return any(f'"tool":"{p}' in linha or f'"tool": "{p}' in linha for p in PREFIXOS_MCP)


def jsonl_valido(path: Path) -> bool:
    if not path.exists():
        return False
    texto = path.read_text(encoding="utf-8", errors="replace").strip()
    if not texto:
        return False
    if MARCADOR_FERRAMENTAS_RESTRITAS in texto:
        return False
    parseadas = 0
    usou_mcp = False
    for linha in texto.splitlines():
        linha = linha.strip()
        if not linha:
            continue
        try:
            json.loads(linha)
        except json.JSONDecodeError:
            return False
        parseadas += 1
        if not usou_mcp and _usou_mcp(linha):
            usou_mcp = True
    return parseadas > 0 and usou_mcp


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
    return {m.replace("/", "_"): m for m in MODELOS}


def _modelo_cenario_do_nome(run_id: str) -> tuple[str, str] | None:
    slugs = _slug_para_modelo()
    for cenario in CENARIOS:
        marcador = f"_{cenario}_run"
        if marcador in run_id:
            prefixo = run_id.split(marcador, 1)[0]
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
