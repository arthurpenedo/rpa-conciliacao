"""Regras de conciliação: cada lançamento do extrato vira conciliado, a revisar ou sem pedido."""

from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass
from datetime import date
from difflib import SequenceMatcher

JANELA_DIAS = 5
LIMITE_NOME = 0.6


def normalizar(texto: str) -> str:
    sem = unicodedata.normalize("NFKD", texto).encode("ascii", "ignore").decode()
    return re.sub(r"\s+", " ", sem.upper()).strip()


def _nome_na_descricao(cliente: str, descricao: str) -> float:
    """Parecença (0 a 1) entre o cliente e o que aparece na descrição do PIX/transferência."""
    d = normalizar(descricao)
    d = re.sub(r"^(PIX RECEBIDO|PIX|TRANSF|TED|DOC)\s+", "", d)
    d = re.sub(r"\s*P\d{4}\b", "", d).strip()  # o código do pedido não faz parte do nome
    partes_c = normalizar(cliente).split()
    partes_d = d.split()
    if not partes_d:
        return 0.0
    inicial_so = len(partes_d) >= 2 and len(partes_d[-1]) == 1 and partes_c  # "ANA S" = Ana Souza
    if inicial_so and partes_c[0] == partes_d[0] and partes_c[-1].startswith(partes_d[-1]):
        return 1.0
    return SequenceMatcher(None, normalizar(cliente), d).ratio()


@dataclass
class Resultado:
    lancamento: dict
    status: str  # conciliado | revisar | sem_pedido
    pedido_id: str | None
    motivo: str


def conciliar(pedidos: list[dict], extrato: list[dict]) -> list[Resultado]:
    """Casa extrato com pedidos. Um pedido só é usado uma vez."""
    livres = {p["id"]: p for p in pedidos}
    resultados: list[Resultado] = []
    pendentes = []
    # 1ª passada: o código do pedido aparece na descrição e o valor bate
    for lan in sorted(extrato, key=lambda x: x["id"]):
        achou = re.search(r"P\d{4}", normalizar(lan["descricao"]))
        pid = achou.group(0) if achou else None
        if pid in livres and abs(livres[pid]["valor"] - lan["valor"]) < 0.005:
            resultados.append(Resultado(lan, "conciliado", pid, "código do pedido e valor iguais"))
            del livres[pid]
        else:
            pendentes.append(lan)
    # 2ª passada: valor igual, data próxima e nome parecido
    for lan in pendentes:
        melhores = []
        for p in livres.values():
            if abs(p["valor"] - lan["valor"]) >= 0.005:
                continue
            dias = (date.fromisoformat(lan["data"]) - date.fromisoformat(p["data"])).days
            if not 0 <= dias <= JANELA_DIAS:
                continue
            nota = _nome_na_descricao(p["cliente"], lan["descricao"])
            if nota >= LIMITE_NOME:
                melhores.append((nota, p["id"]))
        melhores.sort(reverse=True)
        if len(melhores) == 1 or (len(melhores) > 1 and melhores[0][0] - melhores[1][0] > 0.15):
            pid = melhores[0][1]
            resultados.append(Resultado(lan, "conciliado", pid, "valor, data e nome compatíveis"))
            del livres[pid]
        elif melhores:
            resultados.append(Resultado(lan, "revisar", None, "mais de um pedido possível"))
        else:
            resultados.append(_sem_casamento(lan, livres))
    return sorted(resultados, key=lambda r: r.lancamento["id"])


def _sem_casamento(lan: dict, livres: dict[str, dict]) -> Resultado:
    """Sem pedido igual: se há pedido de nome parecido com valor diferente, um humano decide."""
    for p in livres.values():
        if _nome_na_descricao(p["cliente"], lan["descricao"]) >= 0.8:
            dif = round(lan["valor"] - p["valor"], 2)
            return Resultado(lan, "revisar", None, f"nome bate com {p['id']}, mas valor difere em {dif:+.2f}")
    return Resultado(lan, "sem_pedido", None, "nenhum pedido compatível")


def resumo(resultados: list[Resultado], pedidos: list[dict]) -> dict:
    cont = {"conciliado": 0, "revisar": 0, "sem_pedido": 0}
    for r in resultados:
        cont[r.status] += 1
    usados = {r.pedido_id for r in resultados if r.pedido_id}
    cont["pedidos_sem_pagamento"] = sum(1 for p in pedidos if p["id"] not in usados)
    cont["lancamentos"] = len(resultados)
    return cont


def precisao(resultados: list[Resultado], gabarito: dict[str, str | None]) -> dict:
    """Entre os conciliados, quantos acertaram; e quantos dos que tinham pedido foram conciliados."""
    conc = [r for r in resultados if r.status == "conciliado"]
    certos = sum(1 for r in conc if gabarito.get(r.lancamento["id"]) == r.pedido_id)
    com_pedido = [k for k, v in gabarito.items() if v]
    pegos = sum(1 for r in conc if gabarito.get(r.lancamento["id"]))
    return {
        "precisao": certos / len(conc) if conc else 1.0,
        "cobertura": pegos / len(com_pedido) if com_pedido else 1.0,
        "conciliados": len(conc),
    }
