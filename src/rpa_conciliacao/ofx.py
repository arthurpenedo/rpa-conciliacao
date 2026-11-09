"""Leitor de OFX (extrato bancário): converte cada transação em um lançamento igual ao do CSV."""

from __future__ import annotations

import re
from datetime import datetime
from pathlib import Path

_BLOCO = re.compile(r"<STMTTRN>(.*?)(?:</STMTTRN>|(?=<STMTTRN>)|(?=</BANKTRANLIST>)|\Z)", re.DOTALL | re.IGNORECASE)


def _campo(bloco: str, tag: str) -> str | None:
    # OFX 1.x não fecha as tags (`<TRNAMT>10.00`); OFX 2.x fecha. O padrão aceita os dois.
    achou = re.search(rf"<{tag}>\s*([^<\r\n]*)", bloco, re.IGNORECASE)
    return achou.group(1).strip() if achou else None


def ler_ofx(caminho: Path) -> list[dict]:
    """Lê as transações (`STMTTRN`) de um arquivo OFX; erro claro se faltar campo ou o valor for inválido."""
    bruto = caminho.read_bytes()
    try:
        texto = bruto.decode("utf-8")
    except UnicodeDecodeError:  # OFX brasileiro antigo costuma vir em latin-1
        texto = bruto.decode("latin-1")
    blocos = _BLOCO.findall(texto)
    if not blocos:
        raise ValueError(f"{caminho.name}: nenhuma transação (STMTTRN) encontrada")
    linhas = []
    for n, bloco in enumerate(blocos, start=1):
        fitid, data, valor = _campo(bloco, "FITID"), _campo(bloco, "DTPOSTED"), _campo(bloco, "TRNAMT")
        if not (fitid and data and valor):
            raise ValueError(f"{caminho.name} transação {n}: faltam FITID, DTPOSTED ou TRNAMT")
        try:
            dia = datetime.strptime(data[:8], "%Y%m%d").strftime("%Y-%m-%d")
            numero = float(valor.replace(",", "."))
        except ValueError as e:
            raise ValueError(f"{caminho.name} transação {n}: valor ou data inválidos ({e})") from e
        descricao = _campo(bloco, "MEMO") or _campo(bloco, "NAME") or ""
        linhas.append({"id": fitid, "data": dia, "descricao": descricao, "valor": numero})
    return linhas
