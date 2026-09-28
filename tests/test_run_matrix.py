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
    assert (tmp_path / "batch_test").exists()


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
