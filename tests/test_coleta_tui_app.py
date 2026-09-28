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
    monkeypatch.setattr(tui, "salvar_coletor", lambda nome: None)

    app = tui.ColetaApp()
    async with app.run_test() as pilot:
        app.query_one("#runs", tui.Input).value = "2"
        app.query_one("#rodar", tui.Button).press()
        await pilot.pause()
        await app.workers.wait_for_complete()

    assert chamadas.get("runs") == 2
    assert chamadas.get("models") == MODELOS
    assert chamadas.get("scenarios") == CENARIOS
    assert chamadas["out_dir"].name.startswith("batch_tester_")


async def test_rodar_exige_coletor(monkeypatch):
    monkeypatch.setattr(tui.coleta_status, "escanear",
                        lambda *a, **k: cs.Status(grade={}))
    monkeypatch.setattr(tui, "ler_coletor", lambda: None)
    chamou = {"run": False}
    monkeypatch.setattr(tui.run_experiments, "run_matrix",
                        lambda **k: chamou.update(run=True) or [])

    app = tui.ColetaApp()
    async with app.run_test() as pilot:
        app.query_one("#rodar", tui.Button).press()
        await pilot.pause()

    assert chamou["run"] is False


async def test_renomear_ultimo_batch(monkeypatch, tmp_path):
    monkeypatch.setattr(tui.coleta_status, "escanear",
                        lambda *a, **k: cs.Status(grade={}))
    d = tmp_path / "batch_tester_20260613T181229Z"
    d.mkdir()

    app = tui.ColetaApp()
    async with app.run_test() as pilot:
        app._ultimo_batch = d
        app.query_one("#sufixo", tui.Input).value = "retry deepseek"
        botao = app.query_one("#renomear", tui.Button)
        botao.disabled = False
        botao.press()
        await pilot.pause()

    assert (tmp_path / "batch_tester_20260613T181229Z__retry_deepseek").exists()
    assert not d.exists()
