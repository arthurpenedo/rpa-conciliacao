import json

import pytest

from rpa_conciliacao import robo
from rpa_conciliacao.cli import main
from rpa_conciliacao.conciliar import Resultado
from rpa_conciliacao.relatorio import gerar_html


def log_eventos(saida):
    return [json.loads(x) for x in (saida / "robo.jsonl").read_text(encoding="utf-8").splitlines()]


def test_demo_e_robo_ponta_a_ponta(tmp_path, capsys):
    ent, sai = tmp_path / "ent", tmp_path / "sai"
    assert main(["demo", "--entrada", str(ent), "--n", "30"]) == 0
    assert main(["robo", "--entrada", str(ent), "--saida", str(sai)]) == 0
    assert "outubro:" in capsys.readouterr().out
    assert (sai / "outubro" / "conciliado.csv").exists()
    assert (sai / "outubro" / "relatorio.html").exists()
    assert (sai / "processados" / "outubro.extrato.csv").exists()
    assert not list(ent.glob("*.csv"))
    assert log_eventos(sai)[-1]["evento"] == "ok"


def test_arquivo_ruim_vai_para_erros_e_o_lote_segue(tmp_path):
    ent, sai = tmp_path / "ent", tmp_path / "sai"
    main(["demo", "--entrada", str(ent), "--n", "10"])
    (ent / "ruim.extrato.csv").write_text("id,data,descricao,valor\nL1,2026-10-01,X,abc\n", encoding="utf-8")
    (ent / "ruim.pedidos.csv").write_text("id,cliente,valor,data\n", encoding="utf-8")
    res = robo.rodar_uma_vez(ent, sai)
    assert [x["lote"] for x in res] == ["outubro"]
    assert (sai / "erros" / "ruim.extrato.csv").exists()
    erro = [e for e in log_eventos(sai) if e["evento"] == "erro"][0]
    assert "linha 2" in erro["motivo"]


def test_coluna_faltando_da_erro_claro(tmp_path):
    f = tmp_path / "a.csv"
    f.write_text("id,data\n1,2026-10-01\n", encoding="utf-8")
    with pytest.raises(ValueError, match="faltam colunas"):
        robo.ler_csv(f, ("id", "data", "valor"))


def test_valor_com_virgula(tmp_path):
    f = tmp_path / "a.csv"
    f.write_text('id,data,valor\n1,2026-10-01,"12,50"\n', encoding="utf-8")
    assert robo.ler_csv(f, ("id", "data", "valor"))[0]["valor"] == 12.5


def test_sem_arquivo_de_pedidos_fica_aguardando(tmp_path):
    ent, sai = tmp_path / "ent", tmp_path / "sai"
    ent.mkdir()
    (ent / "x.extrato.csv").write_text("id,data,descricao,valor\n", encoding="utf-8")
    assert robo.rodar_uma_vez(ent, sai) == []
    assert (ent / "x.extrato.csv").exists()
    assert log_eventos(sai)[0]["evento"] == "aguardando"


def test_arquivo_travado_tenta_de_novo_e_desiste(tmp_path, monkeypatch):
    ent, sai = tmp_path / "ent", tmp_path / "sai"
    main(["demo", "--entrada", str(ent), "--n", "5"])

    def trava(*a, **k):
        raise PermissionError("aberto no Excel")

    monkeypatch.setattr(robo, "processar_par", trava)
    monkeypatch.setattr(robo.time, "sleep", lambda s: None)
    assert robo.rodar_uma_vez(ent, sai, tentativas=3) == []
    eventos = [e["evento"] for e in log_eventos(sai)]
    assert eventos.count("tentativa") == 3 and eventos[-1] == "erro"
    assert (ent / "outubro.extrato.csv").exists()  # nada foi perdido


def test_html_escapa_texto_dos_dados():
    lan = {"id": "L1", "data": "2026-10-01", "descricao": "<script>x</script>", "valor": 1.0}
    html = gerar_html(
        [Resultado(lan, "sem_pedido", None, "a<b")],
        {"conciliado": 0, "revisar": 0, "sem_pedido": 1, "pedidos_sem_pagamento": 0, "lancamentos": 1},
    )
    assert "<script>" not in html and "&lt;script&gt;" in html


def test_medir_imprime(capsys):
    assert main(["medir"]) == 0
    assert "precisão" in capsys.readouterr().out
