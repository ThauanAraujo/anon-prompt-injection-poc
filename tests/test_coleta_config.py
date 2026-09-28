import coleta_config as cfg


def test_roster_e_meta():
    assert cfg.MODELOS == [
        "opencode/big-pickle",
        "opencode/nemotron-3-ultra-free",
        "opencode/deepseek-v4-flash-free",
    ]
    assert cfg.CENARIOS == ["baseline", "scenario_2", "scenario_3", "scenario_4"]
    assert cfg.META_POR_CELULA == 30
    assert set(cfg.ROTULOS_MODELO) == set(cfg.MODELOS)
    assert set(cfg.ROTULOS_CENARIO) == set(cfg.CENARIOS)
