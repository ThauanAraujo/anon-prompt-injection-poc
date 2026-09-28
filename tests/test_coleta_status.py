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


import csv as _csv


def _batch_com_manifest(base: Path, nome: str, linhas: list[dict]) -> Path:
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
            {"run_id": "r3", "model": "opencode/big-pickle", "scenario": "baseline", "status": "ERROR"},
            {"run_id": "r4", "model": "opencode/big-pickle", "scenario": "baseline",
             "status": "OK", "_jsonl": "nao-json\n"},
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
