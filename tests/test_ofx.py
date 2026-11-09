import pytest

from rpa_conciliacao import robo
from rpa_conciliacao.ofx import ler_ofx

OFX1 = """OFXHEADER:100
DATA:OFXSGML

<OFX><BANKMSGSRSV1><STMTTRNRS><STMTRS><BANKTRANLIST>
<STMTTRN>
<TRNTYPE>CREDIT
<DTPOSTED>20261005120000[-3:BRT]
<TRNAMT>45,50
<FITID>A1
<MEMO>PIX RECEBIDO ANA SOUZA P0001
</STMTTRN>
<STMTTRN>
<DTPOSTED>20261006
<TRNAMT>-10.00
<FITID>A2
<NAME>TARIFA
</BANKTRANLIST></STMTRS></STMTTRNRS></BANKMSGSRSV1></OFX>
"""

OFX2 = (
    "<OFX><STMTTRN><DTPOSTED>20261007</DTPOSTED><TRNAMT>12.30</TRNAMT>"
    "<FITID>B1</FITID><MEMO>Pix João</MEMO></STMTTRN></OFX>"
)


def test_ofx_v1_sem_tags_de_fechamento(tmp_path):
    f = tmp_path / "x.ofx"
    f.write_text(OFX1, encoding="utf-8")
    assert ler_ofx(f) == [
        {"id": "A1", "data": "2026-10-05", "descricao": "PIX RECEBIDO ANA SOUZA P0001", "valor": 45.5},
        {"id": "A2", "data": "2026-10-06", "descricao": "TARIFA", "valor": -10.0},
    ]


def test_ofx_v2_e_latin1(tmp_path):
    f = tmp_path / "y.ofx"
    f.write_bytes(OFX2.encode("latin-1"))
    assert ler_ofx(f)[0]["descricao"] == "Pix João"


@pytest.mark.parametrize(
    "texto",
    ["sem nada", "<STMTTRN><FITID>1<TRNAMT>5</STMTTRN>", "<STMTTRN><FITID>1<DTPOSTED>2026<TRNAMT>x</STMTTRN>"],
)
def test_ofx_invalido_da_erro_claro(tmp_path, texto):
    f = tmp_path / "z.ofx"
    f.write_text(texto, encoding="utf-8")
    with pytest.raises(ValueError, match="z.ofx"):
        ler_ofx(f)


def test_robo_aceita_extrato_ofx(tmp_path):
    ent, sai = tmp_path / "ent", tmp_path / "sai"
    ent.mkdir()
    (ent / "nov.extrato.ofx").write_text(OFX1, encoding="utf-8")
    (ent / "nov.pedidos.csv").write_text(
        "id,cliente,valor,data\nP0001,Ana Souza,45.50,2026-10-04\n", encoding="utf-8"
    )
    res = robo.rodar_uma_vez(ent, sai)
    assert res[0]["lote"] == "nov"
    assert "P0001" in (sai / "nov" / "conciliado.csv").read_text(encoding="utf-8")
    assert (sai / "processados" / "nov.extrato.ofx").exists()
