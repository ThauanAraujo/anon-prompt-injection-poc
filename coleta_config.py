
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

TIMEOUT_POR_TRIAL = 1800
