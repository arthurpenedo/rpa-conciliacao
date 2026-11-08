from rpa_conciliacao.cli import medir
from rpa_conciliacao.conciliar import _nome_na_descricao, conciliar, normalizar, resumo
from rpa_conciliacao.gerar import gerar

PED = [
    {"id": "P0001", "cliente": "Ana Souza", "valor": 45.0, "data": "2026-10-02"},
    {"id": "P0002", "cliente": "Ana Souza", "valor": 60.0, "data": "2026-10-02"},
    {"id": "P0003", "cliente": "João Pires", "valor": 32.5, "data": "2026-10-05"},
]


def lan(i, desc, valor, data="2026-10-03"):
    return {"id": i, "data": data, "descricao": desc, "valor": valor}


def por_id(res):
    return {r.lancamento["id"]: r for r in res}


def test_normalizar_tira_acento():
    assert normalizar("  João   Pirés ") == "JOAO PIRES"


def test_codigo_e_valor_iguais():
    r = por_id(conciliar(PED, [lan("L1", "PIX ANA SOUZA P0001", 45.0)]))
    assert r["L1"].status == "conciliado" and r["L1"].pedido_id == "P0001"


def test_codigo_com_valor_diferente_nao_concilia():
    r = por_id(conciliar(PED, [lan("L1", "PIX ANA SOUZA P0001", 44.0)]))
    assert r["L1"].status == "revisar"
    assert "difere" in r["L1"].motivo


def test_nome_abreviado_com_valor_unico():
    r = por_id(conciliar(PED, [lan("L1", "PIX RECEBIDO JOAO P", 32.5, "2026-10-06")]))
    assert r["L1"].status == "conciliado" and r["L1"].pedido_id == "P0003"


def test_fora_da_janela_de_dias_nao_casa():
    r = por_id(conciliar(PED, [lan("L1", "PIX RECEBIDO JOAO P", 32.5, "2026-10-20")]))
    assert r["L1"].status != "conciliado"


def test_pagamento_antes_do_pedido_nao_casa():
    r = por_id(conciliar(PED, [lan("L1", "PIX RECEBIDO JOAO P", 32.5, "2026-10-01")]))
    assert r["L1"].status != "conciliado"


def test_tarifa_fica_sem_pedido():
    r = por_id(conciliar(PED, [lan("L1", "TARIFA MENSAL CONTA", 12.5)]))
    assert r["L1"].status == "sem_pedido"


def test_pedido_nao_e_usado_duas_vezes():
    res = conciliar(PED, [lan("L1", "PIX ANA SOUZA P0001", 45.0), lan("L2", "PIX ANA S", 45.0)])
    assert sum(r.pedido_id == "P0001" for r in res) == 1


def test_ambiguo_vai_para_revisao():
    ped = [
        {"id": "P0010", "cliente": "Ana Souza", "valor": 50.0, "data": "2026-10-02"},
        {"id": "P0011", "cliente": "Ana Souza", "valor": 50.0, "data": "2026-10-02"},
    ]
    r = por_id(conciliar(ped, [lan("L1", "PIX RECEBIDO ANA S", 50.0)]))
    assert r["L1"].status == "revisar"


def test_nome_abreviado_pontua_alto():
    assert _nome_na_descricao("Ana Souza", "PIX RECEBIDO ANA S") == 1.0
    assert _nome_na_descricao("Ana Souza", "PIX RECEBIDO ZZZ") < 0.6


def test_resumo_conta_pedidos_sem_pagamento():
    res = conciliar(PED, [lan("L1", "PIX ANA SOUZA P0001", 45.0)])
    s = resumo(res, PED)
    assert s["conciliado"] == 1 and s["pedidos_sem_pagamento"] == 2 and s["lancamentos"] == 1


def test_gerar_e_reprodutivel():
    assert gerar(20, 3) == gerar(20, 3)
    assert gerar(20, 3) != gerar(20, 4)


def test_medir_no_lote_sintetico():
    m = medir()
    assert m["precisao"] >= 0.95
    assert m["cobertura"] >= 0.8
