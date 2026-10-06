"""Testes dos metadados de repositório e do funil de seleção. Nunca acessam a rede."""
from pipeline.funil import Funnel


# --------------------------------------------------------------------------- Funnel

def test_funil_calcula_descartados_entre_etapas():
    funil = Funnel()
    funil.add("candidatos", 4000)
    funil.add("com Actions", 2900, "sem workflows")
    funil.add(">=5 releases e >=50 runs", 610, "poucas releases ou runs")
    funil.add("amostra final", 350, "amostra atingida")
    df = funil.to_dataframe()
    assert list(df.columns) == ["etapa", "restantes", "descartados", "motivo"]
    assert df.to_dict("records") == [
        {"etapa": "candidatos", "restantes": 4000, "descartados": 0, "motivo": ""},
        {"etapa": "com Actions", "restantes": 2900, "descartados": 1100, "motivo": "sem workflows"},
        {"etapa": ">=5 releases e >=50 runs", "restantes": 610, "descartados": 2290,
         "motivo": "poucas releases ou runs"},
        {"etapa": "amostra final", "restantes": 350, "descartados": 260, "motivo": "amostra atingida"},
    ]
