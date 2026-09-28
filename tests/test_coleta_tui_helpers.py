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


def test_nome_batch_com_sufixo():
    momento = datetime(2026, 6, 13, 18, 12, 29, tzinfo=timezone.utc)
    assert (tui.nome_batch("XXXX-1", momento, sufixo="retry deepseek")
            == "batch_anon_20260613T181229Z__retry_deepseek")


def test_nome_batch_sufixo_vazio_nao_muda():
    momento = datetime(2026, 6, 13, 18, 12, 29, tzinfo=timezone.utc)
    assert tui.nome_batch("XXXX-1", momento, sufixo="   ") == "batch_anon_20260613T181229Z"


def test_renomear_batch_aplica_sufixo_preservando_base(tmp_path):
    d = tmp_path / "batch_anon_20260613T181229Z"
    d.mkdir()
    novo = tui.renomear_batch(d, "retry deepseek")
    assert novo.name == "batch_anon_20260613T181229Z__retry_deepseek"
    assert novo.exists() and not d.exists()


def test_renomear_batch_troca_sufixo_existente(tmp_path):
    d = tmp_path / "batch_anon_20260613T181229Z__old"
    d.mkdir()
    novo = tui.renomear_batch(d, "novo")
    assert novo.name == "batch_anon_20260613T181229Z__novo"


def test_renomear_batch_sufixo_vazio_remove_sufixo(tmp_path):
    d = tmp_path / "batch_anon_20260613T181229Z__old"
    d.mkdir()
    novo = tui.renomear_batch(d, "  ")
    assert novo.name == "batch_anon_20260613T181229Z"
