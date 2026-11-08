"""Linha de comando: demo (gera dados e roda), robo (processa a pasta de entrada) e medir."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from .conciliar import conciliar, precisao
from .gerar import gerar
from .robo import escrever_csv, rodar_uma_vez


def medir(n: int = 60, seed: int = 7) -> dict:
    pedidos, extrato, gabarito = gerar(n, seed)
    return precisao(conciliar(pedidos, extrato), gabarito)


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(prog="rpa-conciliacao")
    sub = ap.add_subparsers(dest="cmd", required=True)
    d = sub.add_parser("demo", help="gera um lote fictício na pasta de entrada")
    d.add_argument("--entrada", default="entrada")
    d.add_argument("--n", type=int, default=60)
    r = sub.add_parser("robo", help="processa os pares da pasta de entrada")
    r.add_argument("--entrada", default="entrada")
    r.add_argument("--saida", default="saida")
    sub.add_parser("medir", help="precisão e cobertura no lote sintético com gabarito")
    a = ap.parse_args(argv)

    if a.cmd == "demo":
        pedidos, extrato, _ = gerar(a.n)
        pasta = Path(a.entrada)
        escrever_csv(pasta / "outubro.pedidos.csv", pedidos, ("id", "cliente", "valor", "data"))
        escrever_csv(pasta / "outubro.extrato.csv", extrato, ("id", "data", "descricao", "valor"))
        print(f"Lote fictício gravado em {pasta}/ ({len(pedidos)} pedidos, {len(extrato)} lançamentos).")
    elif a.cmd == "robo":
        res = rodar_uma_vez(Path(a.entrada), Path(a.saida))
        for x in res:
            print(f"{x['lote']}: {x['conciliado']} conciliados, {x['revisar']} a revisar, {x['sem_pedido']} sem pedido")
        if not res:
            print("Nada processado (veja saida/robo.jsonl).")
    else:
        m = medir()
        print(f"precisão {m['precisao']:.1%} | cobertura {m['cobertura']:.1%} | conciliados {m['conciliados']}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
