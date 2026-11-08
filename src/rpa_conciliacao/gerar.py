"""Gera pedidos e extrato sintéticos, com gabarito (dados 100% fictícios)."""

from __future__ import annotations

import random
from datetime import date, timedelta

NOMES = [
    "Ana Souza", "Bruno Lima", "Carla Dias", "Diego Ramos", "Elisa Prado",
    "Fabio Nunes", "Gabriela Melo", "Hugo Teixeira", "Irene Castro", "Joao Pires",
    "Karen Alves", "Lucas Moreira", "Marina Rocha", "Nicolas Faria", "Olivia Barros",
]
PRECOS = [18.0, 25.0, 32.5, 45.0, 60.0, 89.9, 120.0]


def gerar(n: int = 60, seed: int = 7) -> tuple[list[dict], list[dict], dict[str, str | None]]:
    """Devolve (pedidos, extrato, gabarito). Gabarito: id da linha do extrato -> id do pedido (ou None)."""
    rng = random.Random(seed)
    base = date(2026, 10, 1)
    pedidos, extrato, gabarito = [], [], {}
    for i in range(1, n + 1):
        nome = rng.choice(NOMES)
        valor = round(rng.choice(PRECOS) * rng.randint(1, 4), 2)
        dia = base + timedelta(days=rng.randint(0, 25))
        pid = f"P{i:04d}"
        pedidos.append({"id": pid, "cliente": nome, "valor": valor, "data": dia.isoformat()})
        sorte = rng.random()
        if sorte < 0.08:  # cliente não pagou
            continue
        lid = f"L{len(extrato) + 1:04d}"
        pago = dia + timedelta(days=rng.randint(0, 3))
        if sorte < 0.55:  # PIX com o código do pedido na descrição
            desc = f"PIX RECEBIDO {nome.upper()} {pid}"
        elif sorte < 0.85:  # PIX sem código, nome sem acento/abreviado
            primeiro, ultimo = nome.split()
            desc = f"PIX RECEBIDO {primeiro.upper()} {ultimo[0].upper()}"
        else:  # valor pago com erro de digitação
            desc = f"TRANSF {nome.upper()}"
            valor = round(valor + rng.choice([-1, 1]) * 0.5, 2)
        extrato.append({"id": lid, "data": pago.isoformat(), "descricao": desc, "valor": valor})
        gabarito[lid] = pid if sorte < 0.85 else None
    # lançamentos que não são de pedido (tarifa, estorno)
    for k in range(5):
        lid = f"L{len(extrato) + 1:04d}"
        dia = base + timedelta(days=rng.randint(0, 25))
        extrato.append({"id": lid, "data": dia.isoformat(), "descricao": "TARIFA MENSAL CONTA", "valor": 12.5})
        gabarito[lid] = None
    rng.shuffle(extrato)
    return pedidos, extrato, gabarito
