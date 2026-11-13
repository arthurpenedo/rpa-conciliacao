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
    erro = next(e for e in log_eventos(sai) if e["evento"] == "erro")
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


def test_demo_em_ofx_gera_o_mesmo_resultado_do_csv(tmp_path):
    csv_, ofx_ = tmp_path / "csv", tmp_path / "ofx"
    main(["demo", "--entrada", str(csv_), "--n", "20"])
    main(["demo", "--entrada", str(ofx_), "--n", "20", "--formato", "ofx"])
    assert (ofx_ / "outubro.extrato.ofx").exists()
    assert not (ofx_ / "outubro.extrato.csv").exists()
    res_csv = robo.rodar_uma_vez(csv_, tmp_path / "s1")
    res_ofx = robo.rodar_uma_vez(ofx_, tmp_path / "s2")
    assert res_csv == res_ofx


def test_vigiar_processa_arquivo_que_chega_no_meio(tmp_path):
    ent, sai = tmp_path / "ent", tmp_path / "sai"
    ent.mkdir()
    esperas = []

    def dormir(seg):  # simula a chegada de um lote enquanto o robô espera
        esperas.append(seg)
        if len(esperas) == 1:
            main(["demo", "--entrada", str(ent), "--n", "8"])

    total = robo.vigiar(ent, sai, intervalo=3, max_ciclos=3, dormir=dormir)
    assert total == 1
    assert esperas == [3, 3]  # não dorme depois do último ciclo
    eventos = [e["evento"] for e in log_eventos(sai)]
    assert eventos[0] == "vigia_inicio" and eventos[-1] == "vigia_fim"


def test_cli_vigiar_com_ciclos(tmp_path, capsys):
    ent = tmp_path / "ent"
    main(["demo", "--entrada", str(ent), "--n", "5"])
    assert main(["robo", "--entrada", str(ent), "--saida", str(tmp_path / "s"), "--vigiar", "0.01", "--ciclos", "2"]) == 0
    assert "1 lote(s)" in capsys.readouterr().out


def test_vigiar_termina_limpo_com_ctrl_c(tmp_path):
    def dormir_e_interromper(_segundos):
        raise KeyboardInterrupt

    total = robo.vigiar(tmp_path / "ent", tmp_path / "s", dormir=dormir_e_interromper)
    assert total == 0
    eventos = log_eventos(tmp_path / "s")
    assert eventos[-1]["evento"] == "vigia_fim"
    assert eventos[-1]["ciclos"] == 1
